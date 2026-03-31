from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 直接导入所有模型（不要延迟导入）
from .user import User
from .course import Course, Class, Student
from .data import Attendance, Homework, Quiz, Interaction
from .warning import Warning
from .assistant_assignment import AssistantCourseAssignment
