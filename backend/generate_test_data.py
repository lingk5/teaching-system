import pandas as pd
import os
import random
from datetime import datetime, timedelta

# 确保输出目录存在
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'test_data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_students():
    """生成学生名单"""
    data = []
    # 生成2个班级，每班5人
    for class_idx in range(1, 3):
        class_name = f"计算机240{class_idx}班"
        for i in range(1, 6):
            # 20240101, 20240102...
            student_no = f"2024{class_idx:02d}{i:02d}"
            name = f"学生{class_idx}-{i}"
            gender = random.choice(['男', '女'])
            data.append({
                'student_no': student_no,
                'name': name,
                'gender': gender,
                'class_name': class_name
            })
    
    df = pd.DataFrame(data)
    file_path = os.path.join(OUTPUT_DIR, '1_students.xlsx')
    df.to_excel(file_path, index=False)
    print(f"✅ 学生名单已生成: {file_path}")
    return df

def generate_scores(students_df):
    """生成成绩数据 (作业 + 测验)"""
    data = []
    
    # 模拟3次作业，2次测验
    tasks = [
        {'title': 'Python基础语法作业', 'type': 'homework', 'max': 100},
        {'title': '函数与模块作业', 'type': 'homework', 'max': 100},
        {'title': '期中项目', 'type': 'homework', 'max': 100},
        {'title': '第一次月考', 'type': 'quiz', 'max': 100, 'duration': 60},
        {'title': '期中考试', 'type': 'quiz', 'max': 100, 'duration': 90},
    ]
    
    base_date = datetime.now() - timedelta(days=60)
    
    for idx, student in students_df.iterrows():
        # 故意制造差生 (每班第1号学生是学霸，第5号是学渣)
        student_idx = int(student['student_no'][-2:])
        
        for task_idx, task in enumerate(tasks):
            # 学霸分高，学渣分低
            if student_idx == 1:
                score = random.randint(90, 100)
            elif student_idx == 5:
                score = random.randint(40, 65) # 容易触发红色/橙色预警
            else:
                score = random.randint(70, 95)
                
            data.append({
                'student_no': student['student_no'],
                'title': task['title'],
                'score': score,
                'max_score': task['max'],
                'type': task['type'],
                'duration': task.get('duration', ''),
                'status': 'graded',
                'date': (base_date + timedelta(days=task_idx*10)).strftime('%Y-%m-%d')
            })
            
    df = pd.DataFrame(data)
    file_path = os.path.join(OUTPUT_DIR, '2_scores.xlsx')
    df.to_excel(file_path, index=False)
    print(f"✅ 成绩数据已生成: {file_path}")

def generate_attendance(students_df):
    """生成考勤数据"""
    data = []
    base_date = datetime.now() - timedelta(days=30)
    
    # 模拟10次考勤
    for i in range(10):
        date = (base_date + timedelta(days=i*3)).strftime('%Y-%m-%d')
        
        for idx, student in students_df.iterrows():
            student_idx = int(student['student_no'][-2:])
            
            # 学渣经常缺勤
            if student_idx == 5:
                status = random.choice(['absent', 'late', 'leave', 'present'])
            # 普通人偶尔迟到
            elif student_idx == 4:
                status = random.choice(['present', 'present', 'present', 'late'])
            else:
                status = 'present'
                
            data.append({
                'student_no': student['student_no'],
                'date': date,
                'status': status,
                'remark': '病假' if status == 'leave' else ''
            })
            
    df = pd.DataFrame(data)
    file_path = os.path.join(OUTPUT_DIR, '3_attendance.xlsx')
    df.to_excel(file_path, index=False)
    print(f"✅ 考勤数据已生成: {file_path}")

if __name__ == '__main__':
    print("正在生成测试数据...")
    students = generate_students()
    generate_scores(students)
    generate_attendance(students)
    print("\n所有文件已生成在 backend/test_data 目录下！")
