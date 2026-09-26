-- SecLab main business database initialization.
-- Scope: users/classes, course/module catalog, and image metadata.
-- Profile/event tables belong in init_seclab_profile.sql.

CREATE DATABASE IF NOT EXISTS `seclab_db`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `seclab_db`;

CREATE TABLE IF NOT EXISTS `class` (
  `class_id` BIGINT NOT NULL AUTO_INCREMENT,
  `admin_id` INT NULL,
  `class_detail` VARCHAR(255) NULL,
  `class_name` VARCHAR(255) NOT NULL,
  `is_end` INT NULL DEFAULT 0,
  PRIMARY KEY (`class_id`),
  UNIQUE KEY `uk_class_name` (`class_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user` (
  `user_id` BIGINT NOT NULL AUTO_INCREMENT,
  `create_time` DATETIME(6) NULL DEFAULT CURRENT_TIMESTAMP(6),
  `is_admin` BIT(1) NULL DEFAULT b'0',
  `user_role` VARCHAR(16) NOT NULL DEFAULT 'STUDENT',
  `is_deleted` INT NULL DEFAULT 0,
  `user_academy` VARCHAR(255) NULL,
  `user_email` VARCHAR(255) NULL,
  `user_gender` INT NULL DEFAULT 2,
  `user_image` VARCHAR(255) NULL,
  `user_name` VARCHAR(255) NULL,
  `user_password` VARCHAR(255) NOT NULL,
  `user_student_number` VARCHAR(13) NOT NULL,
  `user_tel` VARCHAR(11) NULL,
  `class_id_class_id` BIGINT NOT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_user_student_number` (`user_student_number`),
  KEY `idx_user_class_id` (`class_id_class_id`),
  KEY `idx_user_admin_deleted` (`is_admin`, `is_deleted`),
  KEY `idx_user_role_deleted` (`user_role`, `is_deleted`),
  CONSTRAINT `fk_user_class`
    FOREIGN KEY (`class_id_class_id`) REFERENCES `class` (`class_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `course` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `cost_time` INT NULL,
  `course_description` VARCHAR(1024) NOT NULL,
  `difficulty` INT NULL,
  `image_url` VARCHAR(255) NULL,
  `instructor` VARCHAR(255) NULL,
  `created_by` BIGINT NULL,
  `course_name` VARCHAR(255) NOT NULL,
  `schedule` VARCHAR(255) NULL,
  `course_status` TINYINT NULL DEFAULT 1,
  `tags` LONGTEXT NULL,
  `type` VARCHAR(255) NULL,
  PRIMARY KEY (`id`),
  KEY `idx_course_status_type` (`course_status`, `type`),
  KEY `idx_course_creator_status` (`created_by`, `course_status`),
  CONSTRAINT `fk_course_creator`
    FOREIGN KEY (`created_by`) REFERENCES `user` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `module` (
  `module_id` INT NOT NULL AUTO_INCREMENT,
  `difficulty` INT NULL,
  `image_id` INT NULL,
  `introduction` VARCHAR(1024) NULL,
  `module_name` VARCHAR(255) NULL,
  `task_points` LONGTEXT NULL,
  `type` LONGTEXT NULL,
  PRIMARY KEY (`module_id`),
  KEY `idx_module_difficulty` (`difficulty`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `module_course` (
  `module_id` INT NOT NULL,
  `course_id` INT NOT NULL,
  PRIMARY KEY (`module_id`, `course_id`),
  KEY `idx_module_course_course` (`course_id`),
  CONSTRAINT `fk_module_course_module`
    FOREIGN KEY (`module_id`) REFERENCES `module` (`module_id`),
  CONSTRAINT `fk_module_course_course`
    FOREIGN KEY (`course_id`) REFERENCES `course` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `images` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `content_type` VARCHAR(50) NULL,
  `filename` VARCHAR(255) NULL,
  `original_filename` VARCHAR(255) NULL,
  `path` VARCHAR(255) NULL,
  `size` BIGINT NULL,
  `upload_time` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  `url` VARCHAR(255) NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_images_filename` (`filename`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 行政班（class）与教师端教学班（teaching_class）保持一一对应：
-- 这里只建一个默认班，其余班级由教师在 /teacher/classes 建教学班后自动产生
-- （学生注册按教学班名 find-or-create，Excel 导入按名单里的行政班列 find-or-create）。
INSERT IGNORE INTO `class` (`class_id`, `class_name`, `class_detail`, `is_end`) VALUES
(1, '网络安全232班', 'SecLab 默认班级', 0);

-- 注意：本脚本建的是 `seclab_db`，而 user-service 实际连的是 `userservice`
-- （见 user-service/application.yml 的 datasource url）。行政班的老库自愈迁移
-- 统一放在 user-service-local-init.sql 里，不要在这里重复一份。

-- password: 123456; user-service upgrades legacy MD5 to BCrypt on successful login.
INSERT IGNORE INTO `user`
  (`user_id`, `user_student_number`, `user_password`, `user_name`, `user_gender`, `class_id_class_id`, `is_admin`, `user_role`, `is_deleted`)
VALUES
  (1, 'admin', 'e10adc3949ba59abbe56e057f20f883e', 'Administrator', 1, 1, b'1', 'TEACHER', 0),
  (2, '202400000001', 'e10adc3949ba59abbe56e057f20f883e', 'Demo Student', 1, 1, b'0', 'STUDENT', 0);

INSERT IGNORE INTO `course`
  (`id`, `cost_time`, `course_description`, `difficulty`, `image_url`, `instructor`, `course_name`, `schedule`, `course_status`, `tags`, `type`)
VALUES
  (1, 8, 'SQL injection fundamentals and defensive practice.', 3, 'a9fe8e50-ba21-45ef-abd5-50b717857502-course-sql-injection.png', 'SecLab Teacher', 'SQL注入攻防实战', '每周一', 1, '["SQL注入","Web安全"]', 'web'),
  (2, 6, 'XSS and CSRF attack and defense labs.', 2, 'eb678908-4878-4303-94ae-b3434d52612a-course-xss-deep-dive.png', 'SecLab Teacher', 'XSS漏洞深度解析', '每周二', 1, '["XSS","CSRF","Web安全"]', 'web'),
  (3, 7, 'File upload vulnerability exploitation and mitigation.', 3, '5780e906-42a1-4a88-ad06-d054bbf92735-3.文件上传漏洞突破.png', 'SecLab Teacher', '文件上传漏洞突破', '每周三', 1, '["文件上传","Web安全"]', 'web');

INSERT IGNORE INTO `module`
  (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `task_points`, `type`)
VALUES
  (1, 3, 101, 'SQL injection lab module.', 'SQL注入基础实验', '[]', '["SQL注入","Web安全"]'),
  (2, 2, 102, 'XSS and CSRF lab module.', 'XSS与CSRF基础实验', '[]', '["XSS","CSRF","Web安全"]'),
  (3, 3, 103, 'File upload lab module.', '文件上传基础实验', '[]', '["文件上传","Web安全"]');

INSERT IGNORE INTO `module_course` (`module_id`, `course_id`) VALUES
(1, 1),
(2, 2),
(3, 3);
