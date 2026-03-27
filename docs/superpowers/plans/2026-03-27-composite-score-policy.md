# Composite Score Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the agreed composite-score policy (no data → score 0, partial data → normalized score, coverage shown in detail, warnings only when ≥2 metrics).

**Architecture:** Add a small metrics summary helper in `WarningEngine`, then propagate `score`, `score_coverage`, and `score_is_empty` through student list and student profile APIs. Frontend detail view displays coverage only, list stays score-only.

**Tech Stack:** Flask + SQLAlchemy backend, vanilla JS frontend, unittest for tests.

---

## File Structure (Planned Touchpoints)

- Modify: `/Users/a2914452089/Desktop/teaching-system/backend/app/services/warning_engine.py`  
  Purpose: add helper to compute `available_metrics`, `score_is_empty`, `score_coverage`.

- Modify: `/Users/a2914452089/Desktop/teaching-system/backend/app/routes/courses.py`  
  Purpose: student list API returns `score`, `score_coverage`, `score_is_empty`.

- Modify: `/Users/a2914452089/Desktop/teaching-system/backend/app/routes/analytics.py`  
  Purpose: student profile API returns `score`, `score_coverage`, `score_is_empty`.

- Modify: `/Users/a2914452089/Desktop/teaching-system/frontend/src/pages/students.html`  
  Purpose: detail modal shows coverage text (e.g., `覆盖2/4项`).

- Create: `/Users/a2914452089/Desktop/teaching-system/backend/tests/test_score_policy.py`  
  Purpose: unit tests for score policy logic and API payloads.

---

### Task 1: Add Failing Tests For Score Policy

**Files:**
- Create: `/Users/a2914452089/Desktop/teaching-system/backend/tests/test_score_policy.py`

- [ ] **Step 1: Write the failing test**

```python
import os
import tempfile
import unittest

from datetime import date
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import db
from app.models import User, Course, Class, Student
from app.models.data import Attendance
from app.services.warning_engine import WarningEngine


class ScorePolicyTests(unittest.TestCase):
    def setUp(self):
        db_fd, db_path = tempfile.mkstemp(prefix="score_policy_", suffix=".db")
        os.close(db_fd)
        self._db_path = db_path
        os.environ["DATABASE_URI"] = f"sqlite:///{db_path}"

        app = create_app()
        self.app = app
        self.client = app.test_client()

        with app.app_context():
            admin = User(
                username="admin",
                password_hash=generate_password_hash("123456"),
                name="管理员",
                role="admin",
            )
            db.session.add(admin)
            course = Course(name="测试课程", code="T-001", teacher_id=1)
            db.session.add(course)
            db.session.flush()
            clazz = Class(name="测试班级", course_id=course.id)
            db.session.add(clazz)
            db.session.flush()
            student = Student(student_no="S001", name="学生A", class_id=clazz.id)
            db.session.add(student)
            db.session.commit()

            self.course_id = course.id
            self.student_id = student.id

    def tearDown(self):
        if os.path.exists(self._db_path):
            os.remove(self._db_path)

    def test_no_data_score_is_zero_and_empty(self):
        with self.app.app_context():
            engine = WarningEngine(self.course_id)
            metrics = engine._calculate_metrics(self.student_id)
            summary = engine.summarize_metrics(metrics)

            self.assertEqual(summary["score_is_empty"], True)
            self.assertEqual(summary["score_coverage"], "0/4")

    def test_single_metric_still_counts_coverage(self):
        with self.app.app_context():
            db.session.add(
                Attendance(
                    student_id=self.student_id,
                    course_id=self.course_id,
                    date=date.today(),
                    status="present",
                )
            )
            db.session.commit()

            engine = WarningEngine(self.course_id)
            metrics = engine._calculate_metrics(self.student_id)
            summary = engine.summarize_metrics(metrics)

            self.assertEqual(summary["score_is_empty"], False)
            self.assertEqual(summary["score_coverage"], "1/4")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```
cd /Users/a2914452089/Desktop/teaching-system/backend
source venv/bin/activate
python -m unittest tests/test_score_policy.py -v
```

Expected: FAIL because `summarize_metrics` does not exist yet.

- [ ] **Step 3: Commit the failing test**

```bash
git add /Users/a2914452089/Desktop/teaching-system/backend/tests/test_score_policy.py
git commit -m "test: add composite score policy coverage checks"
```

---

### Task 2: Add Metrics Summary Helper In WarningEngine

**Files:**
- Modify: `/Users/a2914452089/Desktop/teaching-system/backend/app/services/warning_engine.py`

- [ ] **Step 1: Implement minimal helper**

```python
    def summarize_metrics(self, metrics):
        available = self._get_available_metrics(metrics)
        coverage = f"{len(available)}/{len(self.WEIGHTS)}"
        return {
            "available_metrics": available,
            "score_is_empty": len(available) == 0,
            "score_coverage": coverage,
        }
