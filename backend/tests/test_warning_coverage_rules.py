import os
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

TEST_DB_DIR = tempfile.mkdtemp(prefix="teaching-system-warning-tests-")
TEST_DB_PATH = Path(TEST_DB_DIR) / "warning_rules.db"

os.environ["DATABASE_URI"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "warning-test-secret"
os.environ["JWT_SECRET_KEY"] = "warning-test-jwt-secret"

from app import create_app  # noqa: E402
from app.models import db, User, Course, Class, Student, Warning  # noqa: E402
from app.models.data import Attendance, Homework, FinalScore  # noqa: E402
from app.services.warning_engine import WarningEngine  # noqa: E402
from app.services.weight_config import WeightConfig  # noqa: E402


class WarningCoverageRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()

        from werkzeug.security import generate_password_hash

        teacher = User(
            username="coverage_teacher",
            password_hash=generate_password_hash("123456"),
            name="覆盖教师",
            role="teacher",
        )
        db.session.add(teacher)
        db.session.flush()

        course = Course(
            name="覆盖规则课程",
            code="COVERAGE-101",
            semester="2026-2027-1",
            teacher_id=teacher.id,
        )
        db.session.add(course)
        db.session.flush()

        class_ = Class(name="覆盖测试班级", course_id=course.id)
        db.session.add(class_)
        db.session.flush()

        student = Student(
            student_no="COVERAGE-STU-001",
            name="覆盖规则学生",
            gender="男",
            class_id=class_.id,
        )
        db.session.add(student)
        db.session.commit()

        self.course_id = course.id
        self.student_id = student.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def test_partial_metrics_are_reweighted_instead_of_treated_as_full_score(self):
        metrics = {
            "attendance": 40,
            "homework": None,
            "quiz": None,
            "final_exam": None,
            "interaction": None,
        }

        result = WeightConfig.calculate_comprehensive_score(metrics)
        coverage = WeightConfig.get_coverage(metrics)

        self.assertEqual(result, 40.0)
        self.assertEqual(coverage["covered_count"], 1)
        self.assertEqual(coverage["missing_fields"], ["homework", "quiz", "final_exam", "interaction"])

    def test_no_available_metrics_returns_zero_score(self):
        metrics = {
            "attendance": None,
            "homework": None,
            "quiz": None,
            "final_exam": None,
            "interaction": None,
        }

        result = WeightConfig.calculate_comprehensive_score(metrics)
        coverage = WeightConfig.get_coverage(metrics)

        self.assertEqual(result, 0.0)
        self.assertEqual(coverage["covered_count"], 0)
        self.assertFalse(coverage["eligible_for_warning"])

    def test_warning_engine_does_not_warn_when_zero_or_one_metric_exists(self):
        engine = WarningEngine(self.course_id)

        generated_without_data = engine.check_all_students()
        self.assertEqual(generated_without_data, [])
        self.assertEqual(Warning.query.count(), 0)

        db.session.add(
            Attendance(
                student_id=self.student_id,
                course_id=self.course_id,
                date=date.today(),
                status="absent",
            )
        )
        db.session.commit()

        generated_with_one_metric = engine.check_all_students()
        self.assertEqual(generated_with_one_metric, [])
        self.assertEqual(Warning.query.count(), 0)

    def test_warning_engine_creates_warning_when_two_metrics_trigger_threshold(self):
        db.session.add(
            Attendance(
                student_id=self.student_id,
                course_id=self.course_id,
                date=date.today(),
                status="absent",
            )
        )
        db.session.add(
            Homework(
                student_id=self.student_id,
                course_id=self.course_id,
                title="低分作业",
                score=20,
                max_score=100,
                status="graded",
            )
        )
        db.session.commit()

        engine = WarningEngine(self.course_id)
        generated = engine.check_all_students()

        self.assertEqual(len(generated), 1)
        warning = Warning.query.one()
        self.assertEqual(warning.status, "active")
        self.assertEqual(warning.level, "red")
        self.assertEqual(warning.metrics["coverage"]["covered_count"], 2)
        self.assertEqual(warning.metrics["comprehensive_score"], 10.0)

    def test_warning_engine_uses_final_exam_in_comprehensive_score(self):
        db.session.add(
            Attendance(
                student_id=self.student_id,
                course_id=self.course_id,
                date=date.today(),
                status="present",
            )
        )
        db.session.add(
            FinalScore(
                student_id=self.student_id,
                course_id=self.course_id,
                title="期末考试",
                score=0,
                max_score=100,
            )
        )
        db.session.commit()

        engine = WarningEngine(self.course_id)
        generated = engine.check_all_students()

        self.assertEqual(len(generated), 1)
        warning = Warning.query.one()
        self.assertEqual(warning.level, "red")
        self.assertEqual(warning.metrics["coverage"]["covered_count"], 2)
        self.assertIn("final_exam", warning.metrics["coverage"]["covered_fields"])
        self.assertEqual(warning.metrics["comprehensive_score"], 40.0)

    def test_warning_is_cleared_when_coverage_drops_below_threshold(self):
        db.session.add(
            Attendance(
                student_id=self.student_id,
                course_id=self.course_id,
                date=date.today(),
                status="absent",
            )
        )
        low_homework = Homework(
            student_id=self.student_id,
            course_id=self.course_id,
            title="将被删除的作业",
            score=20,
            max_score=100,
            status="graded",
        )
        db.session.add(low_homework)
        db.session.commit()

        engine = WarningEngine(self.course_id)
        engine.check_all_students()

        warning = Warning.query.one()
        self.assertEqual(warning.status, "active")

        db.session.delete(low_homework)
        db.session.commit()

        engine.check_all_students()

        warning = Warning.query.one()
        self.assertEqual(warning.status, "cleared")


if __name__ == "__main__":
    unittest.main()
