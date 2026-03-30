from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from ..models import db, Course, Class, Student, Warning, User
from ..services.warning_engine import WarningEngine # 引入预警引擎计算分数

courses_bp = Blueprint('courses', __name__)


def _current_role():
    claims = get_jwt()
    return (claims.get('role') or 'teacher').lower()


@courses_bp.route('/', methods=['GET'])
@jwt_required()
def get_courses():
    """获取所有课程及班级信息"""
    try:
        courses = Course.query.all()
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
@jwt_required()
def create_course():
    """创建课程"""
    if _current_role() == 'assistant':
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

    # 获取当前用户ID
    current_user_identity = get_jwt_identity()
    
    # 兼容不同的 identity 类型 (可能是对象或直接是ID)
    teacher_id = None
    if isinstance(current_user_identity, dict):
        teacher_id = current_user_identity.get('id')
    else:
        try:
            teacher_id = int(current_user_identity)
        except (ValueError, TypeError):
            pass
            
    if not teacher_id:
        # 如果从JWT拿不到ID，尝试通过用户名查找
        if isinstance(current_user_identity, str):
            user = User.query.filter_by(username=current_user_identity).first()
            if user:
                teacher_id = user.id

    if not teacher_id:
         # 尝试从 User 表查找第一个用户作为 fallback (仅用于测试环境)
        first_user = User.query.first()
        if first_user:
            teacher_id = first_user.id
        else:
            # 如果系统真的没有任何用户，这是一个严重问题
            return jsonify({'success': False, 'message': '无法获取有效的教师ID，且系统中无用户'}), 401

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


@courses_bp.route('/<int:course_id>/classes', methods=['GET', 'POST'])
@jwt_required()
def classes(course_id):
    """获取班级或创建班级"""
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
    if _current_role() == 'assistant':
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
                s_dict['score'] = round(score, 1)
                
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
    if _current_role() == 'assistant':
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
    if _current_role() == 'assistant':
        return jsonify({'success': False, 'message': '助教无权限修改或删除学生'}), 403
