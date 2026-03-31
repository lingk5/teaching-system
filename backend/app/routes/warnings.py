from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from ..models import db, Warning, Student, Course
from ..models.data import Attendance, Homework, Quiz
from ..utils.permissions import current_user_can
from datetime import datetime

warnings_bp = Blueprint('warnings', __name__)


@warnings_bp.route('/', methods=['GET'])
@jwt_required()
def get_warnings():
    """获取预警列表"""
    try:
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

        # 按课程筛选
        if course_id:
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
@jwt_required()
def get_warning_detail(warning_id):
    """获取预警详情"""
    try:
        warning = Warning.query.get(warning_id)
        if not warning:
            return jsonify({'success': False, 'message': '预警不存在'}), 404
        
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
@jwt_required()
def process_warning(warning_id):
    """处理预警"""
    if not current_user_can('process_warnings'):
        return jsonify({'success': False, 'message': '助教无权限处理预警'}), 403

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
            
        # 兼容处理 handled_by，如果是对象取 ID
        current_user = get_jwt_identity()
        user_id = current_user.get('id') if isinstance(current_user, dict) else current_user
        
        try:
            warning.handled_by = int(user_id)
        except:
            pass # 如果转换失败保持 None
            
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
@jwt_required()
def get_warning_history(warning_id):
    """获取预警处理历史"""
    try:
        warning = Warning.query.get(warning_id)
        if not warning:
            return jsonify({'success': False, 'message': '预警不存在'}), 404
        
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
@jwt_required()
def generate_warnings():
    """手动触发预警生成"""
    if not current_user_can('generate_warnings'):
        return jsonify({'success': False, 'message': '助教无权限触发预警生成'}), 403

    try:
        # 这里应该调用新的 WarningEngine
        from ..services.warning_engine import WarningEngine
        
        # 简单起见，对所有课程执行检查
        # 实际场景可能需要根据当前教师的课程来检查
        courses = Course.query.all()
        total_generated = 0
        
        for course in courses:
            engine = WarningEngine(course.id)
            warnings = engine.check_all_students()
            total_generated += len(warnings)

        return jsonify({
            'success': True,
            'message': f'预警检查完成，更新了 {total_generated} 条预警记录'
        })

    except Exception as e:
        print(f"生成预警失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': '生成预警失败'}), 500
