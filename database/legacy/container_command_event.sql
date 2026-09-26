CREATE DATABASE IF NOT EXISTS `seclab_profile`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `seclab_profile`;

CREATE TABLE IF NOT EXISTS `container_command_event` (
  `command_id` VARCHAR(64) NOT NULL,
  `lab_session_id` VARCHAR(64) NULL,
  `user_id` BIGINT NULL,
  `class_id` BIGINT NULL,
  `course_id` BIGINT NULL,
  `module_id` BIGINT NULL,
  `task_id` BIGINT NULL,
  `container_name` VARCHAR(128) NULL,
  `command` VARCHAR(2048) NOT NULL,
  `normalized_command` VARCHAR(2048) NOT NULL,
  `cmd_category` VARCHAR(64) NOT NULL DEFAULT 'other',
  `cwd` VARCHAR(1024) NULL,
  `exit_code` INT NULL,
  `duration_ms` INT NULL,
  `output_digest` VARCHAR(512) NULL,
  `source` VARCHAR(64) NOT NULL DEFAULT 'hook',
  `request_id` VARCHAR(64) NULL,
  `executed_at` DATETIME(6) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`command_id`),
  KEY `idx_container_command_session_time` (`lab_session_id`, `executed_at`),
  KEY `idx_container_command_user_time` (`user_id`, `executed_at`),
  KEY `idx_container_command_module_time` (`module_id`, `executed_at`),
  KEY `idx_container_command_container_time` (`container_name`, `executed_at`),
  KEY `idx_container_command_category_time` (`cmd_category`, `executed_at`),
  KEY `idx_container_command_request_id` (`request_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
