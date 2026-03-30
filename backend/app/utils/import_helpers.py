"""
导入数据辅助工具模块
提供通用的数据导入功能，消除重复代码
"""
import pandas as pd
from datetime import datetime
from ..models import db
from ..models.course import Student, Class
from ..models.data import Attendance, Homework, Quiz, Interaction


class ImportHelper:
    """数据导入辅助类"""
    
    @staticmethod
    def validate_required_columns(df, required_cols):
        """验证必需列是否存在"""
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return False, f'缺少必要列: {", ".join(missing_cols)}，当前列: {list(df.columns)}'
        return True, None
    
    @staticmethod
    def get_or_create_class(class_name, course_id):
        """获取或创建班级"""
        class_obj = Class.query.filter_by(name=class_name, course_id=course_id).first()
        if not class_obj:
            class_obj = Class(name=class_name, course_id=course_id)
            db.session.add(class_obj)
            db.session.flush()  # 获取id
        return class_obj
    
    @staticmethod
    def get_student_by_no(student_no):
        """通过学号获取学生"""
        return Student.query.filter_by(student_no=student_no).first()
    
    @staticmethod
    def parse_date(date_val):
        """解析日期值"""
        if pd.isna(date_val):
            return datetime.now().date()
        
        if isinstance(date_val, str):
            try:
                return pd.to_datetime(date_val).date()
            except:
                return None
        elif hasattr(date_val, 'date'):
            return date_val.date()
        return date_val
    
    @staticmethod
    def clean_string(value, default=''):
        """清理字符串值"""
        if pd.isna(value):
            return default
        return str(value).strip()
    
    @staticmethod
    def clean_float(value, default=None):
        """清理浮点数值"""
        if pd.isna(value):
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def clean_int(value, default=None):
        """清理整数值"""
        if pd.isna(value):
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def create_import_result(success_count=0, skip_count=0, errors=None, message=''):
        """创建导入结果响应"""
        errors = errors or []
        return {
            'success': True,
            'message': message or f'导入完成：成功{success_count}条，跳过{skip_count}条，失败{len(errors)}条',
            'data': {
                'success_count': success_count,
                'skip_count': skip_count,
                'error_count': len(errors),
                'errors': errors[:10]  # 只显示前10个错误
            }
        }
    
    @staticmethod
    def create_error_result(message, error_type='ValidationError'):
        """创建错误响应"""
        return {
            'success': False,
            'message': message,
            'error_type': error_type
        }
    
    @staticmethod
    def batch_commit(success_count, batch_size=20):
        """批量提交数据库操作"""
        if success_count % batch_size == 0:
            db.session.commit()
    
    @staticmethod
    def process_row_errors(index, errors, max_errors=50):
        """处理行错误，限制错误数量"""
        if len(errors) >= max_errors:
            errors.append(f'错误过多，已停止记录后续错误（已记录{max_errors}个）')
            return True  # 停止处理
        return False


class BaseImporter:
    """基础导入器，提供通用导入功能"""
    
    def __init__(self, df, course_id, model_class):
        """
        初始化导入器
        
        Args:
            df: pandas DataFrame
            course_id: 课程ID
            model_class: 数据模型类
        """
        self.df = df
        self.course_id = course_id
        self.model_class = model_class
        
        # 导入统计
        self.success_count = 0
        self.skip_count = 0
        self.errors = []
        
        # 导入助手
        self.helper = ImportHelper()
    
    def validate_data(self):
        """验证数据，子类需要实现"""
        raise NotImplementedError("子类必须实现 validate_data 方法")
    
    def process_row(self, index, row):
        """处理单行数据，子类需要实现"""
        raise NotImplementedError("子类必须实现 process_row 方法")
    
    def import_data(self):
        """执行数据导入"""
        # 验证数据
        is_valid, error_msg = self.validate_data()
        if not is_valid:
            return self.helper.create_error_result(error_msg)
        
        # 处理每一行数据
        for index, row in self.df.iterrows():
            try:
                # 检查错误数量限制
                if self.helper.process_row_errors(index, self.errors):
                    break
                
                # 处理单行数据
                self.process_row(index, row)
                
                # 批量提交
                self.helper.batch_commit(self.success_count)
                
            except Exception as e:
                self.errors.append(f'第{index + 2}行：{str(e)}')
        
        # 最终提交
        db.session.commit()
        
        # 返回结果
        return self.helper.create_import_result(
            success_count=self.success_count,
            skip_count=self.skip_count,
            errors=self.errors
        )
    
    def find_existing_record(self, **filters):
        """查找已存在的记录"""
        return self.model_class.query.filter_by(**filters).first()


class AttendanceImporter(BaseImporter):
    """出勤数据导入器"""
    
    REQUIRED_COLS = ['student_no', 'date', 'status']
    VALID_STATUS = {'present', 'absent', 'late', 'leave'}
    
    def validate_data(self):
        return self.helper.validate_required_columns(self.df, self.REQUIRED_COLS)
    
    def process_row(self, index, row):
        student_no = self.helper.clean_string(row['student_no'])
        student = self.helper.get_student_by_no(student_no)
        
        if not student:
            self.errors.append(f'第{index + 2}行：学号{student_no}不存在')
            return
        
        # 解析日期
        date_obj = self.helper.parse_date(row['date'])
        if not date_obj:
            self.errors.append(f'第{index + 2}行：日期格式无效')
            return
        
        # 验证状态
        status = self.helper.clean_string(row['status']).lower()
        if status not in self.VALID_STATUS:
            self.errors.append(f'第{index + 2}行：状态"{status}"无效，可选: {", ".join(self.VALID_STATUS)}')
            return
        
        # 检查是否已存在
        existing = self.find_existing_record(
            student_id=student.id,
            date=date_obj,
            course_id=self.course_id
        )
        
        if existing:
            # 更新现有记录
            existing.status = status
            existing.remark = self.helper.clean_string(row.get('remark'))
            self.skip_count += 1
        else:
            # 创建新记录
            att = Attendance(
                student_id=student.id,
                date=date_obj,
                status=status,
                remark=self.helper.clean_string(row.get('remark')),
                course_id=self.course_id
            )
            db.session.add(att)
            self.success_count += 1


