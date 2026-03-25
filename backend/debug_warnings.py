from app import create_app, db
from app.models import Warning, Student
from sqlalchemy.orm import joinedload

app = create_app()

with app.app_context():
    print("=== 开始调试预警查询逻辑 ===")
    
    # 模拟前端传参
    course_id = 1
    # 先找一个存在的班级ID
    student = Student.query.first()
    if not student:
        print("错误：数据库中没有学生数据，无法测试")
        exit()
    class_id = student.class_id
    
    level = 'red'
    status = 'active'
    
    print(f"测试参数: course_id={course_id}, class_id={class_id}, level={level}, status={status}")
    
    # 1. 模拟统计查询 (Stats Query)
    base_stats_query = Warning.query
    if course_id:
        base_stats_query = base_stats_query.filter(Warning.course_id == course_id)
    if class_id:
        base_stats_query = base_stats_query.join(Student).filter(
            Student.class_id == class_id
        )
        
    red_count = base_stats_query.filter(
        Warning.status.in_(['active', 'pending']),
        Warning.level == 'red'
    ).count()
    
    print(f"统计查询结果 (Red Count): {red_count}")
    
    # 2. 模拟列表查询 (List Query)
    query = Warning.query
    if course_id:
        query = query.filter(Warning.course_id == course_id)
    if class_id:
        query = query.join(Student).filter(Student.class_id == class_id)
    
    # 按等级筛选
    if level:
        query = query.filter_by(level=level)
        
    # 按状态筛选
    if status == 'active':
        query = query.filter(Warning.status.in_(['active', 'pending']))
        
    list_count = query.count()
    print(f"列表查询结果 (List Count): {list_count}")
    
    print(f"生成的 SQL: {query}")
    
    if red_count != list_count:
        print("!!! 发现问题：统计数量与列表数量不一致！")
    else:
        print("逻辑看起来是正确的，数量一致。")

