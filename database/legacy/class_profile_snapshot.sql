CREATE DATABASE IF NOT EXISTS `seclab_profile`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `seclab_profile`;

CREATE TABLE IF NOT EXISTS `class_profile_snapshot` (
  `snapshot_id` VARCHAR(64) NOT NULL,
  `class_id` BIGINT NOT NULL,
  `course_id` BIGINT NULL,
  `computed_at` DATETIME(6) NOT NULL,
  `student_count` INT NOT NULL DEFAULT 0,
  `class_avg_knowledge_mastery` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `class_avg_troubleshooting` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `class_avg_autonomy` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `class_avg_ai_collaboration` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `class_avg_engagement` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `class_overall_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `weak_dimensions_json` JSON NOT NULL,
  `strengths_json` JSON NOT NULL,
  `risk_students_json` JSON NOT NULL,
  `summary_json` JSON NOT NULL,
  `source_range_start` DATETIME(6) NULL,
  `source_range_end` DATETIME(6) NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`snapshot_id`),
  KEY `idx_class_profile_class_time` (`class_id`, `computed_at`),
  KEY `idx_class_profile_course_time` (`course_id`, `computed_at`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `class_profile_student_metric` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `class_id` BIGINT NOT NULL,
  `user_id` BIGINT NOT NULL,
  `snapshot_id` VARCHAR(64) NOT NULL,
  `overall_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `knowledge_mastery_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `troubleshooting_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `autonomy_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `ai_collaboration_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `engagement_score` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `risk_level` VARCHAR(16) NOT NULL DEFAULT 'low',
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_class_profile_metric_snapshot_user` (`snapshot_id`, `user_id`),
  KEY `idx_class_profile_metric_class_user` (`class_id`, `user_id`),
  KEY `idx_class_profile_metric_snapshot` (`snapshot_id`),
  KEY `idx_class_profile_metric_risk` (`class_id`, `risk_level`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
