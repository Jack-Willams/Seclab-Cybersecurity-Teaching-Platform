CREATE DATABASE IF NOT EXISTS `seclab_profile`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `seclab_profile`;

-- Incremental compatibility for the existing question_submission evidence chain.
SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'question_submission' AND COLUMN_NAME = 'question_uid') = 0,
  'ALTER TABLE `question_submission` ADD COLUMN `question_uid` VARCHAR(128) NULL AFTER `question_id`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'question_submission' AND COLUMN_NAME = 'question_source') = 0,
  'ALTER TABLE `question_submission` ADD COLUMN `question_source` VARCHAR(64) NOT NULL DEFAULT ''course_question'' AFTER `cost_time`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'question_submission' AND COLUMN_NAME = 'training_session_id') = 0,
  'ALTER TABLE `question_submission` ADD COLUMN `training_session_id` VARCHAR(64) NULL AFTER `question_source`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'question_submission' AND COLUMN_NAME = 'knowledge_point_id') = 0,
  'ALTER TABLE `question_submission` ADD COLUMN `knowledge_point_id` BIGINT NULL AFTER `training_session_id`',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.STATISTICS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'question_submission' AND INDEX_NAME = 'idx_question_submission_uid') = 0,
  'CREATE INDEX `idx_question_submission_uid` ON `question_submission` (`question_uid`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.STATISTICS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'question_submission' AND INDEX_NAME = 'idx_question_submission_training') = 0,
  'CREATE INDEX `idx_question_submission_training` ON `question_submission` (`training_session_id`, `created_at`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.STATISTICS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'question_submission' AND INDEX_NAME = 'idx_question_submission_kp_time') = 0,
  'CREATE INDEX `idx_question_submission_kp_time` ON `question_submission` (`knowledge_point_id`, `created_at`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = IF(
  (SELECT COUNT(*) FROM information_schema.STATISTICS
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'question_submission' AND INDEX_NAME = 'idx_question_submission_source_time') = 0,
  'CREATE INDEX `idx_question_submission_source_time` ON `question_submission` (`question_source`, `created_at`)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS `knowledge_point` (
  `knowledge_point_id` BIGINT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `category` VARCHAR(64) NULL,
  `description` TEXT NULL,
  `difficulty_level` VARCHAR(32) NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`knowledge_point_id`),
  KEY `idx_knowledge_point_category` (`category`),
  KEY `idx_knowledge_point_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `module_knowledge_point` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `module_id` BIGINT NOT NULL,
  `knowledge_point_id` BIGINT NOT NULL,
  `relevance_weight` DECIMAL(5,2) NOT NULL DEFAULT 1.00,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_module_knowledge_point` (`module_id`, `knowledge_point_id`),
  KEY `idx_module_kp_module` (`module_id`),
  KEY `idx_module_kp_kp` (`knowledge_point_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `task_knowledge_point` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `module_id` BIGINT NULL,
  `task_id` BIGINT NOT NULL,
  `knowledge_point_id` BIGINT NOT NULL,
  `relevance_weight` DECIMAL(5,2) NOT NULL DEFAULT 1.00,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_task_knowledge_point` (`module_id`, `task_id`, `knowledge_point_id`),
  KEY `idx_task_kp_task` (`task_id`),
  KEY `idx_task_kp_module_task` (`module_id`, `task_id`),
  KEY `idx_task_kp_kp` (`knowledge_point_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `question_knowledge_point` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `question_id` BIGINT NULL,
  `question_uid` VARCHAR(128) NULL,
  `generated_question_id` VARCHAR(64) NULL,
  `knowledge_point_id` BIGINT NOT NULL,
  `relevance_weight` DECIMAL(5,2) NOT NULL DEFAULT 1.00,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  KEY `idx_question_kp_question_id` (`question_id`),
  KEY `idx_question_kp_question_uid` (`question_uid`),
  KEY `idx_question_kp_generated` (`generated_question_id`),
  KEY `idx_question_kp_kp` (`knowledge_point_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `training_session` (
  `training_session_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NOT NULL,
  `class_id` BIGINT NULL,
  `course_id` BIGINT NULL,
  `profile_snapshot_id` VARCHAR(64) NULL,
  `source_type` VARCHAR(64) NOT NULL DEFAULT 'personalized_training',
  `diagnose_result_json` JSON NOT NULL,
  `training_context_json` JSON NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`training_session_id`),
  KEY `idx_training_session_user_time` (`user_id`, `created_at`),
  KEY `idx_training_session_course_time` (`course_id`, `created_at`),
  KEY `idx_training_session_profile` (`profile_snapshot_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `generated_question` (
  `generated_question_id` VARCHAR(64) NOT NULL,
  `question_numeric_id` BIGINT NOT NULL,
  `training_session_id` VARCHAR(64) NOT NULL,
  `question_type` VARCHAR(64) NOT NULL,
  `knowledge_point_id` BIGINT NULL,
  `module_id` BIGINT NULL,
  `task_id` BIGINT NULL,
  `difficulty` VARCHAR(32) NULL,
  `title` VARCHAR(255) NOT NULL,
  `stem` TEXT NOT NULL,
  `options_json` JSON NULL,
  `standard_answer` TEXT NULL,
  `reference_answer` TEXT NULL,
  `explanation` TEXT NULL,
  `scoring_rubric_json` JSON NULL,
  `source_model` VARCHAR(128) NULL,
  `raw_ai_json` JSON NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`generated_question_id`),
  UNIQUE KEY `uk_generated_question_numeric` (`question_numeric_id`),
  KEY `idx_generated_question_session` (`training_session_id`),
  KEY `idx_generated_question_kp` (`knowledge_point_id`),
  KEY `idx_generated_question_module_task` (`module_id`, `task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `generated_question_attempt` (
  `attempt_id` VARCHAR(64) NOT NULL,
  `training_session_id` VARCHAR(64) NOT NULL,
  `generated_question_id` VARCHAR(64) NOT NULL,
  `user_id` BIGINT NOT NULL,
  `answer_json` JSON NOT NULL,
  `is_correct` TINYINT(1) NULL,
  `score` DECIMAL(8,2) NOT NULL DEFAULT 0,
  `cost_time` INT NULL,
  `submission_id` VARCHAR(64) NULL,
  `profile_rebuild_snapshot_id` VARCHAR(64) NULL,
  `submitted_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`attempt_id`),
  KEY `idx_generated_attempt_session` (`training_session_id`, `submitted_at`),
  KEY `idx_generated_attempt_question` (`generated_question_id`, `submitted_at`),
  KEY `idx_generated_attempt_user_time` (`user_id`, `submitted_at`),
  KEY `idx_generated_attempt_submission` (`submission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `knowledge_point`
  (`knowledge_point_id`, `name`, `category`, `description`, `difficulty_level`, `is_active`)
VALUES
  (101, 'SQL注入联合查询列数判断', 'SQL注入', '通过ORDER BY、UNION SELECT等方式判断字段数和回显位。', 'medium', 1),
  (102, 'SQL盲注与时间延迟判断', 'SQL注入', '通过布尔条件或sleep延迟推断数据库内容。', 'medium', 1),
  (201, 'XSS输入输出上下文判断', 'XSS', '识别HTML、属性、脚本等上下文并选择合适payload。', 'easy', 1),
  (301, 'CSRF Token校验与请求伪造', 'CSRF', '理解跨站请求伪造、Token绑定和Referer校验。', 'medium', 1),
  (401, '无空格命令执行绕过', '命令执行', '使用IFS、变量替换、重定向等方式替代空格完成命令拼接。', 'medium', 1),
  (402, '命令执行黑名单字符绕过', '命令执行', '针对过滤规则使用编码、拼接、环境变量或通配符绕过。', 'hard', 1),
  (501, '文件上传类型校验绕过', '文件上传', '围绕后缀、MIME、Content-Type和解析差异构造上传绕过。', 'medium', 1),
  (601, '目录遍历路径规范化绕过', '目录遍历', '理解../、编码、绝对路径和路径归一化绕过。', 'medium', 1)
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `category` = VALUES(`category`),
  `description` = VALUES(`description`),
  `difficulty_level` = VALUES(`difficulty_level`),
  `is_active` = 1;

INSERT IGNORE INTO `module_knowledge_point` (`module_id`, `knowledge_point_id`, `relevance_weight`) VALUES
  (1, 101, 1.00), (1, 102, 1.00), (2, 201, 1.00), (3, 301, 1.00),
  (4, 401, 1.00), (4, 402, 1.00), (5, 501, 1.00), (6, 601, 1.00);

INSERT IGNORE INTO `task_knowledge_point` (`module_id`, `task_id`, `knowledge_point_id`, `relevance_weight`) VALUES
  (1, 1, 101, 1.00), (1, 2, 102, 1.00), (2, 1, 201, 1.00), (3, 1, 301, 1.00),
  (4, 1, 401, 1.00), (4, 2, 402, 1.00), (5, 1, 501, 1.00), (6, 1, 601, 1.00);
