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
            
            # 2. 创建/检查默认用户（admin, teacher, assistant）
            default_users = [
                {
                    'username': 'admin',
                    'password': '123456',
                    'name': '系统管理员',
                    'role': 'admin'
                },
                {
                    'username': 'teacher',
                    'password': '123456',
                    'name': '演示教师',
                    'role': 'teacher'
                },
                {
                    'username': 'assistant',
                    'password': '123456',
                    'name': '演示助教',
                    'role': 'assistant'
                }
            ]
            
            created_count = 0
            for user_info in default_users:
                existing_user = User.query.filter_by(username=user_info['username']).first()
                if not existing_user:
                    user = User(
                        username=user_info['username'],
                        password_hash=generate_password_hash(user_info['password']),
                        name=user_info['name'],
                        email='',
                        role=user_info['role']
                    )
                    db.session.add(user)
                    created_count += 1
                    print(f"✅ 创建账号：{user_info['username']} / 123456 ({user_info['role']})")
                else:
                    # 如果用户已存在，更新角色信息以确保正确
                    if existing_user.role != user_info['role']:
                        existing_user.role = user_info['role']
                        print(f"🔄 更新账号角色：{user_info['username']} -> {user_info['role']}")
            
            if created_count > 0:
                db.session.commit()
                print(f"✅ 已创建 {created_count} 个新账号")
            else:
                print("✅ 所有默认账号已存在")
            
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
