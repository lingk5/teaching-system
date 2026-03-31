from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func, case
from ..models import db, Course, Class, Student, Warning, User, AssistantCourseAssignment
from ..models.data import Attendance
from ..services.warning_engine import WarningEngine
from ..utils.permissions import (
    current_user_can,
    current_user_id,
    current_role,
    can_access_course,
    can_access_class,
    can_access_student,
    accessible_course_query,
)

courses_bp = Blueprint('courses', __name__)


def _compute_attendance_rate(student_ids, course_id):
    if not student_ids:
        return None

    total = Attendance.query.filter(
        Attendance.student_id.in_(student_ids),
        Attendance.course_id == course_id
    ).count()
    if total == 0:
        return None

    present = Attendance.query.filter(
        Attendance.student_id.in_(student_ids),
        Attendance.course_id == course_id,
        Attendance.status == 'present'
    ).count()
    return round(present / total * 100, 1)


def _can_manage_course_assignments(course):
    role = current_role()
    user_id = current_user_id()
    return role == 'admin' or (role == 'teacher' and course.teacher_id == user_id)


@courses_bp.route('/', methods=['GET'])
@jwt_required()
def get_courses():
    """获取所有课程及班级信息"""
    try:
        courses = accessible_course_query().order_by(Course.id.asc()).all()
        data = []

        for course in courses:
            teacher = User.query.get(course.teacher_id) if course.teacher_id else None
            assistant_rows = db.session.query(
                AssistantCourseAssignment,
                User.name,
                User.username
            ).join(
                User,
                AssistantCourseAssignment.assistant_id == User.id
            ).filter(
                AssistantCourseAssignment.course_id == course.id
            ).all()
            
            # 获取该课程的所有班级
            classes = Class.query.filter_by(course_id=course.id).all()
            classes_data = []
            all_course_student_ids = []

            for cls in classes:
                class_students = Student.query.filter_by(class_id=cls.id).all()
                class_student_ids = [s.id for s in class_students]
                student_count = len(class_student_ids)
                all_course_student_ids.extend(class_student_ids)
                
                warning_count = 0
                if class_student_ids:
                    warning_count = Warning.query.filter(
                        Warning.student_id.in_(class_student_ids),
                        Warning.course_id == course.id,
                        Warning.status.in_(['active', 'pending'])
                    ).count()

                classes_data.append({
                    'id': cls.id,
                    'name': cls.name,
                    'student_count': student_count,
                    'warning_count': warning_count,
                    'attendance_rate': _compute_attendance_rate(class_student_ids, course.id),
                    'teacher': teacher.name if teacher else None
                })

            data.append({
                'id': course.id,
                'name': course.name,
                'code': course.code,
                'teacher_name': teacher.name if teacher else '未分配教师',
                'semester': course.semester,
                'student_count': sum(c['student_count'] for c in classes_data),
                'warning_count': sum(c['warning_count'] for c in classes_data),
                'attendance_rate': _compute_attendance_rate(all_course_student_ids, course.id),
                'classes': classes_data,
                'assistants': [
                    {
                        'assistant_id': row.assistant_id,
                        'assistant_name': name,
                        'assistant_username': username,
                        'assigned_by': row.assigned_by,
                        'assigned_at': row.assigned_at.strftime('%Y-%m-%d %H:%M:%S'),
                    }
                    for row, name, username in assistant_rows
                ],
            })

        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取课程列表失败: {str(e)}'}), 500


@courses_bp.route('/', methods=['POST'])
@jwt_required()
def create_course():
    """创建课程"""
    if not current_user_can('manage_courses'):
        return jsonify({'success': False, 'message': '助教无权限创建课程'}), 403

    if not request.is_json:
        return jsonify(
            {'success': False, 'message': 'Content-Type必须是application/json'}
        ), 400

    payload = request.get_json() or {}
    name = (payload.get('name') or '').strip()
    code = (payload.get('code') or '').strip() or None
    semester = (payload.get('semester') or '').strip() or None
    description = (payload.get('description') or '').strip() or None

    if not name:
        return jsonify({'success': False, 'message': '课程名称不能为空'}), 400

    if code:
        existing_course = Course.query.filter_by(code=code).first()
        if existing_course:
            return jsonify({'success': False, 'message': f'课程代码 {code} 已存在'}), 400

    role = current_role()
    requester_id = current_user_id()
    teacher_id = requester_id if role == 'teacher' else payload.get('teacher_id', requester_id)

    teacher = User.query.get(teacher_id)
    if not teacher:
        return jsonify({'success': False, 'message': '教师用户不存在'}), 404

    try:
        course = Course(
            name=name,
            code=code,
            semester=semester,
            description=description,
            teacher_id=teacher_id,
        )
        db.session.add(course)
        db.session.commit()

        return jsonify(
            {
                'success': True,
                'message': '课程创建成功',
                'data': {
                    'id': course.id,
                    'name': course.name,
                    'code': course.code,
                    'semester': course.semester,
                    'teacher_id': course.teacher_id,
                    'teacher_name': teacher.name,
                    'classes': [],
                    'student_count': 0,
                    'warning_count': 0,
                    'attendance_rate': 0,
                },
            }
        ), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'创建课程失败: {str(e)}'}), 500


