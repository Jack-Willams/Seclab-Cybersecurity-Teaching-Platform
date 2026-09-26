-- Minimal local bootstrap for the real user-service login and registration flow.
-- Local teacher account: T20260001 / 123456.

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
  `user_role` VARCHAR(16) NOT NULL DEFAULT 'STUDENT',
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
  KEY `idx_user_role_deleted` (`user_role`, `is_deleted`),
  CONSTRAINT `fk_user_class`
    FOREIGN KEY (`class_id_class_id`) REFERENCES `class` (`class_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `teaching_class` (
  `teaching_class_id` BIGINT NOT NULL AUTO_INCREMENT,
  `class_name` VARCHAR(120) NOT NULL,
  `academic_year` VARCHAR(9) NOT NULL,
  `semester` TINYINT NOT NULL,
  `teacher_id` BIGINT NOT NULL,
  `start_date` DATE NULL,
  `end_date` DATE NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`teaching_class_id`),
  UNIQUE KEY `uk_teacher_term_class_name`
    (`teacher_id`, `academic_year`, `semester`, `class_name`),
  KEY `idx_teaching_class_teacher_status` (`teacher_id`, `status`),
  KEY `idx_teaching_class_term_status` (`academic_year`, `semester`, `status`),
  CONSTRAINT `fk_teaching_class_teacher`
    FOREIGN KEY (`teacher_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `chk_teaching_class_semester` CHECK (`semester` IN (1, 2)),
  CONSTRAINT `chk_teaching_class_status`
    CHECK (`status` IN ('ACTIVE', 'ARCHIVED')),
  CONSTRAINT `chk_teaching_class_dates`
    CHECK (`start_date` IS NULL OR `end_date` IS NULL OR `end_date` >= `start_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `teaching_class_student` (
  `teaching_class_id` BIGINT NOT NULL,
  `student_id` BIGINT NOT NULL,
  `source` VARCHAR(24) NOT NULL DEFAULT 'EXCEL_IMPORT',
  `joined_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`teaching_class_id`, `student_id`),
  KEY `idx_teaching_class_student_user` (`student_id`, `teaching_class_id`),
  CONSTRAINT `fk_teaching_class_student_class`
    FOREIGN KEY (`teaching_class_id`) REFERENCES `teaching_class` (`teaching_class_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_teaching_class_student_user`
    FOREIGN KEY (`student_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `chk_teaching_class_student_source`
    CHECK (`source` IN ('EXCEL_IMPORT', 'MANUAL'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- course is created by experiment-module-service-local-init.sql before this
-- table is used by the application.
CREATE TABLE IF NOT EXISTS `teaching_class_course` (
  `teaching_class_course_id` BIGINT NOT NULL AUTO_INCREMENT,
  `teaching_class_id` BIGINT NOT NULL,
  `course_id` INT NOT NULL,
  `teaching_order` INT NOT NULL,
  `planned_start_date` DATE NULL,
  `planned_end_date` DATE NULL,
  `teaching_content` TEXT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`teaching_class_course_id`),
  UNIQUE KEY `uk_teaching_class_course` (`teaching_class_id`, `course_id`),
  UNIQUE KEY `uk_teaching_class_order` (`teaching_class_id`, `teaching_order`),
  KEY `idx_teaching_class_course_course` (`course_id`, `teaching_class_id`),
  CONSTRAINT `fk_teaching_class_course_class`
    FOREIGN KEY (`teaching_class_id`) REFERENCES `teaching_class` (`teaching_class_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_teaching_class_course_course`
    FOREIGN KEY (`course_id`) REFERENCES `course` (`id`),
  CONSTRAINT `chk_teaching_class_course_order` CHECK (`teaching_order` > 0),
  CONSTRAINT `chk_teaching_class_course_dates`
    CHECK (
      `planned_start_date` IS NULL
      OR `planned_end_date` IS NULL
      OR `planned_end_date` >= `planned_start_date`
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET @sql := IF(
  EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'userservice'
      AND table_name = 'teaching_class_course'
      AND column_name = 'teaching_content'
  ),
  'SELECT 1',
  'ALTER TABLE `teaching_class_course` ADD COLUMN `teaching_content` TEXT NULL AFTER `planned_end_date`'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS `teaching_class_import_batch` (
  `import_batch_id` CHAR(36) NOT NULL,
  `teaching_class_id` BIGINT NOT NULL,
  `teacher_id` BIGINT NOT NULL,
  `file_sha256` CHAR(64) NOT NULL,
  `preview_json` JSON NOT NULL,
  `confirmed_result_json` JSON NULL,
  `status` VARCHAR(16) NOT NULL DEFAULT 'PREVIEWED',
  `expires_at` DATETIME(6) NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `confirmed_at` DATETIME(6) NULL,
  PRIMARY KEY (`import_batch_id`),
  KEY `idx_import_batch_class_status`
    (`teaching_class_id`, `status`, `expires_at`),
  KEY `idx_import_batch_teacher_created` (`teacher_id`, `created_at`),
  CONSTRAINT `fk_import_batch_class`
    FOREIGN KEY (`teaching_class_id`) REFERENCES `teaching_class` (`teaching_class_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_import_batch_teacher`
    FOREIGN KEY (`teacher_id`) REFERENCES `user` (`user_id`),
  CONSTRAINT `chk_import_batch_status`
    CHECK (`status` IN ('PREVIEWED', 'CONFIRMED', 'EXPIRED'))
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
  `user_role`,
  `is_deleted`
)
SELECT
  'T20260001',
  'e10adc3949ba59abbe56e057f20f883e',
  '李伟',
  1,
  '网络安全学院',
  'liwei@seclab.edu.cn',
  '13800138000',
  NULL,
  (SELECT `class_id` FROM `class` WHERE `class_name` = '网络安全232班' ORDER BY `class_id` LIMIT 1),
  b'1',
  'TEACHER',
  0
WHERE NOT EXISTS (
  SELECT 1 FROM `user` WHERE `user_student_number` = 'T20260001'
);

-- ---------------------------------------------------------------------------
-- 行政班（class）与教师端教学班（teaching_class）对齐 —— 只保留教学班
--
-- 正常流程下两者天然同名：学生注册按所选教学班名 find-or-create 行政班，
-- Excel 导入按名单里的「行政班」列 find-or-create。老库里还留着两类脏数据：
--   1. 早期版本建的英文班名 "Cyber Security 23x"，排行榜/管理后台直接显示英文
--   2. 注册页班级下拉写死时期误建的班，不对应任何教学班
-- class_id 被 seclab_profile 的各类快照引用，所以只改名 / 只删空班，不重新编号。
-- 必须放在上面所有 INSERT 之后：默认班和 T20260001 建好了才做清理。
-- ---------------------------------------------------------------------------

-- 1) 英文班名就地改中文。uk_class_name 是唯一键，先让出被占用的目标名。
DELETE `dup` FROM `class` AS `dup`
WHERE `dup`.`class_name` IN ('网络安全231班', '网络安全232班', '网络安全233班')
  AND `dup`.`class_id` NOT IN (1, 2, 3)
  AND NOT EXISTS (
    SELECT 1 FROM `user` `u` WHERE `u`.`class_id_class_id` = `dup`.`class_id`
  );

UPDATE `class` SET `class_name` = '网络安全232班'
  WHERE `class_id` = 1 AND `class_name` = 'Cyber Security 232';
UPDATE `class` SET `class_name` = '网络安全231班'
  WHERE `class_id` = 2 AND `class_name` = 'Cyber Security 231';
UPDATE `class` SET `class_name` = '网络安全233班'
  WHERE `class_id` = 3 AND `class_name` = 'Cyber Security 233';

-- 2) 演示数据的 32 名学生（202321040501-0532）行政班挂在「网络安全233班」，
--    但他们在教师端属于教学班「网络安全232班」，两边名字对不上。
--    按教学班归位，只动这批演示学号，不碰任何其他学生。
UPDATE `user` `u`
JOIN `class` `src`
  ON `src`.`class_id` = `u`.`class_id_class_id` AND `src`.`class_name` = '网络安全233班'
JOIN `class` `dst`
  ON `dst`.`class_name` = '网络安全232班'
SET `u`.`class_id_class_id` = `dst`.`class_id`
WHERE `u`.`user_student_number` BETWEEN '202321040501' AND '202321040532';

-- 3) 删掉既没有学生、也不对应任何未归档教学班的行政班。
--    有学生的班一律保留，避免误伤真实数据；'网络安全232班' 是本脚本的默认班，永远保留。
DELETE `orphan` FROM `class` AS `orphan`
WHERE `orphan`.`class_name` <> '网络安全232班'
  AND NOT EXISTS (
    SELECT 1 FROM `user` `u` WHERE `u`.`class_id_class_id` = `orphan`.`class_id`
  )
  AND NOT EXISTS (
    SELECT 1 FROM `teaching_class` `tc`
    WHERE `tc`.`class_name` = `orphan`.`class_name`
      AND `tc`.`status` = 'ACTIVE'
  );
