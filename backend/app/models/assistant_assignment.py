from datetime import datetime

from . import db


class AssistantCourseAssignment(db.Model):
    """助教课程指派关系表（教师指派，管理员可补救调整）"""
    __tablename__ = 'assistant_course_assignments'
    __table_args__ = (
        db.UniqueConstraint('assistant_id', 'course_id', name='uq_assistant_course'),
        db.Index('idx_assignment_course', 'course_id'),
        db.Index('idx_assignment_assistant', 'assistant_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    assistant_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        comment='助教用户ID'
    )
    course_id = db.Column(
        db.Integer,
        db.ForeignKey('courses.id', ondelete='CASCADE'),
        nullable=False,
        comment='课程ID'
    )
    assigned_by = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        comment='指派人(教师/管理员)'
    )
    assigned_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'assistant_id': self.assistant_id,
            'course_id': self.course_id,
            'assigned_by': self.assigned_by,
            'assigned_at': self.assigned_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
