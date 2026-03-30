from . import db
from datetime import datetime


class User(db.Model):
    """教师用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, comment='登录账号')
    password_hash = db.Column(db.String(256), nullable=False, comment='密码哈希')
    name = db.Column(db.String(50), nullable=False, comment='教师姓名')
    email = db.Column(db.String(120), unique=True, comment='邮箱')
    role = db.Column(db.String(20), default='teacher', comment='角色：admin/teacher/assistant')
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_active = db.Column(db.Boolean, default=True)

    # 关系：一个教师有多个课程
    courses = db.relationship('Course', backref='teacher', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