@courses_bp.route('/assistant-options', methods=['GET'])
@jwt_required()
def assistant_options():
    """获取可分配的助教列表"""
    if current_role() == 'assistant':
        return jsonify({'success': False, 'message': '助教无权限查看可分配助教列表'}), 403

    assistants = User.query.filter_by(role='assistant').order_by(User.id.asc()).all()
    return jsonify({
        'success': True,
        'data': [assistant.to_dict() for assistant in assistants]
    })


@courses_bp.route('/<int:course_id>/classes', methods=['GET', 'POST'])
@jwt_required()
def classes(course_id):
    """获取班级或创建班级"""
    if not can_access_course(course_id):
        return jsonify({'success': False, 'message': '无权访问该课程'}), 403

    if request.method == 'GET':
        try:
            classes = Class.query.filter_by(course_id=course_id).all()
            return jsonify({
                'success': True,
                'data': [c.to_dict() for c in classes]
            })
        except Exception as e:
            return jsonify({'success': False, 'message': f'获取班级失败: {str(e)}'}), 500

    # POST 创建班级
    if not current_user_can('manage_courses'):
        return jsonify({'success': False, 'message': '助教无权限创建班级'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求体为空'}), 400
        
    name = data.get('name')
    
    if not name:
        return jsonify({'success': False, 'message': '班级名称不能为空'}), 400
        
    try:
        class_ = Class(name=name, course_id=course_id)
        db.session.add(class_)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '班级创建成功',
            'data': class_.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'创建班级失败: {str(e)}'}), 500


@courses_bp.route('/<int:course_id>/classes/<int:class_id>/students', methods=['GET', 'POST'])
@jwt_required()
def students(course_id, class_id):
    """获取学生或添加学生"""
    if not can_access_course(course_id) or not can_access_class(class_id):
        return jsonify({'success': False, 'message': '无权访问该班级'}), 403

    if request.method == 'GET':
        try:
            students = Student.query.filter_by(class_id=class_id).all()
            
            # --- 优化：计算学生的综合评分 ---
            engine = WarningEngine(course_id)
            result = []
            
            for s in students:
                s_dict = s.to_dict()
                
                # 1. 计算分数 (使用 WarningEngine 逻辑)
                metrics = engine._calculate_metrics(s.id)
                score_details = engine._calculate_comprehensive_score(metrics)
                if isinstance(score_details, dict):
                    s_dict['score'] = round(score_details['comprehensive_score'], 1)
                else:
                    s_dict['score'] = round(score_details, 1)
                
                # 2. 获取预警状态 (从 Warning 表查)
                active_warning = Warning.query.filter_by(
                    student_id=s.id, 
                    course_id=course_id, 
                    status='active'
                ).first()
                
                s_dict['warning_level'] = active_warning.level if active_warning else None
                s_dict['class_name'] = s.class_.name # 补充班级名称
                
                result.append(s_dict)
                
            return jsonify({
                'success': True,
                'data': result
            })
        except Exception as e:
            print(f"Error fetching students: {str(e)}")
            return jsonify({'success': False, 'message': f'获取学生失败: {str(e)}'}), 500

    # POST 添加学生
    if not current_user_can('manage_students'):
        return jsonify({'success': False, 'message': '助教无权限添加学生'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求体为空'}), 400

    try:
        student = Student(
            student_no=data['student_no'],
            name=data['name'],
            gender=data.get('gender'),
            class_id=class_id
        )
        db.session.add(student)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '学生添加成功',
            'data': student.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'添加学生失败: {str(e)}'}), 500

