from flask import Blueprint, request, jsonify
from ..models import db, Warning, Student, Course
from datetime import datetime
from ..utils.authz import (
    ROLE_ADMIN,
    ROLE_ASSISTANT,
    ROLE_TEACHER,
    ensure_course_access,
    get_accessible_course_ids,
    get_current_user,
    role_required,
)

warnings_bp = Blueprint('warnings', __name__)


@warnings_bp.route('/', methods=['GET'])
@role_required(ROLE_ADMIN, ROLE_TEACHER, ROLE_ASSISTANT)
def get_warnings():
    """获取预警列表"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401

        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        level = request.args.get('level', '')
        status = request.args.get('status', 'active') # 默认只看活跃的
        search = request.args.get('search', '')
        course_id = request.args.get('course_id', type=int)
        class_id = request.args.get('class_id', type=int)

        print(f"Fetch Warnings: level={level}, status={status}, course_id={course_id}, class_id={class_id}")

        # 构建查询
        query = Warning.query

        # 非管理员按可访问课程过滤
        accessible_course_ids = get_accessible_course_ids(current_user)
        if accessible_course_ids is not None:
            if not accessible_course_ids:
                return jsonify({'success': True, 'warnings': [], 'stats': {'total': 0, 'total_pending': 0, 'red_count': 0, 'orange_count': 0, 'resolved_count': 0}, 'total': 0, 'page': page, 'per_page': per_page})
            query = query.filter(Warning.course_id.in_(accessible_course_ids))

        # 按课程筛选
        if course_id:
            allowed, error = ensure_course_access(course_id, current_user)
            if not allowed:
                message, status = error
                return jsonify({'success': False, 'message': message}), status
            query = query.filter(Warning.course_id == course_id)

        # 按班级筛选（需要关联学生表）
        if class_id:
            query = query.join(Student).filter(Student.class_id == class_id)

        # 按等级筛选
        if level and level not in ['null', 'undefined', 'all']:
            query = query.filter_by(level=level)

        # 按状态筛选
        if status == 'active':
            # active 包含 active 和 pending
            query = query.filter(Warning.status.in_(['active', 'pending']))
        elif status == 'processed':
            # processed 包含 processed 和 ignored (即已处理或已解决)
            query = query.filter(Warning.status.in_(['processed', 'ignored']))
        elif status:
            # 其他明确的状态值
            query = query.filter_by(status=status)

        # 搜索功能
        if search:
            # 关联学生表进行搜索
            query = query.join(Student).filter(
                (Student.name.ilike(f'%{search}%')) |
                (Student.student_no.ilike(f'%{search}%'))
            )

        # 分页
        pagination = query.order_by(Warning.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        # 构建响应数据
        warnings = []
        for warning in pagination.items:
            # 获取学生信息
            student = Student.query.get(warning.student_id)
            student_name = student.name if student else '未知学生'
            student_no = student.student_no if student else ''
            class_name = student.class_.name if student and student.class_ else ''

            metrics = warning.metrics or {}
            
            warnings.append({
                'id': warning.id,
                'student_id': warning.student_id,
                'student_name': student_name,
                'student_no': student_no,
                'class_name': class_name,
                'course_id': warning.course_id,
                'type': warning.type,
                'level': warning.level,
                'reason': warning.reason,
                'metrics': warning.metrics,
                'suggestion': warning.suggestion,
                'status': warning.status,
                'created_at': warning.created_at.isoformat(),
                'attendance_rate': metrics.get('attendance_rate'),
                'assignment_rate': metrics.get('assignment_rate'), # 兼容旧字段名
                'avg_score': metrics.get('avg_score'),
                'score': metrics.get('comprehensive_score')
            })

        # 统计数据 (用于前端卡片数字)
        base_stats_query = Warning.query
        if accessible_course_ids is not None:
            base_stats_query = base_stats_query.filter(Warning.course_id.in_(accessible_course_ids))
        if course_id:
            base_stats_query = base_stats_query.filter(Warning.course_id == course_id)
        if class_id:
            base_stats_query = base_stats_query.join(Student).filter(
                Student.class_id == class_id
            )

        # 统计：活跃预警总数
        total_pending = base_stats_query.filter(
            Warning.status.in_(['active', 'pending'])
        ).count()
        
        # 统计：红色预警数 (活跃的)
        red_count = base_stats_query.filter(
            Warning.status.in_(['active', 'pending']),
            Warning.level == 'red'
        ).count()
        
        # 统计：橙色预警数 (活跃的)
        orange_count = base_stats_query.filter(
            Warning.status.in_(['active', 'pending']),
            Warning.level == 'orange'
        ).count()
        
        # 统计：已处理总数
        resolved_count = base_stats_query.filter(
            Warning.status.in_(['processed', 'ignored'])
        ).count()

        stats = {
            'total': pagination.total,
            'total_pending': total_pending,
            'red_count': red_count,
            'orange_count': orange_count,
            'resolved_count': resolved_count
        }
        
        return jsonify(
            {
            'success': True,
            'warnings': warnings,
            'stats': stats,
            'total': pagination.total,
            'page': page,
            'per_page': per_page
            }
        )

    except Exception as e:
        print(f"获取预警列表失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': '获取预警列表失败'}), 500


@warnings_bp.route('/<int:warning_id>', methods=['GET'])
@role_required(ROLE_ADMIN, ROLE_TEACHER, ROLE_ASSISTANT)
def get_warning_detail(warning_id):
    """获取预警详情"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401

        warning = Warning.query.get(warning_id)
        if not warning:
            return jsonify({'success': False, 'message': '预警不存在'}), 404

        allowed, error = ensure_course_access(warning.course_id, current_user)
        if not allowed:
            message, status = error
            return jsonify({'success': False, 'message': message}), status
        
        student = Student.query.get(warning.student_id)
        student_name = student.name if student else '未知学生'
        student_no = student.student_no if student else ''
        class_name = student.class_.name if student and student.class_ else ''
        
        metrics = warning.metrics or {}

        return jsonify({
            'success': True,
            'warning': {
                'id': warning.id,
                'student_id': warning.student_id,
                'student_name': student_name,
                'student_no': student_no,
                'class_name': class_name,
                'course_id': warning.course_id,
                'type': warning.type,
                'level': warning.level,
                'reason': warning.reason,
                'metrics': warning.metrics,
                'suggestion': warning.suggestion,
                'status': warning.status,
                'created_at': warning.created_at.isoformat(),
                'handled_at': (
                    warning.handled_at.isoformat() if warning.handled_at else None
                ),
                'handled_by': warning.handled_by,
                'handle_note': warning.handle_note,
                'score': metrics.get('comprehensive_score')
            }
        })

    except Exception as e:
        print(f"获取预警详情失败: {str(e)}")
        return jsonify({'success': False, 'message': '获取预警详情失败'}), 500


