import io
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from openpyxl import load_workbook


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

TEST_DB_DIR = tempfile.mkdtemp(prefix="teaching-system-final-score-tests-")
TEST_DB_PATH = Path(TEST_DB_DIR) / "final_score.db"

os.environ["DATABASE_URI"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "final-score-test-secret"
os.environ["JWT_SECRET_KEY"] = "final-score-test-jwt-secret"

from app import create_app  # noqa: E402
from app.models import db, User, Course, Class, Student  # noqa: E402
from app.models.data import Attendance, Homework, Quiz, Interaction, FinalScore  # noqa: E402


class FinalScoreIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

        from werkzeug.security import generate_password_hash

        teacher = User(
            username="final_teacher",
            password_hash=generate_password_hash("123456"),
            name="期末教师",
            role="teacher",
        )
        db.session.add(teacher)
        db.session.flush()

        course = Course(
            name="期末建模课程",
            code="FINAL-101",
            semester="2026-2027-1",
            teacher_id=teacher.id,
        )
        db.session.add(course)
        db.session.flush()

        class_ = Class(name="期末测试班", course_id=course.id)
        db.session.add(class_)
        db.session.flush()

        student = Student(
            student_no="FINAL-STU-001",
            name="期末学生",
            gender="男",
            class_id=class_.id,
        )
        db.session.add(student)
        db.session.commit()

        self.teacher_id = teacher.id
        self.course_id = course.id
        self.student_id = student.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def auth_headers(self, username="final_teacher", password="123456"):
        response = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        self.assertEqual(response.status_code, 200)
        token = response.get_json()["data"]["token"]
        return {"Authorization": f"Bearer {token}"}

    def test_final_exam_import_creates_final_score_record(self):
        csv_content = (
            "student_no,title,score,max_score,duration\n"
            "FINAL-STU-001,Python程序设计期末,86,100,120\n"
        )

        response = self.client.post(
            "/api/data/import/final_exam",
            headers=self.auth_headers(),
            data={
                "course_id": str(self.course_id),
                "file": (io.BytesIO(csv_content.encode("utf-8")), "final_exam.csv"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FinalScore.query.count(), 1)
        self.assertEqual(Quiz.query.count(), 0)

        record = FinalScore.query.one()
        self.assertEqual(record.title, "Python程序设计期末")
        self.assertEqual(record.duration, 120)

    def test_export_scores_contains_final_exam_column(self):
        db.session.add(
            Attendance(
                student_id=self.student_id,
                course_id=self.course_id,
                date=date(2026, 3, 31),
                status="present",
            )
        )
        db.session.add(
            Homework(
                student_id=self.student_id,
                course_id=self.course_id,
                title="平时作业",
                score=80,
                max_score=100,
                status="graded",
            )
        )
        db.session.add(
            Quiz(
                student_id=self.student_id,
                course_id=self.course_id,
                title="随堂测验",
                score=90,
                max_score=100,
            )
        )
        db.session.add(
            FinalScore(
                student_id=self.student_id,
                course_id=self.course_id,
                title="期末考试",
                score=70,
                max_score=100,
            )
        )
        db.session.add(
            Interaction(
                student_id=self.student_id,
                course_id=self.course_id,
                type="discussion",
                count=2,
            )
        )
        db.session.commit()

        response = self.client.get(
            f"/api/export/scores?course_id={self.course_id}",
            headers=self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(io.BytesIO(response.data))
        sheet = workbook["成绩报表"]
        headers = [cell.value for cell in sheet[1]]

        self.assertIn("期末分(30%)", headers)
        self.assertIn("综合分", headers)


if __name__ == "__main__":
    unittest.main()
