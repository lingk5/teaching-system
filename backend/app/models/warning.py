from . import db
from datetime import datetime


class Warning(db.Model):
    """预警记录表"""
    __tablename__ = 'warnings'
    __table_args__ = (
        db.Index('idx_warning_course_status_level', 'course_id', 'status', 'level'),
        db.Index('idx_warning_student_created', 'student_id', 'created_at'),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)

    # 预警指标
    type = db.Column(db.String(50), nullable=False, comment='类型：attendance/homework/quiz/comprehensive')
    level = db.Column(db.String(20), nullable=False, comment='等级：yellow/orange/red')

    # 触发原因（可解释性）
    reason = db.Column(db.Text, nullable=False, comment='触发原因描述')
    metrics = db.Column(db.JSON, comment='具体指标数据，如：{"attendance_rate": 0.65, "threshold": 0.70}')

    # 干预建议
    suggestion = db.Column(db.Text, comment='干预建议')

    # 处理状态
    status = db.Column(db.String(20), default='active', comment='状态：active/processed/ignored')
    handled_by = db.Column(db.Integer, db.ForeignKey('users.id'), comment='处理人')
    handled_at = db.Column(db.DateTime, comment='处理时间')
    handle_note = db.Column(db.Text, comment='处理备注')

    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student.name if self.student else None,
            'type': self.type,
            'level': self.level,
            'reason': self.reason,
            'metrics': self.metrics,
            'suggestion': self.suggestion,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
