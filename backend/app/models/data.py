from . import db
from datetime import datetime, date


class Attendance(db.Model):
    """出勤记录表"""
    __tablename__ = 'attendances'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, comment='日期')
    status = db.Column(db.String(20), nullable=False, comment='状态：present/absent/late/leave')
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    remark = db.Column(db.String(200), comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'date': self.date.strftime('%Y-%m-%d'),
            'status': self.status,
            'remark': self.remark
        }


class Homework(db.Model):
    """作业记录表"""
    __tablename__ = 'homeworks'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False, comment='作业标题')
    score = db.Column(db.Float, comment='得分')
    max_score = db.Column(db.Float, default=100, comment='满分')
    submit_time = db.Column(db.DateTime, comment='提交时间')
    deadline = db.Column(db.DateTime, comment='截止时间')
    status = db.Column(db.String(20), default='submitted', comment='状态：submitted/missing/late')
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'title': self.title,
            'score': self.score,
            'max_score': self.max_score,
            'status': self.status,
            'submit_time': self.submit_time.strftime('%Y-%m-%d %H:%M') if self.submit_time else None
        }


class Quiz(db.Model):
    """测验记录表"""
    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False, comment='测验名称')
    score = db.Column(db.Float, comment='得分')
    max_score = db.Column(db.Float, default=100, comment='满分')
    duration = db.Column(db.Integer, comment='用时（分钟）')
    submit_time = db.Column(db.DateTime, comment='提交时间')
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'title': self.title,
            'score': self.score,
            'max_score': self.max_score,
            'duration': self.duration
        }


class Interaction(db.Model):
    """课堂互动记录表"""
    __tablename__ = 'interactions'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    type = db.Column(db.String(50), comment='互动类型：question/discussion/click/like')
    count = db.Column(db.Integer, default=1, comment='互动次数')
    date = db.Column(db.Date, default=date.today, comment='日期')
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'type': self.type,
            'count': self.count,
            'date': self.date.strftime('%Y-%m-%d')
        }
