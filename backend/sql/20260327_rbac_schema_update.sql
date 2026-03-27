-- RBAC + table/index hardening (single-college mode)
-- Run on MySQL in database: teaching_system

-- 1) Assistant-course assignment table
CREATE TABLE IF NOT EXISTS assistant_course_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assistant_id INT NOT NULL,
    course_id INT NOT NULL,
    assigned_by INT NOT NULL,
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_assignment_assistant FOREIGN KEY (assistant_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_assignment_course FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    CONSTRAINT fk_assignment_assigner FOREIGN KEY (assigned_by) REFERENCES users(id),
    CONSTRAINT uq_assistant_course UNIQUE (assistant_id, course_id),
    INDEX idx_assignment_course (course_id),
    INDEX idx_assignment_assistant (assistant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) Deduplicate attendance rows before unique constraint
DELETE a1
FROM attendances a1
JOIN attendances a2
  ON a1.student_id = a2.student_id
 AND a1.course_id = a2.course_id
 AND a1.date = a2.date
 AND a1.id > a2.id;

-- 3) Unique + query indexes (idempotent by information_schema checks)
SET @schema_name := DATABASE();

SET @exists := (
  SELECT COUNT(*) FROM information_schema.table_constraints
  WHERE table_schema = @schema_name
    AND table_name = 'attendances'
    AND constraint_name = 'uq_attendance_student_course_date'
);
SET @sql := IF(@exists = 0,
  'ALTER TABLE attendances ADD CONSTRAINT uq_attendance_student_course_date UNIQUE (student_id, course_id, date)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.statistics
  WHERE table_schema = @schema_name
    AND table_name = 'attendances'
    AND index_name = 'idx_attendance_course_date'
);
SET @sql := IF(@exists = 0,
  'CREATE INDEX idx_attendance_course_date ON attendances(course_id, date)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.statistics
  WHERE table_schema = @schema_name
    AND table_name = 'homeworks'
    AND index_name = 'idx_homework_course_student'
);
SET @sql := IF(@exists = 0,
  'CREATE INDEX idx_homework_course_student ON homeworks(course_id, student_id)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.statistics
  WHERE table_schema = @schema_name
    AND table_name = 'quizzes'
    AND index_name = 'idx_quiz_course_student'
);
SET @sql := IF(@exists = 0,
  'CREATE INDEX idx_quiz_course_student ON quizzes(course_id, student_id)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.statistics
  WHERE table_schema = @schema_name
    AND table_name = 'interactions'
    AND index_name = 'idx_interaction_course_student_date'
);
SET @sql := IF(@exists = 0,
  'CREATE INDEX idx_interaction_course_student_date ON interactions(course_id, student_id, date)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.statistics
  WHERE table_schema = @schema_name
    AND table_name = 'warnings'
    AND index_name = 'idx_warning_course_status_level'
);
SET @sql := IF(@exists = 0,
  'CREATE INDEX idx_warning_course_status_level ON warnings(course_id, status, level)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @exists := (
  SELECT COUNT(*) FROM information_schema.statistics
  WHERE table_schema = @schema_name
    AND table_name = 'warnings'
    AND index_name = 'idx_warning_student_created'
);
SET @sql := IF(@exists = 0,
  'CREATE INDEX idx_warning_student_created ON warnings(student_id, created_at)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
