"""
SQLite -> MySQL 数据迁移脚本
功能：将旧数据库（SQLite）的数据迁移到新数据库（MySQL）
"""
import sqlite3
from app import create_app
from app.models import db, User, Course, Class, Student
from app.models.data import Attendance, Homework, Quiz, Interaction
from app.models.warning import Warning
from sqlalchemy import text
import json

def migrate_data():
    """执行数据迁移"""
    print("=" * 50)
    print("SQLite -> MySQL 数据迁移工具")
    print("=" * 50)
    
    # 1. 连接 SQLite 数据库
    sqlite_db_path = 'instance/app.db'
    try:
        sqlite_conn = sqlite3.connect(sqlite_db_path)
        sqlite_cursor = sqlite_conn.cursor()
        print(f"✅ 已连接到 SQLite 数据库：{sqlite_db_path}")
    except Exception as e:
        print(f"❌ 无法连接 SQLite 数据库：{e}")
        return
    
    # 2. 创建 MySQL 会话
    try:
        app = create_app()
        with app.app_context():
            mysql_session = db.session
            print("✅ 已连接到 MySQL 数据库")
            
            # 3. 开始迁移
            print("\n📊 开始迁移数据...")
            
            # 3.1 迁移用户表
            print("\n[1/7] 迁移用户数据...")
            sqlite_cursor.execute("SELECT * FROM users")
            users = sqlite_cursor.fetchall()
            
            for user in users:
                # 检查是否已存在（用 username 而不是 id）
                existing = User.query.filter_by(username=user[1]).first()
                if not existing:
                    try:
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
                        print(f"  ✓ 添加用户：{user[1]}")
                    except Exception as e:
                        print(f"  ⚠️  用户 {user[1]} 添加失败：{e}")
                        continue
            
            mysql_session.commit()
            print(f"✅ 用户迁移完成，共 {len(users)} 条")
            
            # 3.2 迁移课程表
            print("\n[2/7] 迁移课程数据...")
            sqlite_cursor.execute("SELECT * FROM courses")
            courses = sqlite_cursor.fetchall()
            
            for course in courses:
                existing = Course.query.get(course[0])
                if not existing:
                    new_course = Course(
                        id=course[0],
                        name=course[1],
                        code=course[2],
                        description=course[3],
                        semester=course[4],
                        teacher_id=course[5],
                        created_at=course[6],
                        is_active=course[7]
                    )
                    mysql_session.add(new_course)
                    print(f"  ✓ 添加课程：{course[1]}")
            
            mysql_session.commit()
            print(f"✅ 课程迁移完成，共 {len(courses)} 条")
            
            # 3.3 迁移班级表
            print("\n[3/7] 迁移班级数据...")
            sqlite_cursor.execute("SELECT * FROM classes")
            classes = sqlite_cursor.fetchall()
            
            for cls in classes:
                existing = Class.query.get(cls[0])
                if not existing:
                    new_class = Class(
                        id=cls[0],
                        name=cls[1],
                        course_id=cls[2],
                        student_count=cls[3],
                        created_at=cls[4]
                    )
                    mysql_session.add(new_class)
                    print(f"  ✓ 添加班级：{cls[1]}")
            
            mysql_session.commit()
            print(f"✅ 班级迁移完成，共 {len(classes)} 条")
            
            # 3.4 迁移学生表
            print("\n[4/7] 迁移学生数据...")
            sqlite_cursor.execute("SELECT * FROM students")
            students = sqlite_cursor.fetchall()
            
            for student in students:
                existing = Student.query.get(student[0])
                if not existing:
                    new_student = Student(
                        id=student[0],
                        student_no=student[1],
                        name=student[2],
                        gender=student[3],
                        class_id=student[4],
                        created_at=student[5]
                    )
                    mysql_session.add(new_student)
                    print(f"  ✓ 添加学生：{student[2]} ({student[1]})")
            
            mysql_session.commit()
            print(f"✅ 学生迁移完成，共 {len(students)} 条")
            
            # 3.5 迁移考勤数据
            print("\n[5/7] 迁移考勤数据...")
            sqlite_cursor.execute("SELECT * FROM attendances")
            attendances = sqlite_cursor.fetchall()
            
            for att in attendances:
                existing = Attendance.query.get(att[0])
                if not existing:
                    new_attendance = Attendance(
                        id=att[0],
                        student_id=att[1],
                        date=att[2],
                        status=att[3],
                        course_id=att[4],
                        remark=att[5],
                        created_at=att[6]
                    )
                    mysql_session.add(new_attendance)
            
            mysql_session.commit()
            print(f"✅ 考勤数据迁移完成，共 {len(attendances)} 条")
            
            # 3.6 迁移作业数据
            print("\n[6/7] 迁移作业数据...")
            sqlite_cursor.execute("SELECT * FROM homeworks")
            homeworks = sqlite_cursor.fetchall()
            
            for hw in homeworks:
                existing = Homework.query.get(hw[0])
                if not existing:
                    new_homework = Homework(
                        id=hw[0],
                        student_id=hw[1],
                        title=hw[2],
                        score=hw[3],
                        max_score=hw[4],
                        submit_time=hw[5],
                        deadline=hw[6],
                        status=hw[7],
                        course_id=hw[8],
                        created_at=hw[9]
                    )
                    mysql_session.add(new_homework)
            
            mysql_session.commit()
            print(f"✅ 作业数据迁移完成，共 {len(homeworks)} 条")
            
            # 3.7 迁移测验数据
            print("\n[7/7] 迁移测验数据...")
            sqlite_cursor.execute("SELECT * FROM quizzes")
            quizzes = sqlite_cursor.fetchall()
            
            for quiz in quizzes:
                existing = Quiz.query.get(quiz[0])
                if not existing:
                    new_quiz = Quiz(
                        id=quiz[0],
                        student_id=quiz[1],
                        title=quiz[2],
                        score=quiz[3],
                        max_score=quiz[4],
                        duration=quiz[5],
                        submit_time=quiz[6],
                        course_id=quiz[7],
                        created_at=quiz[8]
                    )
                    mysql_session.add(new_quiz)
            
            mysql_session.commit()
            print(f"✅ 测验数据迁移完成，共 {len(quizzes)} 条")
            
            # 可选：迁移互动和预警数据
            print("\n[可选] 迁移互动数据...")
            sqlite_cursor.execute("SELECT * FROM interactions")
            interactions = sqlite_cursor.fetchall()
            
            for inter in interactions:
                existing = Interaction.query.get(inter[0])
                if not existing:
                    new_interaction = Interaction(
                        id=inter[0],
                        student_id=inter[1],
                        type=inter[2],
                        count=inter[3],
                        date=inter[4],
                        course_id=inter[5],
                        created_at=inter[6]
                    )
                    mysql_session.add(new_interaction)
            
            mysql_session.commit()
            print(f"✅ 互动数据迁移完成，共 {len(interactions)} 条")
            
            print("\n[可选] 迁移预警数据...")
            sqlite_cursor.execute("SELECT * FROM warnings")
            warnings = sqlite_cursor.fetchall()
            
            for warning in warnings:
                existing = Warning.query.get(warning[0])
                if not existing:
                    # metrics 字段可能是 JSON 字符串
                    metrics = warning[6]
                    if isinstance(metrics, str):
                        try:
                            metrics = json.loads(metrics)
                        except:
                            metrics = None
                    
                    new_warning = Warning(
                        id=warning[0],
                        student_id=warning[1],
                        course_id=warning[2],
                        type=warning[3],
                        level=warning[4],
                        reason=warning[5],
                        metrics=metrics,
                        suggestion=warning[7],
                        status=warning[8],
                        handled_by=warning[9],
                        handled_at=warning[10],
                        handle_note=warning[11],
                        created_at=warning[12]
                    )
                    mysql_session.add(new_warning)
            
            mysql_session.commit()
            print(f"✅ 预警数据迁移完成，共 {len(warnings)} 条")
            
            print("\n" + "=" * 50)
            print("🎉 数据迁移完成！")
            print("=" * 50)
            print(f"\n统计信息:")
            print(f"  - 用户：{len(users)}")
            print(f"  - 课程：{len(courses)}")
            print(f"  - 班级：{len(classes)}")
            print(f"  - 学生：{len(students)}")
            print(f"  - 考勤：{len(attendances)}")
            print(f"  - 作业：{len(homeworks)}")
            print(f"  - 测验：{len(quizzes)}")
            print(f"  - 互动：{len(interactions)}")
            print(f"  - 预警：{len(warnings)}")
            
    except Exception as e:
        print(f"\n❌ 迁移过程出错：{e}")
        import traceback
        traceback.print_exc()
        mysql_session.rollback()
    
    finally:
        sqlite_conn.close()


if __name__ == '__main__':
    migrate_data()
