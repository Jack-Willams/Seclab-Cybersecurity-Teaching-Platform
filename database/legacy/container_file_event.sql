CREATE DATABASE IF NOT EXISTS `seclab_profile`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `seclab_profile`;

CREATE TABLE IF NOT EXISTS `container_file_event` (
  `file_event_id` VARCHAR(64) NOT NULL,
  `lab_session_id` VARCHAR(64) NULL,
  `user_id` BIGINT NULL,
  `class_id` BIGINT NULL,
  `course_id` BIGINT NULL,
  `module_id` BIGINT NULL,
  `task_id` BIGINT NULL,
  `container_name` VARCHAR(128) NULL,
  `file_path` VARCHAR(2048) NOT NULL,
  `file_ext` VARCHAR(32) NULL,
  `action` VARCHAR(32) NOT NULL,
  `size_before` BIGINT NULL,
  `size_after` BIGINT NULL,
  `sha256` VARCHAR(64) NULL,
  `is_key_file` TINYINT(1) NOT NULL DEFAULT 0,
  `source` VARCHAR(64) NOT NULL DEFAULT 'watcher',
  `request_id` VARCHAR(64) NULL,
  `changed_at` DATETIME(6) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`file_event_id`),
  KEY `idx_container_file_session_time` (`lab_session_id`, `changed_at`),
  KEY `idx_container_file_user_time` (`user_id`, `changed_at`),
  KEY `idx_container_file_module_time` (`module_id`, `changed_at`),
  KEY `idx_container_file_container_time` (`container_name`, `changed_at`),
  KEY `idx_container_file_action_time` (`action`, `changed_at`),
  KEY `idx_container_file_request_id` (`request_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
