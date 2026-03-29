from flask import Flask, jsonify, redirect
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from .routes.export import export_bp


# 初始化扩展（放在全局，但要在 create_app 中 init）
jwt = JWTManager()

def create_app():
    """应用工厂"""
    basedir = os.path.abspath(os.path.dirname(__file__))
    # 设置静态文件根目录为 frontend/src，这样可以同时访问 js 和 pages
    frontend_src = os.path.abspath(os.path.join(basedir, '..', '..', 'frontend', 'src'))
    app = Flask(__name__, static_folder=frontend_src, static_url_path='')

    # 配置 - MySQL 版本
    # 方式 1: 使用环境变量（推荐生产环境）
    db_uri = os.getenv('DATABASE_URI')
    if not db_uri:
        # 方式 2: 默认使用 MySQL（本地开发）
        db_user = os.getenv('DB_USER', 'root')
        db_password = os.getenv('DB_PASSWORD', '12345678')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '3306')
        db_name = os.getenv('DB_NAME', 'teaching_system')
        db_uri = f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

    def detect_database_name(uri):
        if not uri:
            return 'Unknown'
        lowered = uri.lower()
        if lowered.startswith('mysql'):
            return 'MySQL'
        if lowered.startswith('sqlite'):
            return 'SQLite'
        if lowered.startswith('postgresql'):
            return 'PostgreSQL'
        return uri.split(':', 1)[0]

    # 初始化扩展
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    jwt.init_app(app)

    # 导入并初始化数据库（必须在 CORS 之后，避免循环导入）
    from .models import db
    db.init_app(app)

    # 导入模型（用于创建表和统计接口）
    from .models import User, Course, Class, Student
    from .models.data import Attendance, Homework, Quiz, Interaction
    from .models.warning import Warning

    # 注册蓝图
    from .routes.auth import auth_bp
    from .routes.courses import courses_bp
    from .routes.data import data_bp
    from .routes.analytics import analytics_bp
    
    try:
        from .routes.warnings import warnings_bp
        app.register_blueprint(warnings_bp, url_prefix='/api/warnings')
    except ImportError:
        print("⚠️ warnings蓝图未找到，跳过注册")

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(courses_bp, url_prefix='/api/courses')
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(export_bp, url_prefix='/api/export')

    # 创建数据库表
    with app.app_context():
        # MySQL 不需要创建目录，但保留这个逻辑以防万一
        # os.makedirs(os.path.join(basedir, '..', 'instance'), exist_ok=True)
        db.create_all()
        print("✅ 数据库表创建成功")

        if not User.query.filter_by(username='teacher').first():
            from werkzeug.security import generate_password_hash
            default_user = User(
                username='teacher',
                password_hash=generate_password_hash('123456'),
                name='演示教师',
                role='teacher'
            )
            db.session.add(default_user)
            db.session.commit()
            print("✅ 默认账号创建成功：teacher / 123456")

    # 前端页面路由 - 统一指向 pages 目录下的文件
    @app.route('/')
    @app.route('/login')
    @app.route('/login.html')
    def login_page():
        return app.send_static_file('pages/login.html')

    @app.route('/dashboard')
    @app.route('/dashboard.html')
    def dashboard_page():
        return app.send_static_file('pages/dashboard.html')

    @app.route('/courses')
    @app.route('/courses.html')
    def courses_page():
        return app.send_static_file('pages/courses.html')

    @app.route('/students')
    @app.route('/students.html')
    def students_page():
        return app.send_static_file('pages/students.html')

    @app.route('/data-import')
    @app.route('/data-import.html')
    def data_import_page():
        return app.send_static_file('pages/data-import.html')

    @app.route('/analytics')
    @app.route('/analytics.html')
    def analytics_page():
        return app.send_static_file('pages/analytics.html')

    @app.route('/warnings')
    @app.route('/warnings.html')
    def warnings_page():
        return app.send_static_file('pages/warnings.html')

    # 健康检查路由
    @app.route('/api/hello')
    def hello():
        return jsonify({
            "success": True,
            "message": "教学效果监督系统后端运行正常！",
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/status')
    def status():
        # 基础计数
        total_attendance = Attendance.query.count()
        present_count    = Attendance.query.filter_by(status='present').count()
        total_homework   = Homework.query.count()
        completed_hw     = Homework.query.filter(
            Homework.status.in_(['submitted', 'graded'])
        ).count()

        attendance_rate = round(present_count / total_attendance * 100, 1) if total_attendance > 0 else None
        homework_rate   = round(completed_hw / total_homework * 100, 1) if total_homework > 0 else None

        # 预警分布 (红/橙/黄/正常)
        total_students = Student.query.count()
        warn_red    = Warning.query.filter_by(level='red').count()
        warn_orange = Warning.query.filter_by(level='orange').count()
        warn_yellow = Warning.query.filter_by(level='yellow').count()
        normal_count = max(total_students - warn_red - warn_orange - warn_yellow, 0)

        stats = {
            'users':           User.query.count(),
            'courses':         Course.query.count(),
            'classes':         Class.query.count(),
            'students':        total_students,
            'attendances':     total_attendance,
            'homeworks':       total_homework,
            'quizzes':         Quiz.query.count(),
            'interactions':    Interaction.query.count(),
            'warnings':        Warning.query.count(),
            # 新增：仪表盘卡片需要的聚合字段
            'attendance_rate': attendance_rate,   # None 表示暂无数据
            'homework_rate':   homework_rate,
            'warning_distribution': {
                'red':    warn_red,
                'orange': warn_orange,
                'yellow': warn_yellow,
                'normal': normal_count
            }
        }
        return jsonify({
            "status": "running",
            "database": detect_database_name(app.config.get('SQLALCHEMY_DATABASE_URI')),
            "stats": stats,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    return app
