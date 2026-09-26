CREATE DATABASE IF NOT EXISTS `seclab_profile`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `seclab_profile`;

CREATE TABLE IF NOT EXISTS `question_submission` (
  `submission_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NULL,
  `class_id` BIGINT NULL,
  `course_id` BIGINT NULL,
  `module_id` BIGINT NULL,
  `task_id` BIGINT NULL,
  `question_id` BIGINT NOT NULL,
  `question_uid` VARCHAR(128) NULL,
  `question_type` VARCHAR(64) NOT NULL,
  `answer_json` JSON NOT NULL,
  `standard_answer_json` JSON NULL,
  `is_correct` TINYINT(1) NULL,
  `score` DECIMAL(8,2) NOT NULL DEFAULT 0,
  `cost_time` INT NULL,
  `question_source` VARCHAR(64) NOT NULL DEFAULT 'course_question',
  `training_session_id` VARCHAR(64) NULL,
  `knowledge_point_id` BIGINT NULL,
  `request_id` VARCHAR(64) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`submission_id`),
  KEY `idx_question_submission_user_time` (`user_id`, `created_at`),
  KEY `idx_question_submission_module_time` (`module_id`, `created_at`),
  KEY `idx_question_submission_question_time` (`question_id`, `created_at`),
  KEY `idx_question_submission_uid` (`question_uid`),
  KEY `idx_question_submission_training` (`training_session_id`, `created_at`),
  KEY `idx_question_submission_kp_time` (`knowledge_point_id`, `created_at`),
  KEY `idx_question_submission_source_time` (`question_source`, `created_at`),
  KEY `idx_question_submission_request_id` (`request_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
