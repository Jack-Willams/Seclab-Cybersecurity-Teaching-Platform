CREATE DATABASE IF NOT EXISTS `seclab_profile`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `seclab_profile`;

CREATE TABLE IF NOT EXISTS `learning_event` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `event_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NULL,
  `class_id` BIGINT NULL,
  `course_id` BIGINT NULL,
  `module_id` BIGINT NULL,
  `task_id` BIGINT NULL,
  `question_id` BIGINT NULL,
  `lab_session_id` VARCHAR(64) NULL,
  `event_type` VARCHAR(64) NOT NULL,
  `event_time` DATETIME(6) NOT NULL,
  `payload_json` JSON NOT NULL,
  `source` VARCHAR(64) NOT NULL DEFAULT 'ai-agent-service',
  `request_id` VARCHAR(64) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_learning_event_event_id` (`event_id`),
  KEY `idx_learning_event_user_time` (`user_id`, `event_time`),
  KEY `idx_learning_event_module_time` (`module_id`, `event_time`),
  KEY `idx_learning_event_lab_session_time` (`lab_session_id`, `event_time`),
  KEY `idx_learning_event_type_time` (`event_type`, `event_time`),
  KEY `idx_learning_event_request_id` (`request_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
