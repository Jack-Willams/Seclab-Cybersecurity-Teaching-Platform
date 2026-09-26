USE `seclab_profile`;

CREATE TABLE IF NOT EXISTS `teacher_knowledge_analysis` (
  `analysis_id` BIGINT NOT NULL AUTO_INCREMENT,
  `teacher_id` BIGINT NOT NULL,
  `teaching_class_id` BIGINT NOT NULL,
  `course_id` INT NOT NULL,
  `knowledge_point_id` BIGINT NOT NULL,
  `analysis_status` VARCHAR(16) NOT NULL DEFAULT 'IDLE',
  `analysis_json` LONGTEXT NULL,
  `evidence_json` LONGTEXT NULL,
  `last_attempt_at` DATETIME(6) NULL,
  `last_error_message` VARCHAR(500) NULL,
  `generated_at` DATETIME(6) NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`analysis_id`),
  UNIQUE KEY `uk_teacher_knowledge_scope`
    (`teacher_id`, `teaching_class_id`, `course_id`, `knowledge_point_id`),
  KEY `idx_teacher_knowledge_lookup`
    (`teaching_class_id`, `course_id`, `knowledge_point_id`, `analysis_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `teacher_knowledge_exercise` (
  `exercise_id` BIGINT NOT NULL AUTO_INCREMENT,
  `analysis_id` BIGINT NOT NULL,
  `exercise_role` VARCHAR(24) NOT NULL,
  `question_type` VARCHAR(32) NOT NULL,
  `stem` TEXT NOT NULL,
  `options_json` LONGTEXT NULL,
  `standard_answer` LONGTEXT NOT NULL,
  `explanation` LONGTEXT NULL,
  `difficulty` INT NOT NULL DEFAULT 1,
  `generation_rationale` TEXT NULL,
  `review_status` VARCHAR(24) NOT NULL DEFAULT 'PENDING_REVIEW',
  `review_comment` TEXT NULL,
  `source_version` INT NOT NULL DEFAULT 1,
  `reviewed_by` BIGINT NULL,
  `reviewed_at` DATETIME(6) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`exercise_id`),
  UNIQUE KEY `uk_teacher_knowledge_exercise_role` (`analysis_id`, `exercise_role`),
  KEY `idx_teacher_knowledge_exercise_review` (`review_status`, `updated_at`),
  CONSTRAINT `fk_teacher_knowledge_exercise_analysis`
    FOREIGN KEY (`analysis_id`) REFERENCES `teacher_knowledge_analysis` (`analysis_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

