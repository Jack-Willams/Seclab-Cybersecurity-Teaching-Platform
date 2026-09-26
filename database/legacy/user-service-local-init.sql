-- Minimal local bootstrap for the real user-service login and registration flow.
-- Default admin account: admin / 123456

CREATE DATABASE IF NOT EXISTS `userservice`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `userservice`;

CREATE TABLE IF NOT EXISTS `class` (
  `class_id` BIGINT NOT NULL AUTO_INCREMENT,
  `admin_id` INT DEFAULT NULL,
  `class_detail` VARCHAR(255) DEFAULT NULL,
  `class_name` VARCHAR(255) NOT NULL,
  `is_end` INT DEFAULT 0,
  PRIMARY KEY (`class_id`),
  UNIQUE KEY `uk_class_name` (`class_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user` (
  `user_id` BIGINT NOT NULL AUTO_INCREMENT,
  `create_time` DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
  `is_admin` BIT(1) DEFAULT b'0',
  `is_deleted` INT DEFAULT 0,
  `user_academy` VARCHAR(255) DEFAULT NULL,
  `user_email` VARCHAR(255) DEFAULT NULL,
  `user_gender` INT DEFAULT NULL,
  `user_image` VARCHAR(255) DEFAULT NULL,
  `user_name` VARCHAR(255) DEFAULT NULL,
  `user_password` VARCHAR(255) NOT NULL,
  `user_student_number` VARCHAR(13) NOT NULL,
  `user_tel` VARCHAR(11) DEFAULT NULL,
  `class_id_class_id` BIGINT NOT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_user_student_number` (`user_student_number`),
  KEY `idx_user_class_id` (`class_id_class_id`),
  CONSTRAINT `fk_user_class`
    FOREIGN KEY (`class_id_class_id`) REFERENCES `class` (`class_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `class` (`class_name`, `class_detail`, `is_end`)
SELECT '网络安全232班', '用户服务本地登录默认班级', 0
WHERE NOT EXISTS (
  SELECT 1 FROM `class` WHERE `class_name` = '网络安全232班'
);

INSERT INTO `user` (
  `user_student_number`,
  `user_password`,
  `user_name`,
  `user_gender`,
  `user_academy`,
  `user_email`,
  `user_tel`,
  `user_image`,
  `class_id_class_id`,
  `is_admin`,
  `is_deleted`
)
SELECT
  'admin',
  'e10adc3949ba59abbe56e057f20f883e',
  'Administrator',
  1,
  '网络安全学院',
  'admin@example.com',
  '13800138000',
  NULL,
  (SELECT `class_id` FROM `class` WHERE `class_name` = '网络安全232班' ORDER BY `class_id` LIMIT 1),
  b'1',
  0
WHERE NOT EXISTS (
  SELECT 1 FROM `user` WHERE `user_student_number` = 'admin'
);
