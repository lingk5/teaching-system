from flask import Blueprint, jsonify, request
from sqlalchemy import func, case
from datetime import datetime, timedelta
from ..models import db, Student, Class
from ..models.data import Attendance, Homework, Quiz, Interaction
from ..models.warning import Warning
from ..services.warning_engine import WarningEngine

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/course/<int:course_id>/overview')
def course_overview(course_id):
    """课程概览数据"""
    # 1. 基础统计
    classes = Class.query.filter_by(course_id=course_id).all()
    class_ids = [c.id for c in classes]
    students = Student.query.filter(Student.class_id.in_(class_ids)).all()
    student_ids = [s.id for s in students]

    if not student_ids:
        return jsonify({
            'success': True,
            'data': {
                'student_count': 0,
                'attendance_rate': 0,
                'homework_completion': 0,
                'avg_quiz_score': 0,
                'score_distribution': [0, 0, 0, 0, 0],
                'class_profile': [0, 0, 0, 0, 0],
                'trend': {'labels': [], 'class_avg': [], 'grade_avg': []},
                'student_ranking': []
            }
        })

    # 计算出勤率
    total_attendance = Attendance.query.filter(Attendance.student_id.in_(student_ids), Attendance.course_id == course_id).count()
    present_count = Attendance.query.filter(Attendance.student_id.in_(student_ids), Attendance.status == 'present', Attendance.course_id == course_id).count()
    attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0

    # 计算作业完成率
    total_homework = Homework.query.filter(Homework.student_id.in_(student_ids), Homework.course_id == course_id).count()
    completed_homework = Homework.query.filter(Homework.student_id.in_(student_ids), Homework.status.in_(['submitted', 'graded']), Homework.course_id == course_id).count()
    homework_completion = (completed_homework / total_homework * 100) if total_homework > 0 else 0

    # 计算平均测验分
    avg_quiz_score = db.session.query(func.avg(Quiz.score)).filter(Quiz.student_id.in_(student_ids), Quiz.course_id == course_id).scalar() or 0

    # 2. 成绩分布 (优秀90+, 良好80-89, 中等70-79, 及格60-69, 不及格<60)
    # 这里以综合预警分数为准，或者以最近一次测验为准。为了简化展示，这里统计所有测验的平均分分布
    score_case = case(
        (Quiz.score >= 90, 'excellent'),
        (Quiz.score >= 80, 'good'),
        (Quiz.score >= 70, 'average'),
        (Quiz.score >= 60, 'pass'),
        else_='fail'
    )
    distribution_query = db.session.query(score_case, func.count(Quiz.id)).filter(
        Quiz.student_id.in_(student_ids), Quiz.course_id == course_id
    ).group_by(score_case).all()
    
    dist_map = {k: v for k, v in distribution_query}
    score_distribution = [
        dist_map.get('excellent', 0),
        dist_map.get('good', 0),
        dist_map.get('average', 0),
        dist_map.get('pass', 0),
        dist_map.get('fail', 0)
    ]

    # 3. 班级能力画像 (出勤, 作业, 互动, 测验, 预习-暂无)
    class_profile = [
        round(attendance_rate, 1),
        round(homework_completion, 1),
        min(
            (
                (db.session.query(func.avg(Interaction.count))
                .filter(
                    Interaction.student_id.in_(student_ids),
                    Interaction.course_id == course_id
                )
                .scalar() or 0) * 10
            ),
            100
        ),
        round(float(avg_quiz_score), 1),
        70 # 预习暂定
    ]

    # 4. 学习趋势 (最近5次测验的平均分)
    recent_quizzes = db.session.query(
        Quiz.title, func.avg(Quiz.score)
    ).filter(
        Quiz.student_id.in_(student_ids), Quiz.course_id == course_id
    ).group_by(Quiz.title).order_by(Quiz.created_at).limit(5).all()
    
    trend_labels = [q[0] for q in recent_quizzes]
    trend_data = [round(q[1], 1) for q in recent_quizzes]

    # 5. 学生排行 (前10名，按测验平均分)
    top_students = db.session.query(
        Student.id, Student.student_no, Student.name, func.avg(Quiz.score).label('avg_score')
    ).join(Quiz).filter(
        Quiz.course_id == course_id, Student.id.in_(student_ids)
    ).group_by(Student.id).order_by(func.avg(Quiz.score).desc()).limit(10).all()

    student_ranking = [{
        'id': s.id,
        'student_no': s.student_no,
        'name': s.name,
        'score': round(s.avg_score, 1)
    } for s in top_students]

    return jsonify({
        'success': True,
        'data': {
            'student_count': len(students),
            'attendance_rate': round(attendance_rate, 1),
            'homework_completion': round(homework_completion, 1),
            'avg_quiz_score': round(float(avg_quiz_score), 1),
            'score_distribution': score_distribution,
            'class_profile': class_profile,
            'trend': {
                'labels': trend_labels,
                'class_avg': trend_data,
                'grade_avg': [d * 0.95 for d in trend_data] # 模拟年级平均
            },
            'student_ranking': student_ranking
        }
    })

@analytics_bp.route('/course/<int:course_id>/students/<int:student_id>/profile')
def student_profile(course_id, student_id):
    """学生个人学习档案"""
    student = Student.query.get_or_404(student_id)
    
    # 重新使用 WarningEngine 计算该生的实时指标
    engine = WarningEngine(course_id)
    metrics = engine._calculate_metrics(student.id)
    score = engine._calculate_comprehensive_score(metrics)

    # 趋势数据
    quizzes = Quiz.query.filter_by(student_id=student.id, course_id=course_id).order_by(Quiz.created_at).limit(10).all()
    trend_labels = [q.title for q in quizzes]
    trend_scores = [q.score for q in quizzes]

    return jsonify({
        'success': True,
        'data': {
            'student': {
                'name': student.name,
                'student_no': student.student_no,
                'class_name': student.class_.name if student.class_ else '',
                'score': round(score, 1)
            },
            'attendance': {'rate': round(metrics['attendance'], 1)},
            'homework': {'avg_score': round(metrics['homework'], 1)},
            'quiz': {'avg_score': round(metrics['quiz'], 1)},
            'interaction': {'total': round(metrics['interaction'], 1)},
            'trend': {
                'labels': trend_labels,
                'scores': trend_scores
            }
        }
    })
