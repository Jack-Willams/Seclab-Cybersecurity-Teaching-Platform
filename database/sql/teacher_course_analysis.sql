USE `seclab_profile`;

CREATE TABLE IF NOT EXISTS `teacher_course_analysis` (
  `teacher_id` BIGINT NOT NULL,
  `teaching_class_id` BIGINT NOT NULL,
  `course_id` INT NOT NULL,
  `analysis_scope` VARCHAR(16) NOT NULL,
  `student_id` BIGINT NOT NULL DEFAULT 0,
  `analysis_status` VARCHAR(16) NOT NULL DEFAULT 'IDLE',
  `analysis_json` LONGTEXT NULL,
  `source_stats_json` LONGTEXT NULL,
  `data_cutoff_at` DATETIME(6) NULL,
  `last_attempt_at` DATETIME(6) NULL,
  `last_error_message` VARCHAR(500) NULL,
  `generated_at` DATETIME(6) NULL,
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`teacher_id`, `teaching_class_id`, `course_id`, `analysis_scope`, `student_id`),
  KEY `idx_teacher_course_analysis_lookup` (`teaching_class_id`, `course_id`, `analysis_scope`, `student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
