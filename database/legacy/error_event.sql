CREATE DATABASE IF NOT EXISTS `seclab_profile`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `seclab_profile`;

CREATE TABLE IF NOT EXISTS `error_event` (
  `error_id` VARCHAR(64) NOT NULL,
  `lab_session_id` VARCHAR(64) NULL,
  `user_id` BIGINT NULL,
  `class_id` BIGINT NULL,
  `course_id` BIGINT NULL,
  `module_id` BIGINT NULL,
  `task_id` BIGINT NULL,
  `container_name` VARCHAR(128) NULL,
  `command_id` VARCHAR(64) NULL,
  `error_signature` VARCHAR(64) NOT NULL,
  `error_category` VARCHAR(64) NOT NULL,
  `raw_excerpt` VARCHAR(1024) NULL,
  `severity` VARCHAR(32) NOT NULL DEFAULT 'low',
  `source` VARCHAR(64) NOT NULL DEFAULT 'api',
  `request_id` VARCHAR(64) NULL,
  `occurred_at` DATETIME(6) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`error_id`),
  KEY `idx_error_event_session_time` (`lab_session_id`, `occurred_at`),
  KEY `idx_error_event_user_time` (`user_id`, `occurred_at`),
  KEY `idx_error_event_module_time` (`module_id`, `occurred_at`),
  KEY `idx_error_event_command` (`command_id`),
  KEY `idx_error_event_signature_time` (`error_signature`, `occurred_at`),
  KEY `idx_error_event_category_time` (`error_category`, `occurred_at`),
  KEY `idx_error_event_request_id` (`request_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
