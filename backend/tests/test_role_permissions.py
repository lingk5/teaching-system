import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

TEST_DB_DIR = tempfile.mkdtemp(prefix='teaching-system-role-tests-')
TEST_DB_PATH = Path(TEST_DB_DIR) / 'permissions.db'

os.environ['DATABASE_URI'] = f'sqlite:///{TEST_DB_PATH}'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key'

from app import create_app  # noqa: E402
from app.models import db, User, Course, Class, Student, Warning  # noqa: E402


class RolePermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            teacher = User.query.filter_by(username='teacher').first()
            assert teacher is not None

            course = Course(
                name='权限测试课程',
                code='ROLE101',
                semester='2026-2027-1',
                teacher_id=teacher.id,
            )
            db.session.add(course)
            db.session.flush()

            class_ = Class(name='权限测试班级', course_id=course.id)
            db.session.add(class_)
            db.session.flush()

            student = Student(
                student_no='ROLE-STU-001',
                name='权限测试学生',
                gender='男',
                class_id=class_.id,
            )
            db.session.add(student)
            db.session.flush()

            warning = Warning(
                student_id=student.id,
                course_id=course.id,
                type='comprehensive',
                level='red',
                reason='综合分过低',
                suggestion='安排针对性辅导',
                metrics={'comprehensive_score': 52.5},
                status='active',
            )
            db.session.add(warning)
            db.session.commit()

            cls.teacher_id = teacher.id
            cls.course_id = course.id
            cls.student_id = student.id
            cls.warning_id = warning.id

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def auth_headers(self, username, password='123456'):
        response = self.client.post(
            '/api/auth/login',
            json={'username': username, 'password': password},
        )
        self.assertEqual(response.status_code, 200)
        token = response.get_json()['data']['token']
        return {'Authorization': f'Bearer {token}'}

    def test_teacher_status_excludes_admin_only_stats(self):
        response = self.client.get('/api/status', headers=self.auth_headers('teacher'))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn('stats', payload)
        self.assertNotIn('users', payload['stats'])
        self.assertNotIn('courses', payload['stats'])
        self.assertNotIn('classes', payload['stats'])
        self.assertNotIn('interactions', payload['stats'])

    def test_admin_can_list_users(self):
        response = self.client.get('/api/auth/users', headers=self.auth_headers('admin'))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['success'])
        usernames = {item['username'] for item in payload['data']}
        self.assertIn('admin', usernames)
        self.assertIn('teacher', usernames)
        self.assertIn('assistant', usernames)

    def test_teacher_cannot_list_users(self):
        response = self.client.get('/api/auth/users', headers=self.auth_headers('teacher'))

        self.assertEqual(response.status_code, 403)

    def test_assistant_cannot_import_courses(self):
        response = self.client.post(
            '/api/data/courses/import',
            headers=self.auth_headers('assistant'),
            data={
                'teacher_id': str(self.teacher_id),
                'file': (
                    io.BytesIO('name,code\n助教越权课程,TA-ROLE-001\n'.encode('utf-8')),
                    'courses.csv',
                ),
            },
            content_type='multipart/form-data',
        )

        self.assertEqual(response.status_code, 403)

    def test_assistant_cannot_update_student(self):
        response = self.client.put(
            f'/api/courses/students/{self.student_id}',
            headers=self.auth_headers('assistant'),
            json={'name': '被越权修改的学生'},
        )

        self.assertEqual(response.status_code, 403)

    def test_assistant_cannot_process_warning(self):
        response = self.client.post(
            f'/api/warnings/{self.warning_id}/process',
            headers=self.auth_headers('assistant'),
            json={
                'process_type': 'talk',
                'process_detail': '助教尝试处理',
                'process_result': 'resolved',
            },
        )

        self.assertEqual(response.status_code, 403)


if __name__ == '__main__':
    unittest.main()