```

- [ ] **Step 2: Run tests to verify they pass**

```
cd /Users/a2914452089/Desktop/teaching-system/backend
source venv/bin/activate
python -m unittest tests/test_score_policy.py -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add /Users/a2914452089/Desktop/teaching-system/backend/app/services/warning_engine.py
git commit -m "feat: add metrics summary helper for composite score"
```

---

### Task 3: Update Student List API Payload

**Files:**
- Modify: `/Users/a2914452089/Desktop/teaching-system/backend/app/routes/courses.py`

- [ ] **Step 1: Add failing test for API payload**

Extend `tests/test_score_policy.py`:

```python
    def test_student_list_includes_score_flags(self):
        with self.app.app_context():
            client = self.client
            # Directly call list endpoint (no auth in tests)
            response = client.get(f"/api/courses/{self.course_id}/classes/{self._get_class_id()}/students")
            data = response.get_json()
            student = data["data"][0]
            self.assertIn("score_is_empty", student)
            self.assertIn("score_coverage", student)
```

Add helper in the test file:

```python
    def _get_class_id(self):
        with self.app.app_context():
            return Class.query.first().id
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m unittest tests/test_score_policy.py -v
```

Expected: FAIL (missing fields).

- [ ] **Step 3: Implement payload update**

In the students list logic (where `score` is computed):

```python
                summary = engine.summarize_metrics(metrics)
                s_dict['score_is_empty'] = summary['score_is_empty']
                s_dict['score_coverage'] = summary['score_coverage']
                if summary['score_is_empty']:
                    s_dict['score'] = 0
                else:
                    s_dict['score'] = round(score, 1) if score is not None else 0
```

- [ ] **Step 4: Run tests to verify pass**

```
python -m unittest tests/test_score_policy.py -v
```

- [ ] **Step 5: Commit**

```bash
git add /Users/a2914452089/Desktop/teaching-system/backend/app/routes/courses.py \
        /Users/a2914452089/Desktop/teaching-system/backend/tests/test_score_policy.py
git commit -m "feat: include score coverage flags in student list"
```

---

### Task 4: Update Student Profile API Payload

**Files:**
- Modify: `/Users/a2914452089/Desktop/teaching-system/backend/app/routes/analytics.py`

- [ ] **Step 1: Add failing test for profile payload**

Extend `tests/test_score_policy.py`:

```python
    def test_student_profile_includes_score_flags(self):
        with self.app.app_context():
            response = self.client.get(
                f"/api/analytics/course/{self.course_id}/students/{self.student_id}/profile"
            )
            data = response.get_json()
            student = data["data"]["student"]
            self.assertIn("score_is_empty", student)
            self.assertIn("score_coverage", student)
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m unittest tests/test_score_policy.py -v
```

Expected: FAIL (missing fields).

- [ ] **Step 3: Implement payload update**

In `student_profile`:

```python
    summary = engine.summarize_metrics(metrics)
    score = engine._calculate_comprehensive_score(metrics)
    if summary["score_is_empty"]:
        score = 0

    ...
            'student': {
                ...
                'score': _safe_round(score, 1),
                'score_is_empty': summary['score_is_empty'],
                'score_coverage': summary['score_coverage'],
            },
```

- [ ] **Step 4: Run tests to verify pass**

```
python -m unittest tests/test_score_policy.py -v
```

- [ ] **Step 5: Commit**

```bash
git add /Users/a2914452089/Desktop/teaching-system/backend/app/routes/analytics.py \
        /Users/a2914452089/Desktop/teaching-system/backend/tests/test_score_policy.py
git commit -m "feat: include score coverage flags in student profile"
```

---

### Task 5: Show Coverage In Student Detail Modal

**Files:**
- Modify: `/Users/a2914452089/Desktop/teaching-system/frontend/src/pages/students.html`

- [ ] **Step 1: Add failing UI check (manual)**

Open a student detail; confirm coverage is not shown.

- [ ] **Step 2: Implement UI update**

In `viewStudent`, after computing `displayScore`:

```javascript
                const coverage = s.score_coverage || '0/4';
```

In modal header badge:

```html
                                <span class="badge bg-primary">综合评分：${displayScore}</span>
                                <span class="badge bg-light text-muted ms-2">覆盖${coverage}项</span>
```

- [ ] **Step 3: Manual verify**

Refresh page, open detail; expect coverage badge (e.g., “覆盖2/4项”).

- [ ] **Step 4: Commit**

```bash
git add /Users/a2914452089/Desktop/teaching-system/frontend/src/pages/students.html
git commit -m "feat: show score coverage in student detail"
```

---

## Self-Review Checklist

1. **Spec coverage:**  
   - No data → score 0: Task 3/4 handle via `score_is_empty`.  
   - Partial data → normalized score: existing engine logic remains.  
   - Coverage in detail only: Task 5.  
   - Warnings only if ≥2 metrics: unchanged logic.

2. **Placeholder scan:** No TODO/TBD placeholders remain.

3. **Type consistency:** `score_is_empty` and `score_coverage` used consistently in API + frontend.

---

## Execution Handoff

Plan complete and saved to `/Users/a2914452089/Desktop/teaching-system/docs/superpowers/plans/2026-03-27-composite-score-policy.md`.

Two execution options:
1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration  
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
