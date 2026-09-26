-- SecLab teacher workspace schema migration.
-- Canonical copy. Runtime initialization mirrors live in database/sql/.
-- Safe to run repeatedly on MySQL 8.

CREATE DATABASE IF NOT EXISTS `userservice`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS `seclab_profile`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Existing user accounts need an explicit role so teachers can create their
-- first teaching class without being inferred from legacy class.admin_id.
SET @sql := IF(
  EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'userservice'
      AND table_name = 'user'
      AND column_name = 'user_role'
  ),
  'SELECT 1',
  'ALTER TABLE `userservice`.`user` ADD COLUMN `user_role` VARCHAR(16) NOT NULL DEFAULT ''STUDENT'' AFTER `is_admin`'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := IF(
  EXISTS (
    SELECT 1 FROM information_schema.statistics
    WHERE table_schema = 'userservice'
      AND table_name = 'user'
      AND index_name = 'idx_user_role_deleted'
  ),
  'SELECT 1',
  'ALTER TABLE `userservice`.`user` ADD KEY `idx_user_role_deleted` (`user_role`, `is_deleted`)'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

UPDATE `userservice`.`user` u
SET u.`user_role` = CASE
  WHEN COALESCE(u.`is_admin` + 0, 0) = 1 THEN 'TEACHER'
  WHEN EXISTS (
    SELECT 1
    FROM `userservice`.`class` c
    WHERE c.`admin_id` = u.`user_id`
      AND COALESCE(c.`is_end`, 0) = 0
  ) THEN 'TEACHER'
  WHEN u.`user_role` IN ('STUDENT', 'TEACHER', 'ADMIN') THEN u.`user_role`
  ELSE 'STUDENT'
END
WHERE COALESCE(u.`is_admin` + 0, 0) = 1
   OR EXISTS (
     SELECT 1
     FROM `userservice`.`class` c
     WHERE c.`admin_id` = u.`user_id`
       AND COALESCE(c.`is_end`, 0) = 0
   )
   OR u.`user_role` IS NULL
   OR u.`user_role` NOT IN ('STUDENT', 'TEACHER', 'ADMIN');

-- Courses are shared for reading and selection. created_by controls edits.
SET @sql := IF(
  EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'userservice'
      AND table_name = 'course'
      AND column_name = 'created_by'
  ),
  'SELECT 1',
  'ALTER TABLE `userservice`.`course` ADD COLUMN `created_by` BIGINT NULL AFTER `instructor`'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := IF(
  EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_schema = 'userservice'
      AND table_name = 'course'
      AND constraint_name = 'fk_course_creator'
  ),
  'SELECT 1',
  'ALTER TABLE `userservice`.`course` ADD CONSTRAINT `fk_course_creator` FOREIGN KEY (`created_by`) REFERENCES `userservice`.`user` (`user_id`) ON DELETE SET NULL'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := IF(
  EXISTS (
    SELECT 1 FROM information_schema.statistics
    WHERE table_schema = 'userservice'
      AND table_name = 'course'
      AND index_name = 'idx_course_creator_status'
  ),
  'SELECT 1',
  'ALTER TABLE `userservice`.`course` ADD KEY `idx_course_creator_status` (`created_by`, `course_status`)'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS `userservice`.`teaching_class` (
  `teaching_class_id` BIGINT NOT NULL AUTO_INCREMENT,
  `class_name` VARCHAR(120) NOT NULL,
  `academic_year` VARCHAR(9) NOT NULL,
  `semester` TINYINT NOT NULL,
  `teacher_id` BIGINT NOT NULL,
  `start_date` DATE NULL,
  `end_date` DATE NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`teaching_class_id`),
  UNIQUE KEY `uk_teacher_term_class_name`
    (`teacher_id`, `academic_year`, `semester`, `class_name`),
  KEY `idx_teaching_class_teacher_status` (`teacher_id`, `status`),
  KEY `idx_teaching_class_term_status` (`academic_year`, `semester`, `status`),
  CONSTRAINT `fk_teaching_class_teacher`
    FOREIGN KEY (`teacher_id`) REFERENCES `userservice`.`user` (`user_id`),
  CONSTRAINT `chk_teaching_class_semester`
    CHECK (`semester` IN (1, 2)),
  CONSTRAINT `chk_teaching_class_status`
    CHECK (`status` IN ('ACTIVE', 'ARCHIVED')),
  CONSTRAINT `chk_teaching_class_dates`
    CHECK (`start_date` IS NULL OR `end_date` IS NULL OR `end_date` >= `start_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `userservice`.`teaching_class_student` (
  `teaching_class_id` BIGINT NOT NULL,
  `student_id` BIGINT NOT NULL,
  `source` VARCHAR(24) NOT NULL DEFAULT 'EXCEL_IMPORT',
  `joined_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`teaching_class_id`, `student_id`),
  KEY `idx_teaching_class_student_user` (`student_id`, `teaching_class_id`),
  CONSTRAINT `fk_teaching_class_student_class`
    FOREIGN KEY (`teaching_class_id`)
    REFERENCES `userservice`.`teaching_class` (`teaching_class_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_teaching_class_student_user`
    FOREIGN KEY (`student_id`) REFERENCES `userservice`.`user` (`user_id`),
  CONSTRAINT `chk_teaching_class_student_source`
    CHECK (`source` IN ('EXCEL_IMPORT', 'MANUAL'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `userservice`.`teaching_class_course` (
  `teaching_class_course_id` BIGINT NOT NULL AUTO_INCREMENT,
  `teaching_class_id` BIGINT NOT NULL,
  `course_id` INT NOT NULL,
  `teaching_order` INT NOT NULL,
  `planned_start_date` DATE NULL,
  `planned_end_date` DATE NULL,
  `teaching_content` TEXT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`teaching_class_course_id`),
  UNIQUE KEY `uk_teaching_class_course` (`teaching_class_id`, `course_id`),
  UNIQUE KEY `uk_teaching_class_order` (`teaching_class_id`, `teaching_order`),
  KEY `idx_teaching_class_course_course` (`course_id`, `teaching_class_id`),
  CONSTRAINT `fk_teaching_class_course_class`
    FOREIGN KEY (`teaching_class_id`)
    REFERENCES `userservice`.`teaching_class` (`teaching_class_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_teaching_class_course_course`
    FOREIGN KEY (`course_id`) REFERENCES `userservice`.`course` (`id`),
  CONSTRAINT `chk_teaching_class_course_order`
    CHECK (`teaching_order` > 0),
  CONSTRAINT `chk_teaching_class_course_dates`
    CHECK (
      `planned_start_date` IS NULL
      OR `planned_end_date` IS NULL
      OR `planned_end_date` >= `planned_start_date`
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET @sql := IF(
  EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'userservice'
      AND table_name = 'teaching_class_course'
      AND column_name = 'teaching_content'
  ),
  'SELECT 1',
  'ALTER TABLE `userservice`.`teaching_class_course` ADD COLUMN `teaching_content` TEXT NULL AFTER `planned_end_date`'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS `userservice`.`teaching_class_import_batch` (
  `import_batch_id` CHAR(36) NOT NULL,
  `teaching_class_id` BIGINT NOT NULL,
  `teacher_id` BIGINT NOT NULL,
  `file_sha256` CHAR(64) NOT NULL,
  `preview_json` JSON NOT NULL,
  `confirmed_result_json` JSON NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'PREVIEWED',
  `expires_at` DATETIME(6) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `confirmed_at` DATETIME(6) NULL,
  PRIMARY KEY (`import_batch_id`),
  KEY `idx_import_batch_class_status`
    (`teaching_class_id`, `status`, `expires_at`),
  KEY `idx_import_batch_teacher_created` (`teacher_id`, `created_at`),
  CONSTRAINT `fk_import_batch_class`
    FOREIGN KEY (`teaching_class_id`)
    REFERENCES `userservice`.`teaching_class` (`teaching_class_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_import_batch_teacher`
    FOREIGN KEY (`teacher_id`) REFERENCES `userservice`.`user` (`user_id`),
  CONSTRAINT `chk_import_batch_status`
    CHECK (`status` IN ('PREVIEWED', 'CONFIRMED', 'EXPIRED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `seclab_profile`.`teacher_typical_question` (
  `teacher_id` BIGINT NOT NULL,
  `generated_question_id` VARCHAR(64) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`teacher_id`, `generated_question_id`),
  UNIQUE KEY `uk_teacher_typical_question`
    (`teacher_id`, `generated_question_id`),
  KEY `idx_typical_question_question` (`generated_question_id`, `created_at`),
  CONSTRAINT `fk_typical_question_generated`
    FOREIGN KEY (`generated_question_id`)
    REFERENCES `seclab_profile`.`generated_question` (`generated_question_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `seclab_profile`.`teacher_class_analysis` (
  `teaching_class_id` BIGINT NOT NULL,
  `requested_by` BIGINT NULL,
  `analysis_status` VARCHAR(16) NOT NULL DEFAULT 'IDLE',
  `data_cutoff_at` DATETIME(6) NULL,
  `analysis_json` JSON NULL,
  `source_stats_json` JSON NULL,
  `last_attempt_at` DATETIME(6) NULL,
  `last_error_message` VARCHAR(500) NULL,
  `generated_at` DATETIME(6) NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`teaching_class_id`),
  KEY `idx_teacher_analysis_status` (`analysis_status`, `updated_at`),
  CONSTRAINT `chk_teacher_analysis_status`
    CHECK (`analysis_status` IN ('IDLE', 'RUNNING', 'READY'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- One row per teacher, teaching class, and student. Analyses are manual and
-- only the latest successful result is retained; failed refreshes keep it.
CREATE TABLE IF NOT EXISTS `seclab_profile`.`teacher_student_analysis` (
  `teacher_id` BIGINT NOT NULL,
  `teaching_class_id` BIGINT NOT NULL,
  `student_id` BIGINT NOT NULL,
  `analysis_status` VARCHAR(16) NOT NULL DEFAULT 'IDLE',
  `data_cutoff_at` DATETIME(6) NULL,
  `analysis_json` JSON NULL,
  `source_stats_json` JSON NULL,
  `last_attempt_at` DATETIME(6) NULL,
  `last_error_message` VARCHAR(500) NULL,
  `generated_at` DATETIME(6) NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`teacher_id`, `teaching_class_id`, `student_id`),
  KEY `idx_student_analysis_class_status`
    (`teaching_class_id`, `analysis_status`, `updated_at`),
  KEY `idx_student_analysis_student` (`student_id`, `updated_at`),
  CONSTRAINT `chk_teacher_student_analysis_status`
    CHECK (`analysis_status` IN ('IDLE', 'RUNNING', 'READY'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verification queries return 1 when the migration is complete.
SELECT COUNT(*) = 1 AS has_user_role
FROM information_schema.columns
WHERE table_schema = 'userservice'
  AND table_name = 'user'
  AND column_name = 'user_role';

SELECT COUNT(*) = 1 AS has_course_creator
FROM information_schema.columns
WHERE table_schema = 'userservice'
  AND table_name = 'course'
  AND column_name = 'created_by';

SELECT COUNT(*) = 4 AS has_teaching_tables
FROM information_schema.tables
WHERE table_schema = 'userservice'
  AND table_name IN (
    'teaching_class',
    'teaching_class_student',
    'teaching_class_course',
    'teaching_class_import_batch'
  );

SELECT COUNT(*) = 3 AS has_teacher_profile_tables
FROM information_schema.tables
WHERE table_schema = 'seclab_profile'
  AND table_name IN (
    'teacher_typical_question',
    'teacher_class_analysis',
    'teacher_student_analysis'
  );
