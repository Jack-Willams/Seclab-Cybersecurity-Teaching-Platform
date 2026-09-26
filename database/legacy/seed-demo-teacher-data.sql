-- Non-destructive demo teacher data for the teacher dashboard.
-- This script creates a demo teacher/admin account and points it at the existing
-- SecLab演示班 used by seed-demo-scoreboard-data.sql.
-- It does not delete, truncate, reset, or rebuild any historical data.

CREATE DATABASE IF NOT EXISTS `userservice`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

INSERT INTO `userservice`.`class` (`class_name`, `class_detail`, `is_end`)
SELECT 'SecLab演示班', '教师首页和排行榜演示数据班级', 0
WHERE NOT EXISTS (
  SELECT 1 FROM `userservice`.`class` WHERE `class_name` = 'SecLab演示班'
);

SET @teacher_demo_class_id := (
  SELECT `class_id`
  FROM `userservice`.`class`
  WHERE `class_name` = 'SecLab演示班'
  ORDER BY `class_id`
  LIMIT 1
);

INSERT INTO `userservice`.`user` (
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
  `is_deleted`,
  `create_time`
)
SELECT
  'teacher_demo',
  '13c78700203b4e09d8b1f260e463e4ac',
  'SecLab演示教师',
  2,
  'SecLab演示学院',
  NULL,
  NULL,
  NULL,
  @teacher_demo_class_id,
  b'1',
  0,
  NOW(6)
WHERE NOT EXISTS (
  SELECT 1
  FROM `userservice`.`user`
  WHERE `user_student_number` = 'teacher_demo'
);

SET @teacher_demo_user_id := (
  SELECT `user_id`
  FROM `userservice`.`user`
  WHERE `user_student_number` = 'teacher_demo'
  LIMIT 1
);

UPDATE `userservice`.`class`
SET `admin_id` = COALESCE(`admin_id`, @teacher_demo_user_id),
    `class_detail` = COALESCE(`class_detail`, '教师首页和排行榜演示数据班级')
WHERE `class_id` = @teacher_demo_class_id;
