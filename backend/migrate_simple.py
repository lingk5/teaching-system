"""
SQLite -> MySQL 简化迁移脚本（仅核心数据）
"""
import sqlite3
from app import create_app
from app.models import db, User, Course, Class, Student
from sqlalchemy.orm import Session

def migrate_core_data():
    """迁移核心数据：用户、课程、班级、学生"""
    print("=" * 50)
    print("SQLite -> MySQL 核心数据迁移")
    print("=" * 50)
    
    # 连接 SQLite
    sqlite_conn = sqlite3.connect('instance/app.db')
    sqlite_cursor = sqlite_conn.cursor()
    print(f"✅ 已连接到 SQLite: instance/app.db")
    
    # 创建 MySQL 会话
    app = create_app()
    with app.app_context():
        mysql_session = Session(db.engine)
        print("✅ 已连接到 MySQL")
        
        try:
            # 1. 迁移用户（排除默认账号）
            print("\n[1/4] 迁移用户...")
            sqlite_cursor.execute("SELECT * FROM users WHERE username != 'teacher'")
            users = sqlite_cursor.fetchall()
            
            for user in users:
                existing = mysql_session.query(User).filter_by(username=user[1]).first()
                if not existing:
                    new_user = User(
                        username=user[1],
                        password_hash=user[2],
                        name=user[3],
                        email=user[4],
                        role=user[5],
                        created_at=user[6],
                        is_active=user[7]
                    )
                    mysql_session.add(new_user)
                    print(f"  ✓ {user[1]}")
            
            mysql_session.commit()
            print(f"✅ 用户迁移完成：{len(users)} 条")
            
            # 2. 迁移课程
            print("\n[2/4] 迁移课程...")
            sqlite_cursor.execute("SELECT * FROM courses")
            courses = sqlite_cursor.fetchall()
            
            for course in courses:
                # 使用 get 方法替代 query.get
                existing = mysql_session.get(Course, course[0])
                if not existing:
                    new_course = Course(
                        name=course[1],
                        code=course[2],
                        description=course[3] if course[3] else None,
                        semester=course[4] if course[4] else None,
                        teacher_id=course[5],
                        created_at=course[6],
                        is_active=course[7]
                    )
                    mysql_session.add(new_course)
                    print(f"  ✓ {course[1]}")
            
            mysql_session.commit()
            print(f"✅ 课程迁移完成：{len(courses)} 条")
            
            # 3. 迁移班级
            print("\n[3/4] 迁移班级...")
            sqlite_cursor.execute("SELECT * FROM classes")
            classes = sqlite_cursor.fetchall()
            
            for cls in classes:
                existing = mysql_session.get(Class, cls[0])
                if not existing:
                    new_class = Class(
                        name=cls[1],
                        course_id=cls[2],
                        student_count=cls[3] if cls[3] else 0,
                        created_at=cls[4]
                    )
                    mysql_session.add(new_class)
                    print(f"  ✓ {cls[1]}")
            
            mysql_session.commit()
            print(f"✅ 班级迁移完成：{len(classes)} 条")
            
            # 4. 迁移学生
            print("\n[4/4] 迁移学生...")
            sqlite_cursor.execute("SELECT * FROM students")
            students = sqlite_cursor.fetchall()
            
            for student in students:
                existing = mysql_session.get(Student, student[0])
                if not existing:
                    new_student = Student(
                        student_no=student[1],
                        name=student[2],
                        gender=student[3] if student[3] else None,
                        class_id=student[4]
                    )
                    mysql_session.add(new_student)
                    print(f"  ✓ {student[2]} ({student[1]})")
            
            mysql_session.commit()
            print(f"✅ 学生迁移完成：{len(students)} 条")
            
            print("\n" + "=" * 50)
            print("🎉 核心数据迁移完成！")
            print("=" * 50)
            
        except Exception as e:
            print(f"\n❌ 迁移失败：{e}")
            import traceback
            traceback.print_exc()
            mysql_session.rollback()
        
        finally:
            mysql_session.close()
            sqlite_conn.close()


if __name__ == '__main__':
    migrate_core_data()
