CREATE DATABASE IF NOT EXISTS `seclab_profile`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `seclab_profile`;

CREATE TABLE IF NOT EXISTS `lab_session` (
  `session_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NULL,
  `class_id` BIGINT NULL,
  `course_id` BIGINT NULL,
  `module_id` BIGINT NULL,
  `task_id` BIGINT NULL,
  `container_name` VARCHAR(128) NULL,
  `container_id` VARCHAR(128) NULL,
  `target_url` VARCHAR(512) NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'running',
  `start_time` DATETIME(6) NOT NULL,
  `end_time` DATETIME(6) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`session_id`),
  KEY `idx_lab_session_user_time` (`user_id`, `start_time`),
  KEY `idx_lab_session_module_time` (`module_id`, `start_time`),
  KEY `idx_lab_session_status` (`status`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `flag_submission` (
  `submission_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NULL,
  `class_id` BIGINT NULL,
  `course_id` BIGINT NULL,
  `module_id` BIGINT NULL,
  `task_id` BIGINT NULL,
  `lab_session_id` VARCHAR(64) NULL,
  `container_name` VARCHAR(128) NULL,
  `flag_text` VARCHAR(512) NOT NULL,
  `is_correct` TINYINT(1) NOT NULL DEFAULT 0,
  `score` DECIMAL(8,2) NOT NULL DEFAULT 0,
  `request_id` VARCHAR(64) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`submission_id`),
  KEY `idx_flag_submission_user_time` (`user_id`, `created_at`),
  KEY `idx_flag_submission_session_time` (`lab_session_id`, `created_at`),
  KEY `idx_flag_submission_module_time` (`module_id`, `created_at`),
  KEY `idx_flag_submission_request_id` (`request_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `challenge_completion_event` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NULL,
  `class_id` BIGINT NULL,
  `course_id` BIGINT NULL,
  `module_id` BIGINT NULL,
  `task_id` BIGINT NULL,
  `lab_session_id` VARCHAR(64) NULL,
  `completion_status` VARCHAR(32) NOT NULL,
  `total_time_seconds` INT NULL,
  `total_ai_ask_count` INT NOT NULL DEFAULT 0,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `idx_completion_user_time` (`user_id`, `created_at`),
  KEY `idx_completion_session` (`lab_session_id`),
  KEY `idx_completion_module_time` (`module_id`, `created_at`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
