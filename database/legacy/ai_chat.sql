CREATE DATABASE IF NOT EXISTS `seclab_profile`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `seclab_profile`;

CREATE TABLE IF NOT EXISTS `ai_conversation` (
  `conversation_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NULL,
  `class_id` BIGINT NULL,
  `course_id` BIGINT NULL,
  `module_id` BIGINT NULL,
  `task_id` BIGINT NULL,
  `question_id` BIGINT NULL,
  `lab_session_id` VARCHAR(64) NULL,
  `dify_conversation_id` VARCHAR(128) NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'active',
  `source` VARCHAR(64) NOT NULL DEFAULT 'ai-agent-service',
  `start_time` DATETIME(6) NOT NULL,
  `last_message_at` DATETIME(6) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`conversation_id`),
  UNIQUE KEY `uk_ai_conversation_dify_id` (`dify_conversation_id`),
  KEY `idx_ai_conversation_user_time` (`user_id`, `last_message_at`),
  KEY `idx_ai_conversation_module_time` (`module_id`, `last_message_at`),
  KEY `idx_ai_conversation_lab_session` (`lab_session_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ai_message` (
  `message_id` VARCHAR(64) NOT NULL,
  `conversation_id` VARCHAR(64) NOT NULL,
  `role` VARCHAR(32) NOT NULL,
  `content` LONGTEXT NOT NULL,
  `content_length` INT NOT NULL DEFAULT 0,
  `token_count` INT NULL,
  `event_name` VARCHAR(64) NULL,
  `hint_level` VARCHAR(32) NULL,
  `contains_context` TINYINT(1) NOT NULL DEFAULT 0,
  `contains_error_excerpt` TINYINT(1) NOT NULL DEFAULT 0,
  `raw_payload_json` JSON NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`message_id`),
  KEY `idx_ai_message_conversation_time` (`conversation_id`, `created_at`),
  KEY `idx_ai_message_role_time` (`role`, `created_at`),
  CONSTRAINT `fk_ai_message_conversation`
    FOREIGN KEY (`conversation_id`) REFERENCES `ai_conversation` (`conversation_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ai_tool_call` (
  `tool_call_id` VARCHAR(64) NOT NULL,
  `conversation_id` VARCHAR(64) NOT NULL,
  `message_id` VARCHAR(64) NULL,
  `tool_name` VARCHAR(128) NOT NULL,
  `tool_input_json` JSON NULL,
  `tool_output_json` JSON NULL,
  `status` VARCHAR(32) NOT NULL DEFAULT 'unknown',
  `error_message` TEXT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`tool_call_id`),
  KEY `idx_ai_tool_call_conversation_time` (`conversation_id`, `created_at`),
  KEY `idx_ai_tool_call_message` (`message_id`),
  KEY `idx_ai_tool_call_tool` (`tool_name`),
  CONSTRAINT `fk_ai_tool_call_conversation`
    FOREIGN KEY (`conversation_id`) REFERENCES `ai_conversation` (`conversation_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_ai_tool_call_message`
    FOREIGN KEY (`message_id`) REFERENCES `ai_message` (`message_id`)
    ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `ai_context_injection` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `conversation_id` VARCHAR(64) NOT NULL,
  `message_id` VARCHAR(64) NULL,
  `context_type` VARCHAR(64) NOT NULL,
  `context_summary` TEXT NULL,
  `context_size` INT NOT NULL DEFAULT 0,
  `raw_context_json` JSON NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `idx_ai_context_conversation_time` (`conversation_id`, `created_at`),
  KEY `idx_ai_context_message` (`message_id`),
  CONSTRAINT `fk_ai_context_conversation`
    FOREIGN KEY (`conversation_id`) REFERENCES `ai_conversation` (`conversation_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_ai_context_message`
    FOREIGN KEY (`message_id`) REFERENCES `ai_message` (`message_id`)
    ON DELETE SET NULL
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