@courses_bp.route('/students/<int:student_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def manage_student(student_id):
    """
    修改或删除学生
    PUT: 修改基本信息
    DELETE: 删除学生
    """
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'success': False, 'message': '学生不存在'}), 404

    if not can_access_student(student_id):
        return jsonify({'success': False, 'message': '无权访问该学生'}), 403

    if not current_user_can('manage_students'):
        return jsonify({'success': False, 'message': '助教无权限修改或删除学生'}), 403
        
    if request.method == 'DELETE':
        try:
            # 级联删除由 SQLAlchemy 关系定义处理 (cascade='all, delete-orphan')
            # 如果没有定义级联，这里可能会报错，建议手动清理关联数据或依赖模型级联
            db.session.delete(student)
            db.session.commit()
            return jsonify({'success': True, 'message': '学生已删除'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500
            
    if request.method == 'PUT':
        data = request.get_json()
        try:
            if 'student_no' in data:
                # 检查学号是否冲突 (排除自己)
                existing = Student.query.filter(
                    Student.student_no == data['student_no'],
                    Student.id != student_id
                ).first()
                if existing:
                    return jsonify({'success': False, 'message': '学号已存在'}), 400
                student.student_no = data['student_no']
                
            if 'name' in data:
                student.name = data['name']
            
            if 'gender' in data:
                student.gender = data['gender']
                
            db.session.commit()
            return jsonify({'success': True, 'message': '修改成功', 'data': student.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'修改失败: {str(e)}'}), 500


@courses_bp.route('/<int:course_id>/assistants', methods=['GET', 'POST'])
@jwt_required()
def course_assistants(course_id):
    if not can_access_course(course_id):
        return jsonify({'success': False, 'message': '无权访问该课程'}), 403

    course = Course.query.get(course_id)
    if not course:
        return jsonify({'success': False, 'message': '课程不存在'}), 404

    if request.method == 'GET':
        rows = db.session.query(
            AssistantCourseAssignment,
            User.name,
            User.username
        ).join(
            User,
            AssistantCourseAssignment.assistant_id == User.id
        ).filter(
            AssistantCourseAssignment.course_id == course_id
        ).all()
        return jsonify({
            'success': True,
            'data': [
                {
                    'assistant_id': assignment.assistant_id,
                    'assistant_name': name,
                    'assistant_username': username,
                    'assigned_by': assignment.assigned_by,
                    'assigned_at': assignment.assigned_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
                for assignment, name, username in rows
            ]
        })

    if not _can_manage_course_assignments(course):
        return jsonify({'success': False, 'message': '无权管理该课程助教'}), 403

    payload = request.get_json() or {}
    assistant_id = payload.get('assistant_id')
    assistant = User.query.get(assistant_id)
    if not assistant or assistant.role != 'assistant':
        return jsonify({'success': False, 'message': '助教账号不存在'}), 400

    existing = AssistantCourseAssignment.query.filter_by(
        assistant_id=assistant_id,
        course_id=course_id
    ).first()
    if existing:
        return jsonify({'success': True, 'message': '该助教已分配到本课程', 'data': existing.to_dict()}), 200

    assignment = AssistantCourseAssignment(
        assistant_id=assistant_id,
        course_id=course_id,
        assigned_by=current_user_id(),
    )
    db.session.add(assignment)
    db.session.commit()
    return jsonify({'success': True, 'message': '助教分配成功', 'data': assignment.to_dict()}), 201


@courses_bp.route('/<int:course_id>/assistants/<int:assistant_id>', methods=['DELETE'])
@jwt_required()
def delete_course_assistant(course_id, assistant_id):
    if not can_access_course(course_id):
        return jsonify({'success': False, 'message': '无权访问该课程'}), 403

    course = Course.query.get(course_id)
    if not course:
        return jsonify({'success': False, 'message': '课程不存在'}), 404

    if not _can_manage_course_assignments(course):
        return jsonify({'success': False, 'message': '无权管理该课程助教'}), 403

    assignment = AssistantCourseAssignment.query.filter_by(
        course_id=course_id,
        assistant_id=assistant_id
    ).first()
    if not assignment:
        return jsonify({'success': False, 'message': '助教分配不存在'}), 404

    db.session.delete(assignment)
    db.session.commit()
    return jsonify({'success': True, 'message': '助教分配已取消'})
