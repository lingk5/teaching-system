"""
MySQL 数据库初始化脚本
功能：在 MySQL 中创建所有表结构和初始数据
"""
from app import create_app
from app.models import db, User, Course, Class, Student
from app.models.data import Attendance, Homework, Quiz, Interaction
from app.models.warning import Warning
from werkzeug.security import generate_password_hash

def init_database():
    """初始化 MySQL 数据库"""
    print("=" * 50)
    print("MySQL 数据库初始化")
    print("=" * 50)
    
    try:
        app = create_app()
        with app.app_context():
            # 1. 创建所有表
            print("\n📋 创建数据库表...")
            db.create_all()
            print("✅ 所有表创建成功")
            
            # 2. 检查是否已有默认用户
            default_user = User.query.filter_by(username='teacher').first()
            if not default_user:
                print("\n👤 创建默认管理员账号...")
                user = User(
                    username='teacher',
                    password_hash=generate_password_hash('123456'),
                    name='演示教师',
                    email='',
                    role='teacher'
                )
                db.session.add(user)
                db.session.commit()
                print("✅ 默认账号创建成功：teacher / 123456")
            else:
                print("\n✅ 默认账号已存在：teacher / 123456")
            
            # 3. 显示连接信息
            print("\n" + "=" * 50)
            print("数据库配置信息:")
            print(f"  - URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
            print(f"  - 表数量：{len(db.metadata.tables)}")
            print("\n表清单:")
            for table_name in sorted(db.metadata.tables.keys()):
                print(f"  ✓ {table_name}")
            
            print("\n" + "=" * 50)
            print("🎉 数据库初始化完成！")
            print("=" * 50)
            
    except Exception as e:
        print(f"\n❌ 初始化失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    init_database()
