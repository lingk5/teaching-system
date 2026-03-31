from . import db
from datetime import datetime


class Course(db.Model):
    """课程表"""
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment='课程名称')
    code = db.Column(db.String(20), unique=True, comment='课程代码')
    description = db.Column(db.Text, comment='课程描述')
    semester = db.Column(db.String(20), comment='学期，如：2025-2026-1')
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_active = db.Column(db.Boolean, default=True)

    # 关系
    classes = db.relationship('Class', backref='course', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'semester': self.semester,
            'teacher_id': self.teacher_id,
            'class_count': len(self.classes)
        }


class Class(db.Model):
    """班级表（一个课程下有多个班级）"""
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, comment='班级名称，如：计算机9班')
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    student_count = db.Column(db.Integer, default=0, comment='学生人数')
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 关系
    students = db.relationship('Student', backref='class_', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'course_id': self.course_id,
            'student_count': len(self.students)
        }


class Student(db.Model):
    """学生表"""
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_no = db.Column(db.String(20), unique=True, nullable=False, comment='学号')
    name = db.Column(db.String(50), nullable=False, comment='姓名')
    gender = db.Column(db.String(10), comment='性别')
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 关系
    attendances = db.relationship('Attendance', backref='student', lazy=True)
    homeworks = db.relationship('Homework', backref='student', lazy=True)
    quizzes = db.relationship('Quiz', backref='student', lazy=True)
    final_scores = db.relationship('FinalScore', backref='student', lazy=True)
    interactions = db.relationship('Interaction', backref='student', lazy=True)
    warnings = db.relationship('Warning', backref='student', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'student_no': self.student_no,
            'name': self.name,
            'gender': self.gender,
            'class_id': self.class_id
        }
