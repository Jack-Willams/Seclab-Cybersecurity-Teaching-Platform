USE `seclab_profile`;


CREATE TABLE IF NOT EXISTS `teacher_intervention` (
  `intervention_id` BIGINT NOT NULL AUTO_INCREMENT,
  `teacher_id` BIGINT NOT NULL,
  `teaching_class_id` BIGINT NOT NULL,
  `course_id` INT NULL,
  `title` VARCHAR(255) NOT NULL,
  `action_type` VARCHAR(32) NOT NULL,
  `knowledge_point_id` BIGINT NULL,
  `description` TEXT NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  `baseline_at` DATETIME(6) NOT NULL,
  `due_at` DATETIME(6) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`intervention_id`),
  KEY `idx_intervention_class_status_due` (`teaching_class_id`, `status`, `due_at`),
  KEY `idx_intervention_teacher_time` (`teacher_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `teacher_intervention_student` (
  `intervention_id` BIGINT NOT NULL,
  `student_id` BIGINT NOT NULL,
  `baseline_snapshot_json` JSON NULL,
  `latest_snapshot_json` JSON NULL,
  `assignment_status` VARCHAR(16) NOT NULL DEFAULT 'PENDING',
  `training_session_id` VARCHAR(64) NULL,
  `started_at` DATETIME(6) NULL,
  `completed_at` DATETIME(6) NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`intervention_id`, `student_id`),
  KEY `idx_intervention_student_status` (`student_id`, `assignment_status`, `updated_at`),
  KEY `idx_intervention_training_session` (`training_session_id`),
  CONSTRAINT `fk_intervention_student_parent`
    FOREIGN KEY (`intervention_id`) REFERENCES `teacher_intervention` (`intervention_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `teacher_intervention_question` (
  `intervention_id` BIGINT NOT NULL,
  `generated_question_id` VARCHAR(64) NOT NULL,
  `usage_type` VARCHAR(32) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`intervention_id`, `generated_question_id`, `usage_type`),
  KEY `idx_intervention_question` (`generated_question_id`, `created_at`),
  CONSTRAINT `fk_intervention_question_parent`
    FOREIGN KEY (`intervention_id`) REFERENCES `teacher_intervention` (`intervention_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `teacher_intervention_exercise_snapshot` (
  `snapshot_id` BIGINT NOT NULL AUTO_INCREMENT,
  `intervention_id` BIGINT NOT NULL,
  `source_exercise_id` BIGINT NOT NULL,
  `source_version` INT NOT NULL,
  `snapshot_json` LONGTEXT NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`snapshot_id`),
  UNIQUE KEY `uk_intervention_exercise_snapshot` (`intervention_id`, `source_exercise_id`),
  CONSTRAINT `fk_intervention_exercise_snapshot_parent`
    FOREIGN KEY (`intervention_id`) REFERENCES `teacher_intervention` (`intervention_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

