import os
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import check_password_hash


class RbacUiRegressionTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[2]
        self.login_page = self.repo_root / "frontend" / "src" / "pages" / "login.html"
        self.warnings_page = self.repo_root / "frontend" / "src" / "pages" / "warnings.html"

    def test_login_page_lists_admin_and_assistant_demo_accounts(self):
        content = self.login_page.read_text(encoding="utf-8")
        self.assertIn("admin / 123456", content)
        self.assertIn("assistant / 123456", content)

    def test_warnings_page_has_auth_guard(self):
        content = self.warnings_page.read_text(encoding="utf-8")
        self.assertIn("checkAuth", content)
        self.assertIn("applyRoleUI", content)

    def test_default_admin_teacher_assistant_accounts_seeded(self):
        db_fd, db_path = tempfile.mkstemp(prefix="rbac_seed_", suffix=".db")
        os.close(db_fd)
        db_uri = f"sqlite:///{db_path}"

        old_db_uri = os.environ.get("DATABASE_URI")
        os.environ["DATABASE_URI"] = db_uri

        try:
            from app import create_app
            from app.models import User

            app = create_app()
            with app.app_context():
                users = {
                    user.username: user
                    for user in User.query.filter(
                        User.username.in_(["admin", "teacher", "assistant"])
                    ).all()
                }

                self.assertEqual({"admin", "teacher", "assistant"}, set(users.keys()))
                self.assertEqual("admin", users["admin"].role)
                self.assertEqual("teacher", users["teacher"].role)
                self.assertEqual("assistant", users["assistant"].role)
                self.assertTrue(check_password_hash(users["admin"].password_hash, "123456"))
                self.assertTrue(check_password_hash(users["teacher"].password_hash, "123456"))
                self.assertTrue(check_password_hash(users["assistant"].password_hash, "123456"))
        finally:
            if old_db_uri is None:
                os.environ.pop("DATABASE_URI", None)
            else:
                os.environ["DATABASE_URI"] = old_db_uri
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
