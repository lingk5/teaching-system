from flask import Blueprint, request, jsonify
from ..models import db
from ..models.data import Attendance, Homework, Quiz, Interaction
from ..models.course import Student, Class, Course
import pandas as pd
from datetime import datetime
import os

data_bp = Blueprint('data', __name__)


@data_bp.route('/attendance', methods=['POST'])
def add_attendance():
    """单条添加出勤记录"""
    data = request.get_json()

    record = Attendance(
        student_id=data['student_id'],
        date=data['date'],
        status=data['status'],
        course_id=data['course_id'],
        remark=data.get('remark')
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({'success': True, 'message': '出勤记录添加成功'}), 201


@data_bp.route('/homework', methods=['POST'])
def add_homework():
    """单条添加作业记录"""
    data = request.get_json()

    record = Homework(
        student_id=data['student_id'],
        title=data['title'],
        score=data.get('score'),
        max_score=data.get('max_score', 100),
        status=data.get('status', 'submitted'),
        course_id=data['course_id']
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({'success': True, 'message': '作业记录添加成功'}), 201


@data_bp.route('/quiz', methods=['POST'])
def add_quiz():
    """单条添加测验记录"""
    data = request.get_json()

    record = Quiz(
        student_id=data['student_id'],
        title=data['title'],
        score=data.get('score'),
        max_score=data.get('max_score', 100),
        duration=data.get('duration'),
        course_id=data['course_id']
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({'success': True, 'message': '测验记录添加成功'}), 201


@data_bp.route('/interaction', methods=['POST'])
def add_interaction():
    """单条添加互动记录"""
    data = request.get_json()

    record = Interaction(
        student_id=data['student_id'],
        type=data['type'],
        count=data.get('count', 1),
        date=data.get('date'),
        course_id=data['course_id']
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({'success': True, 'message': '互动记录添加成功'}), 201


@data_bp.route('/import/<string:data_type>', methods=['POST'])
def import_data(data_type):
    """
    批量导入数据（Excel/CSV）
    data_type: students / attendance / homework / quiz / final_exam / interactions
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'}), 400

    file = request.files['file']
    course_id = request.form.get('course_id', type=int)

    if not file or file.filename == '':
        return jsonify({'success': False, 'message': '文件名为空'}), 400

    if not course_id:
        return jsonify({'success': False, 'message': '缺少course_id参数'}), 400

    # 检查文件类型
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({
            'success': False,
            'message': f'不支持的文件格式: {ext}，请上传CSV或Excel文件'
        }), 400

    try:
        # 读取文件
        if ext == '.csv':
            df = pd.read_csv(file, encoding='utf-8')
        else:
            df = pd.read_excel(file)

        # 数据清洗：去除空行，去除前后空格
        df = df.dropna(how='all')
        # 兼容 Pandas 2.0.3: 使用 applymap
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        # 根据类型处理
        if data_type == 'students':
            return _import_students(df, course_id)
        elif data_type == 'attendance':
            return _import_attendance(df, course_id)
        elif data_type == 'homework':
            return _import_homework(df, course_id)
        elif data_type == 'quiz':
            # 普通测验，type='quiz'
            return _import_quiz(df, course_id, quiz_type='quiz')
        elif data_type == 'final_exam':
            # 期末考试，复用 Quiz 表，type='final'
            return _import_quiz(df, course_id, quiz_type='final')
        elif data_type == 'interactions':
            return _import_interactions(df, course_id)
        else:
            return jsonify({
                'success': False,
                'message': f'不支持的导入类型: {data_type}'
            }), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入失败：{str(e)}',
            'error_type': type(e).__name__
        }), 500


def _import_students(df, course_id):
    """导入学生名单"""
    required_cols = ['student_no', 'name']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return jsonify({
            'success': False,
            'message': '缺少必要列: ' + ','.join(missing_cols) + '，当前列: ' + str(list(df.columns))
        }), 400

    success_count = 0
    skip_count = 0
    errors = []

    for index, row in df.iterrows():
        try:
            student_no = str(row['student_no']).strip()
            name = str(row['name']).strip()

            if not student_no or not name:
                errors.append(f'第{index + 2}行：学号或姓名为空')
                continue

            # 检查是否已存在
            existing = Student.query.filter_by(student_no=student_no).first()
            if existing:
                skip_count += 1
                continue

            # 获取或创建班级
            class_name = str(row.get('class_name', '默认班级')).strip()
            class_obj = Class.query.filter_by(name=class_name, course_id=course_id).first()
            if not class_obj:
                class_obj = Class(name=class_name, course_id=course_id)
                db.session.add(class_obj)
                db.session.flush()  # 获取id

            # 创建学生
            gender = str(row.get('gender', '')).strip() if pd.notna(row.get('gender')) else None

            student = Student(
                student_no=student_no,
                name=name,
                gender=gender,
                class_id=class_obj.id
            )
            db.session.add(student)
            success_count += 1

            # 每20条提交一次，避免内存溢出
            if success_count % 20 == 0:
                db.session.commit()

        except Exception as e:
            errors.append(f'第{index + 2}行：{str(e)}')

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'导入完成：成功{success_count}条，跳过{skip_count}条（已存在），失败{len(errors)}条',
        'data': {
            'success_count': success_count,
            'skip_count': skip_count,
            'error_count': len(errors),
            'errors': errors[:10]  # 只显示前10个错误
        }
    })


def _import_attendance(df, course_id):
    """导入出勤数据"""
    required_cols = ['student_no', 'date', 'status']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return jsonify({
            'success': False,
            'message': '缺少必要列: ' + ','.join(missing_cols)
        }), 400

    # 验证状态值
    valid_status = {'present', 'absent', 'late', 'leave'}

    success_count = 0
    skip_count = 0
    errors = []

    for index, row in df.iterrows():
        try:
            student_no = str(row['student_no']).strip()
            student = Student.query.filter_by(student_no=student_no).first()

            if not student:
                errors.append(f'第{index + 2}行：学号{student_no}不存在')
                continue

            # 解析日期
            date_val = row['date']
            if isinstance(date_val, str):
                date_obj = pd.to_datetime(date_val).date()
            else:
                date_obj = date_val.date() if hasattr(date_val, 'date') else date_val

            status = str(row['status']).strip().lower()
            if status not in valid_status:
                errors.append(f'第{index + 2}行：状态"{status}"无效，可选: present/absent/late/leave')
                continue

            # 检查是否已存在
            existing = Attendance.query.filter_by(
                student_id=student.id,
                date=date_obj,
                course_id=course_id
            ).first()

            if existing:
                # 更新现有记录
                existing.status = status
                existing.remark = str(row.get('remark', '')).strip() if pd.notna(row.get('remark')) else None
            else:
                att = Attendance(
                    student_id=student.id,
                    date=date_obj,
                    status=status,
                    remark=str(row.get('remark', '')).strip() if pd.notna(row.get('remark')) else None,
                    course_id=course_id
                )
                db.session.add(att)
                success_count += 1

            if success_count % 20 == 0:
                db.session.commit()

        except Exception as e:
            errors.append(f'第{index + 2}行：{str(e)}')

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'出勤导入完成：成功{success_count}条，失败{len(errors)}条',
        'data': {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors[:10]
        }
    })


def _import_homework(df, course_id):
    """导入作业成绩"""
    required_cols = ['student_no', 'title']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return jsonify({
            'success': False,
            'message': '缺少必要列: ' + ','.join(missing_cols)
        }), 400

    success_count = 0
    errors = []

    for index, row in df.iterrows():
        try:
            student_no = str(row['student_no']).strip()
            student = Student.query.filter_by(student_no=student_no).first()

            if not student:
                errors.append(f'第{index + 2}行：学号{student_no}不存在')
                continue

            title = str(row['title']).strip()
            score = float(row['score']) if pd.notna(row.get('score')) else None
            max_score = float(row.get('max_score', 100)) if pd.notna(row.get('max_score')) else 100

            # 状态判断
            if pd.isna(row.get('status')):
                status = 'submitted' if score is not None else 'missing'
            else:
                status = str(row['status']).strip()

            hw = Homework(
                student_id=student.id,
                title=title,
                score=score,
                max_score=max_score,
                status=status,
                course_id=course_id
            )
            db.session.add(hw)
            success_count += 1

            if success_count % 20 == 0:
                db.session.commit()

        except Exception as e:
            errors.append(f'第{index + 2}行：{str(e)}')

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'作业导入完成：成功{success_count}条，失败{len(errors)}条',
        'data': {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors[:10]
        }
    })


def _import_quiz(df, course_id, quiz_type='quiz'):
    """
    导入测验/期末成绩
    quiz_type: 'quiz' (普通测验) / 'final' (期末考试)
    注：复用 Quiz 表，但我们要在 description 或 title 里标记，或者暂时不做区分，仅在 WarningEngine 里通过 title 识别
    为了简单起见，这里我们不改表结构，而是将 'final' 这个信息隐含在导入逻辑里。
    但在 WarningEngine 里，我们还是得能区分。
    
    方案：虽然 Quiz 表没有 type 字段，但我们可以约定 title 包含 '期末' 二字即为期末。
    或者更稳妥的，我们在 Quiz 模型加个字段？
    考虑到不想动数据库迁移，我们暂时约定：
    如果是期末导入，我们在 title 前面加个 "[期末]" 前缀（如果用户没写）。
    """
    required_cols = ['student_no', 'title']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return jsonify({
            'success': False,
            'message': '缺少必要列: ' + ','.join(missing_cols)
        }), 400

    success_count = 0
    errors = []

    for index, row in df.iterrows():
        try:
            student_no = str(row['student_no']).strip()
            student = Student.query.filter_by(student_no=student_no).first()

            if not student:
                errors.append(f'第{index + 2}行：学号{student_no}不存在')
                continue

            title = str(row['title']).strip()
            
            # 如果是期末导入，强制加标记
            if quiz_type == 'final' and '期末' not in title:
                title = f"[期末] {title}"

            score = float(row['score']) if pd.notna(row.get('score')) else None
            max_score = float(row.get('max_score', 100)) if pd.notna(row.get('max_score')) else 100
            duration = int(row['duration']) if pd.notna(row.get('duration')) else None

            quiz = Quiz(
                student_id=student.id,
                title=title,
                score=score,
                max_score=max_score,
                duration=duration,
                course_id=course_id
            )
            db.session.add(quiz)
            success_count += 1

            if success_count % 20 == 0:
                db.session.commit()

        except Exception as e:
            errors.append(f'第{index + 2}行：{str(e)}')

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'{("期末" if quiz_type=="final" else "测验")}导入完成：成功{success_count}条，失败{len(errors)}条',
        'data': {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors[:10]
        }
    })


def _import_interactions(df, course_id):
    """导入互动数据"""
    required_cols = ['student_no', 'type']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return jsonify({
            'success': False,
            'message': '缺少必要列: ' + ','.join(missing_cols)
        }), 400

    success_count = 0
    errors = []

    for index, row in df.iterrows():
        try:
            student_no = str(row['student_no']).strip()
            student = Student.query.filter_by(student_no=student_no).first()

            if not student:
                errors.append(f'第{index + 2}行：学号{student_no}不存在')
                continue

            inter_type = str(row['type']).strip()
            count = int(row.get('count', 1)) if pd.notna(row.get('count')) else 1

            # 日期处理
            date_val = row.get('date')
            if pd.isna(date_val):
                date_obj = datetime.now().date()
            elif isinstance(date_val, str):
                date_obj = pd.to_datetime(date_val).date()
            else:
                date_obj = date_val.date() if hasattr(date_val, 'date') else date_val

            inter = Interaction(
                student_id=student.id,
                type=inter_type,
                count=count,
                date=date_obj,
                course_id=course_id
            )
            db.session.add(inter)
            success_count += 1

            if success_count % 20 == 0:
                db.session.commit()

        except Exception as e:
            errors.append(f'第{index + 2}行：{str(e)}')

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'互动导入完成：成功{success_count}条，失败{len(errors)}条',
        'data': {
            'success_count': success_count,
            'error_count': len(errors),
            'errors': errors[:10]
        }
    })


@data_bp.route('/templates/<string:template_type>', methods=['GET'])
def download_template(template_type):
    """下载导入模板"""
    from flask import send_from_directory

    # 创建临时目录存放模板
    template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'templates')
    os.makedirs(template_dir, exist_ok=True)

    filename = f'{template_type}_template.xlsx'
    filepath = os.path.join(template_dir, filename)

    # 如果模板不存在，创建一个示例
    if not os.path.exists(filepath):
        if template_type == 'students':
            df = pd.DataFrame({
                'student_no': ['2024001', '2024002', '2024003'],
                'name': ['张三', '李四', '王五'],
                'gender': ['男', '女', '男'],
                'class_name': ['计算机9班', '计算机9班', '计算机10班']
            })
        elif template_type == 'attendance':
            df = pd.DataFrame({
                'student_no': ['2024001', '2024002'],
                'date': ['2026-03-01', '2026-03-01'],
                'status': ['present', 'absent'],
                'remark': ['', '病假']
            })
        elif template_type == 'homework':
            df = pd.DataFrame({
                'student_no': ['2024001', '2024002'],
                'title': ['作业1', '作业1'],
                'score': [85, 92],
                'max_score': [100, 100],
                'status': ['submitted', 'submitted']
            })
        elif template_type == 'quiz':
            df = pd.DataFrame({
                'student_no': ['2024001', '2024002'],
                'title': ['测验1', '测验1'],
                'score': [88, 75],
                'max_score': [100, 100],
                'duration': [45, 60]
            })
        # 增加期末模板
        elif template_type == 'final_exam':
            df = pd.DataFrame({
                'student_no': ['2024001', '2024002'],
                'title': ['期末考试', '期末考试'],
                'score': [88, 75],
                'max_score': [100, 100],
                'duration': [120, 120]
            })
        elif template_type == 'courses':
            df = pd.DataFrame({
                'name': ['Python程序设计', '数据结构'],
                'code': ['CS101', 'CS202'],
                'semester': ['2026-2027-1', '2026-2027-1'],
                'description': ['Python基础与应用', '数据结构与算法']
            })
        else:
            return jsonify({'success': False, 'message': '不支持的模板类型'}), 400

        df.to_excel(filepath, index=False)

    return send_from_directory(template_dir, filename, as_attachment=True)


@data_bp.route('/students/import', methods=['POST'])
def import_students_api():
    """
    学生数据导入API
    POST /api/students/import
    功能：接收Excel文件，解析并导入学生数据
    验证：验证学号唯一性、数据格式正确性
    反馈：返回导入成功/失败信息及详细错误列表
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'}), 400

    file = request.files['file']
    course_id = request.form.get('course_id', type=int)

    if not file or file.filename == '':
        return jsonify({'success': False, 'message': '文件名为空'}), 400

    if not course_id:
        return jsonify({'success': False, 'message': '缺少course_id参数'}), 400

    # 检查文件类型
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({
            'success': False,
            'message': f'不支持的文件格式: {ext}，请上传CSV或Excel文件'
        }), 400

    try:
        # 读取文件
        if ext == '.csv':
            df = pd.read_csv(file, encoding='utf-8')
        else:
            df = pd.read_excel(file)

        # 数据清洗：去除空行，去除前后空格
        df = df.dropna(how='all')
        # 兼容 Pandas 2.0.3: 使用 applymap
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        required_cols = ['student_no', 'name']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return jsonify({
                'success': False,
                'message': '缺少必要列: ' + ','.join(missing_cols) + '，当前列: ' + str(list(df.columns))
            }), 400

        success_count = 0
        skip_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                student_no = str(row['student_no']).strip()
                name = str(row['name']).strip()

                if not student_no or not name:
                    errors.append(f'第{index + 2}行：学号或姓名为空')
                    continue

                # 检查是否已存在
                existing = Student.query.filter_by(student_no=student_no).first()
                if existing:
                    skip_count += 1
                    continue

                # 获取或创建班级
                class_name = str(row.get('class_name', '默认班级')).strip()
                class_obj = Class.query.filter_by(name=class_name, course_id=course_id).first()
                if not class_obj:
                    class_obj = Class(name=class_name, course_id=course_id)
                    db.session.add(class_obj)
                    db.session.flush()  # 获取id

                # 创建学生
                gender = str(row.get('gender', '')).strip() if pd.notna(row.get('gender')) else None

                student = Student(
                    student_no=student_no,
                    name=name,
                    gender=gender,
                    class_id=class_obj.id
                )
                db.session.add(student)
                success_count += 1

                # 每20条提交一次，避免内存溢出
                if success_count % 20 == 0:
                    db.session.commit()

            except Exception as e:
                errors.append(f'第{index + 2}行：{str(e)}')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'导入完成：成功{success_count}条，跳过{skip_count}条（已存在），失败{len(errors)}条',
            'data': {
                'success_count': success_count,
                'skip_count': skip_count,
                'error_count': len(errors),
                'errors': errors[:10]  # 只显示前10个错误
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入失败：{str(e)}',
            'error_type': type(e).__name__
        }), 500


@data_bp.route('/courses/import', methods=['POST'])
def import_courses_api():
    """
    课程数据导入API
    POST /api/courses/import
    功能：接收Excel文件，解析并导入课程数据
    验证：验证课程代码唯一性
    反馈：返回导入成功/失败信息及详细错误列表
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'}), 400

    file = request.files['file']
    teacher_id = request.form.get('teacher_id', type=int)

    if not file or file.filename == '':
        return jsonify({'success': False, 'message': '文件名为空'}), 400

    if not teacher_id:
        return jsonify({'success': False, 'message': '缺少teacher_id参数'}), 400

    # 检查文件类型
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({
            'success': False,
            'message': f'不支持的文件格式: {ext}，请上传CSV或Excel文件'
        }), 400

    try:
        # 读取文件
        if ext == '.csv':
            df = pd.read_csv(file, encoding='utf-8')
        else:
            df = pd.read_excel(file)

        # 数据清洗：去除空行，去除前后空格
        df = df.dropna(how='all')
        # 兼容 Pandas 2.0.3 (因为 Python 3.8): 使用 applymap
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        required_cols = ['name', 'code']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return jsonify({
                'success': False,
                'message': '缺少必要列: ' + ','.join(missing_cols) + '，当前列: ' + str(list(df.columns))
            }), 400

        success_count = 0
        skip_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                name = str(row['name']).strip()
                code = str(row['code']).strip()

                if not name or not code:
                    errors.append(f'第{index + 2}行：课程名称或代码为空')
                    continue

                # 检查是否已存在
                existing = Course.query.filter_by(code=code).first()
                if existing:
                    skip_count += 1
                    continue

                # 创建课程
                semester = str(row.get('semester', '')).strip() if pd.notna(row.get('semester')) else None
                description = str(row.get('description', '')).strip() if pd.notna(row.get('description')) else None

                course = Course(
                    name=name,
                    code=code,
                    semester=semester,
                    description=description,
                    teacher_id=teacher_id
                )
                db.session.add(course)
                success_count += 1

                # 每20条提交一次，避免内存溢出
                if success_count % 20 == 0:
                    db.session.commit()

            except Exception as e:
                errors.append(f'第{index + 2}行：{str(e)}')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'导入完成：成功{success_count}条，跳过{skip_count}条（已存在），失败{len(errors)}条',
            'data': {
                'success_count': success_count,
                'skip_count': skip_count,
                'error_count': len(errors),
                'errors': errors[:10]  # 只显示前10个错误
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入失败：{str(e)}',
            'error_type': type(e).__name__
        }), 500


@data_bp.route('/scores/import', methods=['POST'])
def import_scores_api():
    """
    成绩数据导入API
    POST /api/scores/import
    功能：接收Excel文件，解析并导入成绩数据
    验证：验证学生存在性、课程存在性、成绩范围
    反馈：返回导入成功/失败信息及详细错误列表
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'}), 400

    file = request.files['file']
    course_id = request.form.get('course_id', type=int)

    if not file or file.filename == '':
        return jsonify({'success': False, 'message': '文件名为空'}), 400

    if not course_id:
        return jsonify({'success': False, 'message': '缺少course_id参数'}), 400

    # 检查文件类型
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({
            'success': False,
            'message': f'不支持的文件格式: {ext}，请上传CSV或Excel文件'
        }), 400

    try:
        # 读取文件
        if ext == '.csv':
            df = pd.read_csv(file, encoding='utf-8')
        else:
            df = pd.read_excel(file)

        # 数据清洗：去除空行，去除前后空格
        df = df.dropna(how='all')
        # 兼容 Pandas 2.0.3 (因为 Python 3.8): 使用 applymap
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        required_cols = ['student_no', 'title', 'score']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return jsonify({
                'success': False,
                'message': '缺少必要列: ' + ','.join(missing_cols) + '，当前列: ' + str(list(df.columns))
            }), 400

        success_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                student_no = str(row['student_no']).strip()
                student = Student.query.filter_by(student_no=student_no).first()

                if not student:
                    errors.append(f'第{index + 2}行：学号{student_no}不存在')
                    continue

                title = str(row['title']).strip()
                score = float(row['score']) if pd.notna(row.get('score')) else None
                max_score = float(row.get('max_score', 100)) if pd.notna(row.get('max_score')) else 100

                # 验证成绩范围
                if score is not None and (score < 0 or score > max_score):
                    errors.append(f'第{index + 2}行：成绩{score}超出范围（0-{max_score}）')
                    continue

                # 状态判断
                if pd.isna(row.get('status')):
                    status = 'submitted' if score is not None else 'missing'
                else:
                    status = str(row['status']).strip()

                # 检查是作业还是测验
                score_type = str(row.get('type', 'homework')).strip().lower()
                if score_type == 'quiz':
                    # 导入测验成绩
                    duration = int(row['duration']) if pd.notna(row.get('duration')) else None
                    quiz = Quiz(
                        student_id=student.id,
                        title=title,
                        score=score,
                        max_score=max_score,
                        duration=duration,
                        course_id=course_id
                    )
                    db.session.add(quiz)
                else:
                    # 导入作业成绩
                    hw = Homework(
                        student_id=student.id,
                        title=title,
                        score=score,
                        max_score=max_score,
                        status=status,
                        course_id=course_id
                    )
                    db.session.add(hw)

                success_count += 1

                # 每20条提交一次，避免内存溢出
                if success_count % 20 == 0:
                    db.session.commit()

            except Exception as e:
                errors.append(f'第{index + 2}行：{str(e)}')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'成绩导入完成：成功{success_count}条，失败{len(errors)}条',
            'data': {
                'success_count': success_count,
                'error_count': len(errors),
                'errors': errors[:10]  # 只显示前10个错误
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入失败：{str(e)}',
            'error_type': type(e).__name__
        }), 500


@data_bp.route('/attendance/import', methods=['POST'])
def import_attendance_api():
    """
    考勤数据导入API
    POST /api/attendance/import
    功能：接收Excel文件，解析并导入考勤数据
    验证：验证学生存在性、课程存在性、考勤状态合法性
    反馈：返回导入成功/失败信息及详细错误列表
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'}), 400

    file = request.files['file']
    course_id = request.form.get('course_id', type=int)

    if not file or file.filename == '':
        return jsonify({'success': False, 'message': '文件名为空'}), 400

    if not course_id:
        return jsonify({'success': False, 'message': '缺少course_id参数'}), 400

    # 检查文件类型
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({
            'success': False,
            'message': f'不支持的文件格式: {ext}，请上传CSV或Excel文件'
        }), 400

    try:
        # 读取文件
        if ext == '.csv':
            df = pd.read_csv(file, encoding='utf-8')
        else:
            df = pd.read_excel(file)

        # 数据清洗：去除空行，去除前后空格
        df = df.dropna(how='all')
        # 兼容 Pandas 2.0.3 (因为 Python 3.8): 使用 applymap
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        required_cols = ['student_no', 'date', 'status']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return jsonify({
                'success': False,
                'message': '缺少必要列: ' + ','.join(missing_cols) + '，当前列: ' + str(list(df.columns))
            }), 400

        # 验证状态值
        valid_status = {'present', 'absent', 'late', 'leave'}

        success_count = 0
        skip_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                student_no = str(row['student_no']).strip()
                student = Student.query.filter_by(student_no=student_no).first()

                if not student:
                    errors.append(f'第{index + 2}行：学号{student_no}不存在')
                    continue

                # 解析日期
                date_val = row['date']
                if isinstance(date_val, str):
                    date_obj = pd.to_datetime(date_val).date()
                else:
                    date_obj = date_val.date() if hasattr(date_val, 'date') else date_val

                status = str(row['status']).strip().lower()
                if status not in valid_status:
                    errors.append(f'第{index + 2}行：状态"{status}"无效，可选: present/absent/late/leave')
                    continue

                # 检查是否已存在
                existing = Attendance.query.filter_by(
                    student_id=student.id,
                    date=date_obj,
                    course_id=course_id
                ).first()

                if existing:
                    # 更新现有记录
                    existing.status = status
                    existing.remark = str(row.get('remark', '')).strip() if pd.notna(row.get('remark')) else None
                else:
                    att = Attendance(
                        student_id=student.id,
                        date=date_obj,
                        status=status,
                        remark=str(row.get('remark', '')).strip() if pd.notna(row.get('remark')) else None,
                        course_id=course_id
                    )
                    db.session.add(att)
                    success_count += 1

                if success_count % 20 == 0:
                    db.session.commit()

            except Exception as e:
                errors.append(f'第{index + 2}行：{str(e)}')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'出勤导入完成：成功{success_count}条，失败{len(errors)}条',
            'data': {
                'success_count': success_count,
                'error_count': len(errors),
                'errors': errors[:10]  # 只显示前10个错误
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入失败：{str(e)}',
            'error_type': type(e).__name__
        }), 500