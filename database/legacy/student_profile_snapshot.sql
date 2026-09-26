CREATE DATABASE IF NOT EXISTS `seclab_profile`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `seclab_profile`;

CREATE TABLE IF NOT EXISTS `student_profile_snapshot` (
  `snapshot_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NOT NULL,
  `class_id` BIGINT NULL,
  `course_id` BIGINT NULL,
  `computed_at` DATETIME(6) NOT NULL,
  `knowledge_mastery_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `troubleshooting_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `autonomy_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `ai_collaboration_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `engagement_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `overall_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `profile_summary_json` JSON NOT NULL,
  `source_range_start` DATETIME(6) NULL,
  `source_range_end` DATETIME(6) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`snapshot_id`),
  KEY `idx_student_profile_user_time` (`user_id`, `computed_at`),
  KEY `idx_student_profile_class_time` (`class_id`, `computed_at`),
  KEY `idx_student_profile_course_time` (`course_id`, `computed_at`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `student_profile_feature_daily` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `stat_date` DATE NOT NULL,
  `question_submit_count` INT NOT NULL DEFAULT 0,
  `question_correct_count` INT NOT NULL DEFAULT 0,
  `flag_submit_count` INT NOT NULL DEFAULT 0,
  `flag_correct_count` INT NOT NULL DEFAULT 0,
  `lab_session_count` INT NOT NULL DEFAULT 0,
  `completed_lab_count` INT NOT NULL DEFAULT 0,
  `ai_message_count` INT NOT NULL DEFAULT 0,
  `ai_user_message_count` INT NOT NULL DEFAULT 0,
  `ai_assistant_message_count` INT NOT NULL DEFAULT 0,
  `command_count` INT NOT NULL DEFAULT 0,
  `unique_command_count` INT NOT NULL DEFAULT 0,
  `file_change_count` INT NOT NULL DEFAULT 0,
  `error_count` INT NOT NULL DEFAULT 0,
  `high_severity_error_count` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_profile_feature_user_date` (`user_id`, `stat_date`),
  KEY `idx_profile_feature_user_date` (`user_id`, `stat_date`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