class HomeworkImporter(BaseImporter):
    """作业数据导入器"""
    
    REQUIRED_COLS = ['student_no', 'title']
    
    def validate_data(self):
        return self.helper.validate_required_columns(self.df, self.REQUIRED_COLS)
    
    def process_row(self, index, row):
        student_no = self.helper.clean_string(row['student_no'])
        student = self.helper.get_student_by_no(student_no)
        
        if not student:
            self.errors.append(f'第{index + 2}行：学号{student_no}不存在')
            return
        
        # 判断状态
        status = self.helper.clean_string(row.get('status'))
        score = self.helper.clean_float(row.get('score'))
        
        if not status:
            status = 'submitted' if score is not None else 'missing'
        
        # 创建作业记录
        homework = Homework(
            student_id=student.id,
            title=self.helper.clean_string(row['title']),
            score=score,
            max_score=self.helper.clean_float(row.get('max_score', 100), 100),
            status=status,
            course_id=self.course_id
        )
        db.session.add(homework)
        self.success_count += 1


class QuizImporter(BaseImporter):
    """测验数据导入器"""
    
    REQUIRED_COLS = ['student_no', 'title']
    
    def __init__(self, df, course_id, quiz_type='quiz'):
        super().__init__(df, course_id, Quiz)
        self.quiz_type = quiz_type
    
    def validate_data(self):
        return self.helper.validate_required_columns(self.df, self.REQUIRED_COLS)
    
    def process_row(self, index, row):
        student_no = self.helper.clean_string(row['student_no'])
        student = self.helper.get_student_by_no(student_no)
        
        if not student:
            self.errors.append(f'第{index + 2}行：学号{student_no}不存在')
            return
        
        # 处理标题
        title = self.helper.clean_string(row['title'])
        if self.quiz_type == 'final' and '期末' not in title:
            title = f"[期末] {title}"
        
        # 创建测验记录
        quiz = Quiz(
            student_id=student.id,
            title=title,
            score=self.helper.clean_float(row.get('score')),
            max_score=self.helper.clean_float(row.get('max_score', 100), 100),
            duration=self.helper.clean_int(row.get('duration')),
            course_id=self.course_id
        )
        db.session.add(quiz)
        self.success_count += 1


class InteractionImporter(BaseImporter):
    """互动数据导入器"""
    
    REQUIRED_COLS = ['student_no', 'type']
    
    def validate_data(self):
        return self.helper.validate_required_columns(self.df, self.REQUIRED_COLS)
    
    def process_row(self, index, row):
        student_no = self.helper.clean_string(row['student_no'])
        student = self.helper.get_student_by_no(student_no)
        
        if not student:
            self.errors.append(f'第{index + 2}行：学号{student_no}不存在')
            return
        
        # 解析日期
        date_obj = self.helper.parse_date(row.get('date'))
        
        # 创建互动记录
        interaction = Interaction(
            student_id=student.id,
            type=self.helper.clean_string(row['type']),
            count=self.helper.clean_int(row.get('count', 1), 1),
            date=date_obj,
            course_id=self.course_id
        )
        db.session.add(interaction)
        self.success_count += 1


class StudentImporter:
    """学生数据导入器（特殊处理，不使用BaseImporter）"""
    
    REQUIRED_COLS = ['student_no', 'name']
    
    def __init__(self, df, course_id):
        self.df = df
        self.course_id = course_id
        self.helper = ImportHelper()
        self.success_count = 0
        self.skip_count = 0
        self.errors = []
    
    def validate_data(self):
        return self.helper.validate_required_columns(self.df, self.REQUIRED_COLS)
    
    def process_row(self, index, row):
        student_no = self.helper.clean_string(row['student_no'])
        name = self.helper.clean_string(row['name'])
        
        if not student_no or not name:
            self.errors.append(f'第{index + 2}行：学号或姓名为空')
            return
        
        # 检查是否已存在
        existing = Student.query.filter_by(student_no=student_no).first()
        if existing:
            self.skip_count += 1
            return
        
        # 获取或创建班级
        class_name = self.helper.clean_string(row.get('class_name', '默认班级'))
        class_obj = self.helper.get_or_create_class(class_name, self.course_id)
        
        # 创建学生
        gender = self.helper.clean_string(row.get('gender'))
        student = Student(
            student_no=student_no,
            name=name,
            gender=gender,
            class_id=class_obj.id
        )
        db.session.add(student)
        self.success_count += 1
    
    def import_data(self):
        """执行学生数据导入"""
        # 验证数据
        is_valid, error_msg = self.validate_data()
        if not is_valid:
            return self.helper.create_error_result(error_msg)
        
        # 处理每一行数据
        for index, row in self.df.iterrows():
            try:
                # 检查错误数量限制
                if self.helper.process_row_errors(index, self.errors):
                    break
                
                # 处理单行数据
                self.process_row(index, row)
                
                # 批量提交
                self.helper.batch_commit(self.success_count)
                
            except Exception as e:
                self.errors.append(f'第{index + 2}行：{str(e)}')
        
        # 最终提交
        db.session.commit()
        
        # 返回结果
        return self.helper.create_import_result(
            success_count=self.success_count,
            skip_count=self.skip_count,
            errors=self.errors
        )