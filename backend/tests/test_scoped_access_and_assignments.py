import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

TEST_DB_DIR = tempfile.mkdtemp(prefix="teaching-system-scope-tests-")
TEST_DB_PATH = Path(TEST_DB_DIR) / "scoped_access.db"

os.environ["DATABASE_URI"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "scope-test-secret"
os.environ["JWT_SECRET_KEY"] = "scope-test-jwt-secret"

from app import create_app  # noqa: E402
from app.models import db, User, Course, Class, Student, Warning  # noqa: E402
from app.models.assistant_assignment import AssistantCourseAssignment  # noqa: E402


class ScopedAccessAndAssignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.session.rollback()
        AssistantCourseAssignment.query.delete()
        Warning.query.delete()
        Student.query.delete()
        Class.query.delete()
        Course.query.delete()
        User.query.filter(
            User.username.in_(["teacher_other", "assistant_two"])
        ).delete(synchronize_session=False)
        db.session.commit()

        admin = User.query.filter_by(username="admin").first()
        teacher = User.query.filter_by(username="teacher").first()
        assistant = User.query.filter_by(username="assistant").first()

        if admin is None or teacher is None or assistant is None:
            from werkzeug.security import generate_password_hash

            if admin is None:
                admin = User(
                    username="admin",
                    password_hash=generate_password_hash("123456"),
                    name="系统管理员",
                    role="admin",
                )
                db.session.add(admin)
            if teacher is None:
                teacher = User(
                    username="teacher",
                    password_hash=generate_password_hash("123456"),
                    name="演示教师",
                    role="teacher",
                )
                db.session.add(teacher)
            if assistant is None:
                assistant = User(
                    username="assistant",
                    password_hash=generate_password_hash("123456"),
                    name="演示助教",
                    role="assistant",
                )
                db.session.add(assistant)
            db.session.flush()

        other_teacher = User.query.filter_by(username="teacher_other").first()
        if other_teacher is None:
            from werkzeug.security import generate_password_hash

            other_teacher = User(
                username="teacher_other",
                password_hash=generate_password_hash("123456"),
                name="其他教师",
                role="teacher",
            )
            db.session.add(other_teacher)

        second_assistant = User.query.filter_by(username="assistant_two").first()
        if second_assistant is None:
            from werkzeug.security import generate_password_hash

            second_assistant = User(
                username="assistant_two",
                password_hash=generate_password_hash("123456"),
                name="第二助教",
                role="assistant",
            )
            db.session.add(second_assistant)

        db.session.flush()

        owned_course = Course(
            name="教师自有课程",
            code="SCOPE-OWN-101",
            semester="2026-2027-1",
            teacher_id=teacher.id,
        )
        foreign_course = Course(
            name="其他教师课程",
            code="SCOPE-FOREIGN-201",
            semester="2026-2027-1",
            teacher_id=other_teacher.id,
        )
        db.session.add_all([owned_course, foreign_course])
        db.session.flush()

        owned_class = Class(name="自有班级", course_id=owned_course.id)
        foreign_class = Class(name="外部班级", course_id=foreign_course.id)
        db.session.add_all([owned_class, foreign_class])
        db.session.flush()

        owned_student = Student(
            student_no="SCOPE-STU-001",
            name="自有学生",
            gender="男",
            class_id=owned_class.id,
        )
        foreign_student = Student(
            student_no="SCOPE-STU-002",
            name="外部学生",
            gender="女",
            class_id=foreign_class.id,
        )
        db.session.add_all([owned_student, foreign_student])
        db.session.flush()

        owned_warning = Warning(
            student_id=owned_student.id,
            course_id=owned_course.id,
            type="comprehensive",
            level="yellow",
            reason="自有课程预警",
            suggestion="继续观察",
            metrics={"comprehensive_score": 74.0},
            status="active",
        )
        foreign_warning = Warning(
            student_id=foreign_student.id,
            course_id=foreign_course.id,
            type="comprehensive",
            level="red",
            reason="外部课程预警",
            suggestion="立即干预",
            metrics={"comprehensive_score": 40.0},
            status="active",
        )
        db.session.add_all([owned_warning, foreign_warning])
        db.session.flush()

        assignment = AssistantCourseAssignment(
            assistant_id=assistant.id,
            course_id=owned_course.id,
            assigned_by=teacher.id,
        )
        db.session.add(assignment)
        db.session.commit()

        self.admin_id = admin.id
        self.teacher_id = teacher.id
        self.assistant_id = assistant.id
        self.other_teacher_id = other_teacher.id
        self.second_assistant_id = second_assistant.id
        self.owned_course_id = owned_course.id
        self.foreign_course_id = foreign_course.id
        self.owned_class_id = owned_class.id
        self.foreign_class_id = foreign_class.id
        self.owned_student_id = owned_student.id
        self.foreign_student_id = foreign_student.id
        self.owned_warning_id = owned_warning.id
        self.foreign_warning_id = foreign_warning.id

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def auth_headers(self, username, password="123456"):
        response = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        self.assertEqual(response.status_code, 200)
        token = response.get_json()["data"]["token"]
        return {"Authorization": f"Bearer {token}"}

    def test_models_package_exports_assistant_assignment(self):
        import app.models as models_pkg

        self.assertTrue(hasattr(models_pkg, "AssistantCourseAssignment"))

    def test_course_listing_is_scoped_by_role(self):
        admin_response = self.client.get("/api/courses/", headers=self.auth_headers("admin"))
        teacher_response = self.client.get("/api/courses/", headers=self.auth_headers("teacher"))
        assistant_response = self.client.get("/api/courses/", headers=self.auth_headers("assistant"))

        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(teacher_response.status_code, 200)
        self.assertEqual(assistant_response.status_code, 200)

        admin_courses = {item["id"] for item in admin_response.get_json()["data"]}
        teacher_courses = {item["id"] for item in teacher_response.get_json()["data"]}
        assistant_courses = {item["id"] for item in assistant_response.get_json()["data"]}

        self.assertIn(self.owned_course_id, admin_courses)
        self.assertIn(self.foreign_course_id, admin_courses)
        self.assertEqual({self.owned_course_id}, teacher_courses)
        self.assertEqual({self.owned_course_id}, assistant_courses)

    def test_status_counts_are_scoped_to_accessible_courses(self):
        admin_response = self.client.get("/api/status", headers=self.auth_headers("admin"))
        teacher_response = self.client.get("/api/status", headers=self.auth_headers("teacher"))
        assistant_response = self.client.get("/api/status", headers=self.auth_headers("assistant"))

        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(teacher_response.status_code, 200)
        self.assertEqual(assistant_response.status_code, 200)

        self.assertEqual(admin_response.get_json()["stats"]["students"], 2)
        self.assertEqual(teacher_response.get_json()["stats"]["students"], 1)
        self.assertEqual(assistant_response.get_json()["stats"]["students"], 1)

    def test_teacher_cannot_view_foreign_course_students(self):
        response = self.client.get(
            f"/api/courses/{self.foreign_course_id}/classes/{self.foreign_class_id}/students",
            headers=self.auth_headers("teacher"),
        )

        self.assertEqual(response.status_code, 403)

    def test_assistant_can_only_view_assigned_course_students(self):
        allowed_response = self.client.get(
            f"/api/courses/{self.owned_course_id}/classes/{self.owned_class_id}/students",
            headers=self.auth_headers("assistant"),
        )
        forbidden_response = self.client.get(
            f"/api/courses/{self.foreign_course_id}/classes/{self.foreign_class_id}/students",
            headers=self.auth_headers("assistant"),
        )

        self.assertEqual(allowed_response.status_code, 200)
        self.assertEqual(forbidden_response.status_code, 403)

    def test_assistant_cannot_access_foreign_analytics_or_warnings(self):
        analytics_response = self.client.get(
            f"/api/analytics/course/{self.foreign_course_id}/overview",
            headers=self.auth_headers("assistant"),
        )
        warning_response = self.client.get(
            f"/api/warnings/?course_id={self.foreign_course_id}",
            headers=self.auth_headers("assistant"),
        )

        self.assertEqual(analytics_response.status_code, 403)
        self.assertEqual(warning_response.status_code, 403)

    def test_assistant_cannot_export_reports(self):
        response = self.client.get(
            f"/api/export/students?course_id={self.owned_course_id}",
            headers=self.auth_headers("assistant"),
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_course_for_specific_teacher(self):
        response = self.client.post(
            "/api/courses/",
            headers=self.auth_headers("admin"),
            json={
                "name": "管理员代建课程",
                "code": "ADMIN-CREATE-001",
                "semester": "2026-2027-2",
                "teacher_id": self.other_teacher_id,
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()["data"]
        self.assertEqual(payload["teacher_id"], self.other_teacher_id)

    def test_teacher_course_creation_is_bound_to_self(self):
        response = self.client.post(
            "/api/courses/",
            headers=self.auth_headers("teacher"),
            json={
                "name": "教师自建课程",
                "code": "TEACHER-CREATE-001",
                "semester": "2026-2027-2",
                "teacher_id": self.other_teacher_id,
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()["data"]
        self.assertEqual(payload["teacher_id"], self.teacher_id)

    def test_teacher_can_manage_assistant_assignments_on_owned_course(self):
        create_response = self.client.post(
            f"/api/courses/{self.owned_course_id}/assistants",
            headers=self.auth_headers("teacher"),
            json={"assistant_id": self.second_assistant_id},
        )
        list_response = self.client.get(
            f"/api/courses/{self.owned_course_id}/assistants",
            headers=self.auth_headers("teacher"),
        )
        delete_response = self.client.delete(
            f"/api/courses/{self.owned_course_id}/assistants/{self.second_assistant_id}",
            headers=self.auth_headers("teacher"),
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(delete_response.status_code, 200)

        assistant_ids = {
            item["assistant_id"]
            for item in list_response.get_json()["data"]
        }
        self.assertIn(self.assistant_id, assistant_ids)
        self.assertIn(self.second_assistant_id, assistant_ids)

    def test_teacher_and_admin_can_list_assignable_assistants(self):
        teacher_response = self.client.get(
            "/api/courses/assistant-options",
            headers=self.auth_headers("teacher"),
        )
        admin_response = self.client.get(
            "/api/courses/assistant-options",
            headers=self.auth_headers("admin"),
        )
        assistant_response = self.client.get(
            "/api/courses/assistant-options",
            headers=self.auth_headers("assistant"),
        )

        self.assertEqual(teacher_response.status_code, 200)
        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(assistant_response.status_code, 403)

        assistant_ids = {
            item["id"]
            for item in teacher_response.get_json()["data"]
        }
        self.assertIn(self.assistant_id, assistant_ids)
        self.assertIn(self.second_assistant_id, assistant_ids)

    def test_teacher_cannot_manage_foreign_course_assignments(self):
        response = self.client.post(
            f"/api/courses/{self.foreign_course_id}/assistants",
            headers=self.auth_headers("teacher"),
            json={"assistant_id": self.second_assistant_id},
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_manage_any_course_assignments(self):
        response = self.client.post(
            f"/api/courses/{self.foreign_course_id}/assistants",
            headers=self.auth_headers("admin"),
            json={"assistant_id": self.second_assistant_id},
        )

        self.assertEqual(response.status_code, 201)


if __name__ == "__main__":
    unittest.main()
