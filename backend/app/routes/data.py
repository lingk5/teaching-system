from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt
from ..models import db
from ..models.data import Attendance, Homework, Quiz, Interaction
from ..models.course import Student, Class, Course
from ..utils.import_helpers import (
    ImportHelper, StudentImporter, AttendanceImporter, 
    HomeworkImporter, QuizImporter, InteractionImporter
)
import pandas as pd
import os

data_bp = Blueprint('data', __name__)
helper = ImportHelper()


def _current_role():
    claims = get_jwt()
    return (claims.get('role') or 'teacher').lower()


# ================ 单条数据添加接口 ================

@data_bp.route('/attendance', methods=['POST'])
@jwt_required()
def add_attendance():
    """单条添加出勤记录"""
    if _current_role() == 'assistant':
        return jsonify({'success': False, 'message': '助教无权限写入数据'}), 403

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
@jwt_required()
def add_homework():
    """单条添加作业记录"""
    if _current_role() == 'assistant':
        return jsonify({'success': False, 'message': '助教无权限写入数据'}), 403

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
@jwt_required()
def add_quiz():
    """单条添加测验记录"""
    if _current_role() == 'assistant':
        return jsonify({'success': False, 'message': '助教无权限写入数据'}), 403

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
@jwt_required()
def add_interaction():
    """单条添加互动记录"""
    if _current_role() == 'assistant':
        return jsonify({'success': False, 'message': '助教无权限写入数据'}), 403

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


# ================ 批量导入接口（使用重构后的导入器） ================

@data_bp.route('/import/<string:data_type>', methods=['POST'])
@jwt_required()
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
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

        # 根据类型处理
        if data_type == 'students':
            importer = StudentImporter(df, course_id)
            result = importer.import_data()
        elif data_type == 'attendance':
            importer = AttendanceImporter(df, course_id)
            result = importer.import_data()
        elif data_type == 'homework':
            importer = HomeworkImporter(df, course_id)
            result = importer.import_data()
        elif data_type == 'quiz':
            # 普通测验，type='quiz'
            importer = QuizImporter(df, course_id, quiz_type='quiz')
            result = importer.import_data()
        elif data_type == 'final_exam':
            # 期末考试，复用 Quiz 表，type='final'
            importer = QuizImporter(df, course_id, quiz_type='final')
            result = importer.import_data()
        elif data_type == 'interactions':
            importer = InteractionImporter(df, course_id)
            result = importer.import_data()
        else:
            return jsonify({
                'success': False,
                'message': f'不支持的导入类型: {data_type}'
            }), 400

        return jsonify(result), 200 if result['success'] else 400

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入失败：{str(e)}',
            'error_type': type(e).__name__
        }), 500


# ================ 模板下载接口 ================

@data_bp.route('/templates/<string:template_type>', methods=['GET'])
def download_template(template_type):
    """下载导入模板"""
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


# ================ 专用导入API（向后兼容） ================

@data_bp.route('/students/import', methods=['POST'])
@jwt_required()
def import_students_api():
    """学生数据导入API（兼容旧接口）"""
    return import_data('students')


@data_bp.route('/attendance/import', methods=['POST'])
@jwt_required()
def import_attendance_api():
    """考勤数据导入API（兼容旧接口）"""
    return import_data('attendance')


@data_bp.route('/scores/import', methods=['POST'])
@jwt_required()
def import_scores_api():
    """
    成绩数据导入API - 智能判断是作业还是测验
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

        # 数据清洗
        df = df.dropna(how='all')
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

        # 验证必需列
        required_cols = ['student_no', 'title', 'score']
        is_valid, error_msg = helper.validate_required_columns(df, required_cols)
        if not is_valid:
            return jsonify(helper.create_error_result(error_msg)), 400

        # 智能判断：如果有duration列，优先当作测验；否则当作作业
        if 'duration' in df.columns:
            importer = QuizImporter(df, course_id, quiz_type='quiz')
        else:
            importer = HomeworkImporter(df, course_id)
        
        result = importer.import_data()
        return jsonify(result), 200 if result['success'] else 400

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入失败：{str(e)}',
            'error_type': type(e).__name__
        }), 500


@data_bp.route('/courses/import', methods=['POST'])
@jwt_required()
def import_courses_api():
    """课程数据导入API"""
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

        # 数据清洗
        df = df.dropna(how='all')
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

        # 验证必需列
        required_cols = ['name', 'code']
        is_valid, error_msg = helper.validate_required_columns(df, required_cols)
        if not is_valid:
            return jsonify(helper.create_error_result(error_msg)), 400

        success_count = 0
        skip_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                name = helper.clean_string(row['name'])
                code = helper.clean_string(row['code'])

                if not name or not code:
                    errors.append(f'第{index + 2}行：课程名称或代码为空')
                    continue

                # 检查是否已存在
                existing = Course.query.filter_by(code=code).first()
                if existing:
                    skip_count += 1
                    continue

                # 创建课程
                semester = helper.clean_string(row.get('semester'))
                description = helper.clean_string(row.get('description'))

                course = Course(
                    name=name,
                    code=code,
                    semester=semester,
                    description=description,
                    teacher_id=teacher_id
                )
                db.session.add(course)
                success_count += 1

                # 批量提交
                helper.batch_commit(success_count)

            except Exception as e:
                errors.append(f'第{index + 2}行：{str(e)}')

        db.session.commit()

        result = helper.create_import_result(
            success_count=success_count,
            skip_count=skip_count,
            errors=errors,
            message=f'课程导入完成：成功{success_count}条，跳过{skip_count}条，失败{len(errors)}条'
        )
        return jsonify(result), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入失败：{str(e)}',
            'error_type': type(e).__name__
        }), 500
    if _current_role() == 'assistant':
        return jsonify({'success': False, 'message': '助教无权限导入数据'}), 403