@warnings_bp.route('/<int:warning_id>/process', methods=['POST'])
@role_required(ROLE_ADMIN, ROLE_TEACHER)
def process_warning(warning_id):
    """处理预警"""
    try:
        warning = Warning.query.get(warning_id)
        if not warning:
            return jsonify({'success': False, 'message': '预警不存在'}), 404
        
        data = request.get_json()
        process_type = data.get('process_type')
        process_detail = data.get('process_detail')
        process_result = data.get('process_result')

        if not process_type or not process_detail or not process_result:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400

        # 更新预警状态
        if process_result == 'resolved':
            warning.status = 'processed'
        elif process_result == 'ignored':
            warning.status = 'ignored'
        else:
            warning.status = 'following' # 持续跟进
            
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401

        allowed, error = ensure_course_access(warning.course_id, current_user)
        if not allowed:
            message, status = error
            return jsonify({'success': False, 'message': message}), status

        warning.handled_by = current_user.id
            
        warning.handled_at = datetime.now()
        warning.handle_note = (
            f"处理方式: {process_type}\n"
            f"处理详情: {process_detail}\n"
            f"处理结果: {process_result}"
        )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '预警处理成功',
            'warning': {
                'id': warning.id,
                'status': warning.status,
                'handled_at': warning.handled_at.isoformat()
            }
        })

    except Exception as e:
        print(f"处理预警失败: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': '处理预警失败'}), 500


@warnings_bp.route('/<int:warning_id>/history', methods=['GET'])
@role_required(ROLE_ADMIN, ROLE_TEACHER, ROLE_ASSISTANT)
def get_warning_history(warning_id):
    """获取预警处理历史"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401

        warning = Warning.query.get(warning_id)
        if not warning:
            return jsonify({'success': False, 'message': '预警不存在'}), 404

        allowed, error = ensure_course_access(warning.course_id, current_user)
        if not allowed:
            message, status = error
            return jsonify({'success': False, 'message': message}), status
        
        # 构建历史记录
        history = []

        # 预警创建记录
        history.append({
            'type': 'created',
            'title': '预警创建',
            'description': f'系统自动生成了{warning.level}级预警',
            'time': warning.created_at.isoformat()
        })

        # 处理记录
        if warning.handled_at:
            history.append({
                'type': 'processed',
                'title': '预警处理',
                'description': warning.handle_note or '已处理该预警',
                'time': warning.handled_at.isoformat()
            })

        return jsonify({
            'success': True,
            'history': history
        })

    except Exception as e:
        print(f"获取预警历史失败: {str(e)}")
        return jsonify({'success': False, 'message': '获取预警历史失败'}), 500


@warnings_bp.route('/generate', methods=['POST'])
@role_required(ROLE_ADMIN, ROLE_TEACHER)
def generate_warnings():
    """手动触发预警生成"""
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'message': '用户不存在或未登录'}), 401

        # 这里应该调用新的 WarningEngine
        from ..services.warning_engine import WarningEngine

        active_before = Warning.query.filter_by(
            type='comprehensive',
            status='active'
        ).count()
        
        courses_query = Course.query
        if current_user.role == ROLE_TEACHER:
            courses_query = courses_query.filter(Course.teacher_id == current_user.id)
        courses = courses_query.all()
        total_generated = 0
        
        for course in courses:
            engine = WarningEngine(course.id)
            warnings = engine.check_all_students()
            total_generated += len(warnings)

        active_after = Warning.query.filter_by(
            type='comprehensive',
            status='active'
        ).count()

        if active_after > active_before:
            summary = f'新增 {active_after - active_before} 条活跃预警'
        elif active_after < active_before:
            summary = f'自动关闭 {active_before - active_after} 条误报/过期预警'
        else:
            summary = '活跃预警数量无变化'

        return jsonify({
            'success': True,
            'message': (
                f'预警检查完成，当前活跃预警 {active_after} 条；'
                f'{summary}。'
            ),
            'data': {
                'generated_count': total_generated,
                'active_before': active_before,
                'active_after': active_after
            }
        })

    except Exception as e:
        print(f"生成预警失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': '生成预警失败'}), 500
