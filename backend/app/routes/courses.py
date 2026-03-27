from flask import Blueprint, request, jsonify
from ..models import db, Course, Class, Student, Warning, User, AssistantCourseAssignment
from ..services.warning_engine import WarningEngine # 引入预警引擎计算分数
from ..utils.authz import (
    ROLE_ADMIN,
    ROLE_ASSISTANT,
    ROLE_TEACHER,
    ensure_course_access,
    get_current_user,
    role_required,
    scope_courses_query,
)

courses_bp = Blueprint('courses', __name__)


@courses_bp.route('/', methods=['GET'])
@role_required(ROLE_ADMIN, ROLE_TEACHER, ROLE_ASSISTANT)
def get_courses():
    """获取所有课程及班级信息"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401

        courses_query = Course.query
        courses_query = scope_courses_query(courses_query, current_user)
        courses = courses_query.all()
        data = []

        for course in courses:
            teacher = User.query.get(course.teacher_id) if course.teacher_id else None
            
            # 获取该课程的所有班级
            classes = Class.query.filter_by(course_id=course.id).all()
            classes_data = []

            for cls in classes:
                student_count = Student.query.filter_by(class_id=cls.id).count()
                
                # 获取班级学生ID列表
                class_student_ids = [s.id for s in Student.query.filter_by(class_id=cls.id).all()]
                
                warning_count = 0
                if class_student_ids:
                    warning_count = Warning.query.filter(
                        Warning.student_id.in_(class_student_ids),
                        Warning.status == 'active'
                    ).count()

                classes_data.append({
                    'id': cls.id,
                    'name': cls.name,
                    'student_count': student_count,
                    'warning_count': warning_count,
                    'attendance_rate': 85,  # 待实现具体计算逻辑
                    'teacher': '未分配'  # 待实现
                })

            data.append({
                'id': course.id,
                'name': course.name,
                'code': course.code,
                'teacher_name': teacher.name if teacher else '未分配教师',
                'semester': course.semester,
                'student_count': sum(c['student_count'] for c in classes_data),
                'warning_count': sum(c['warning_count'] for c in classes_data),
                'attendance_rate': 85,
                'classes': classes_data
            })

        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取课程列表失败: {str(e)}'}), 500


@courses_bp.route('/', methods=['POST'])
@role_required(ROLE_ADMIN, ROLE_TEACHER)
def create_course():
    """创建课程"""
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

    current_user = get_current_user()
    if not current_user:
        return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401

    teacher_id = current_user.id
    if current_user.role == ROLE_ADMIN:
        payload_teacher_id = payload.get('teacher_id')
        if payload_teacher_id:
            teacher_id = payload_teacher_id

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


@courses_bp.route('/assistants', methods=['GET'])
@role_required(ROLE_ADMIN, ROLE_TEACHER)
def list_assistants():
    """教师/管理员获取可选助教列表"""
    assistants = User.query.filter_by(role=ROLE_ASSISTANT, is_active=True).order_by(User.name.asc()).all()
    return jsonify({
        'success': True,
        'data': [u.to_dict() for u in assistants]
    })


@courses_bp.route('/<int:course_id>/assistants', methods=['GET', 'POST'])
@role_required(ROLE_ADMIN, ROLE_TEACHER)
def course_assistants(course_id):
    """查询/指派课程助教"""
    current_user = get_current_user()
    if not current_user:
        return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401

    allowed, error = ensure_course_access(course_id, current_user)
    if not allowed:
        message, status = error
        return jsonify({'success': False, 'message': message}), status

    if request.method == 'GET':
        assignments = AssistantCourseAssignment.query.filter_by(course_id=course_id).all()
        data = []
        for assignment in assignments:
            assistant = User.query.get(assignment.assistant_id)
            assigner = User.query.get(assignment.assigned_by)
            data.append({
                'assistant_id': assignment.assistant_id,
                'assistant_name': assistant.name if assistant else '',
                'assistant_username': assistant.username if assistant else '',
                'assigned_by': assignment.assigned_by,
                'assigned_by_name': assigner.name if assigner else '',
                'assigned_at': assignment.assigned_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        return jsonify({'success': True, 'data': data})

    payload = request.get_json() or {}
    assistant_id = payload.get('assistant_id')
    if not assistant_id:
        return jsonify({'success': False, 'message': '缺少assistant_id'}), 400

    assistant = User.query.filter_by(id=assistant_id, role=ROLE_ASSISTANT, is_active=True).first()
    if not assistant:
        return jsonify({'success': False, 'message': '助教不存在或已停用'}), 404

    exists = AssistantCourseAssignment.query.filter_by(
        assistant_id=assistant_id,
        course_id=course_id,
    ).first()
    if exists:
        return jsonify({'success': True, 'message': '助教已被指派到该课程'})

    assignment = AssistantCourseAssignment(
        assistant_id=assistant_id,
        course_id=course_id,
        assigned_by=current_user.id,
    )
    db.session.add(assignment)
    db.session.commit()

    return jsonify({'success': True, 'message': '助教指派成功'}), 201


@courses_bp.route('/<int:course_id>/assistants/<int:assistant_id>', methods=['DELETE'])
@role_required(ROLE_ADMIN, ROLE_TEACHER)
def remove_course_assistant(course_id, assistant_id):
    """解除课程助教指派"""
    current_user = get_current_user()
    if not current_user:
        return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401

    allowed, error = ensure_course_access(course_id, current_user)
    if not allowed:
        message, status = error
        return jsonify({'success': False, 'message': message}), status

    assignment = AssistantCourseAssignment.query.filter_by(
        course_id=course_id,
        assistant_id=assistant_id,
    ).first()
    if not assignment:
        return jsonify({'success': False, 'message': '该助教未被指派到此课程'}), 404

    db.session.delete(assignment)
    db.session.commit()
    return jsonify({'success': True, 'message': '已解除助教指派'})


@courses_bp.route('/<int:course_id>/classes', methods=['GET', 'POST'])
@role_required(ROLE_ADMIN, ROLE_TEACHER, ROLE_ASSISTANT)
def classes(course_id):
    """获取班级或创建班级"""
    current_user = get_current_user()
    if not current_user:
        return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401

    allowed, error = ensure_course_access(course_id, current_user)
    if not allowed:
        message, status = error
        return jsonify({'success': False, 'message': message}), status

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
    if current_user.role == ROLE_ASSISTANT:
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
@role_required(ROLE_ADMIN, ROLE_TEACHER, ROLE_ASSISTANT)
def students(course_id, class_id):
    """获取学生或添加学生"""
    current_user = get_current_user()
    if not current_user:
        return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401

    allowed, error = ensure_course_access(course_id, current_user)
    if not allowed:
        message, status = error
        return jsonify({'success': False, 'message': message}), status

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
                score = engine._calculate_comprehensive_score(metrics)
                s_dict['score'] = round(score, 1) if score is not None else None
                
                # 2. 获取预警状态 (从 Warning 表查)
                active_warning = Warning.query.filter_by(
                    student_id=s.id, 
                    course_id=course_id, 
                    status='active'
                ).order_by(Warning.level).first() # 获取最严重的预警 (red < orange < yellow, 字典序 r < o < y 需注意)
                
                # 实际上 level 字符串比较：red > orange > yellow 
                # 但我们更关心是否有 active warning
                
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
    if current_user.role == ROLE_ASSISTANT:
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
@role_required(ROLE_ADMIN, ROLE_TEACHER)
def manage_student(student_id):
    """
    修改或删除学生
    PUT: 修改基本信息
    DELETE: 删除学生
    """
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'success': False, 'message': '学生不存在'}), 404

    current_user = get_current_user()
    if not current_user:
        return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401
    course_id = student.class_.course_id if student.class_ else None
    if not course_id:
        return jsonify({'success': False, 'message': '学生所属课程不存在'}), 404
    allowed, error = ensure_course_access(course_id, current_user)
    if not allowed:
        message, status = error
        return jsonify({'success': False, 'message': message}), status
        
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
