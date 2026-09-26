-- Reproducible teacher-scope authorization seed.
-- Accounts use password 123456. user-service upgrades the legacy MD5 hash after login.
-- Prerequisites: user-service local schema in userservice and profile schema in seclab_profile.

USE `userservice`;

INSERT INTO `class` (`class_name`, `class_detail`, `is_end`)
VALUES
  ('SecLab教师权限A班', '教师权限测试A班', 0),
  ('SecLab教师权限B班', '教师权限测试B班', 0)
ON DUPLICATE KEY UPDATE
  `class_detail` = VALUES(`class_detail`),
  `is_end` = 0;

SET @class_a_id := (
  SELECT `class_id` FROM `class`
  WHERE `class_name` = 'SecLab教师权限A班'
  ORDER BY `class_id` LIMIT 1
);
SET @class_b_id := (
  SELECT `class_id` FROM `class`
  WHERE `class_name` = 'SecLab教师权限B班'
  ORDER BY `class_id` LIMIT 1
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
VALUES
  ('teacher_a', 'e10adc3949ba59abbe56e057f20f883e', '权限测试教师A', 2, '网络安全学院', 'teacher_a@example.com', '13800138101', NULL, @class_a_id, b'0', 0),
  ('teacher_b', 'e10adc3949ba59abbe56e057f20f883e', '权限测试教师B', 2, '网络安全学院', 'teacher_b@example.com', '13800138102', NULL, @class_b_id, b'0', 0),
  ('student_a', 'e10adc3949ba59abbe56e057f20f883e', '权限测试学生A', 0, '网络安全学院', 'student_a@example.com', '13800138201', NULL, @class_a_id, b'0', 0),
  ('student_b', 'e10adc3949ba59abbe56e057f20f883e', '权限测试学生B', 1, '网络安全学院', 'student_b@example.com', '13800138202', NULL, @class_b_id, b'0', 0)
ON DUPLICATE KEY UPDATE
  `user_name` = VALUES(`user_name`),
  `user_gender` = VALUES(`user_gender`),
  `user_academy` = VALUES(`user_academy`),
  `user_email` = VALUES(`user_email`),
  `user_tel` = VALUES(`user_tel`),
  `class_id_class_id` = VALUES(`class_id_class_id`),
  `is_admin` = b'0',
  `is_deleted` = 0;

SET @teacher_a_id := (
  SELECT `user_id` FROM `user`
  WHERE `user_student_number` = 'teacher_a'
  ORDER BY `user_id` LIMIT 1
);
SET @teacher_b_id := (
  SELECT `user_id` FROM `user`
  WHERE `user_student_number` = 'teacher_b'
  ORDER BY `user_id` LIMIT 1
);
SET @student_a_id := (
  SELECT `user_id` FROM `user`
  WHERE `user_student_number` = 'student_a'
  ORDER BY `user_id` LIMIT 1
);
SET @student_b_id := (
  SELECT `user_id` FROM `user`
  WHERE `user_student_number` = 'student_b'
  ORDER BY `user_id` LIMIT 1
);

UPDATE `class`
SET `admin_id` = @teacher_a_id
WHERE `class_id` = @class_a_id;

UPDATE `class`
SET `admin_id` = @teacher_b_id
WHERE `class_id` = @class_b_id;

USE `seclab_profile`;

INSERT INTO `training_session` (
  `training_session_id`,
  `user_id`,
  `class_id`,
  `course_id`,
  `source_type`,
  `diagnose_result_json`,
  `training_context_json`
)
VALUES
  ('teacher_scope_session_a', @student_a_id, @class_a_id, 1, 'teacher_scope_smoke', JSON_OBJECT('score', 80), JSON_OBJECT('seed', 'teacher_scope_a')),
  ('teacher_scope_session_b', @student_b_id, @class_b_id, 1, 'teacher_scope_smoke', JSON_OBJECT('score', 70), JSON_OBJECT('seed', 'teacher_scope_b'))
ON DUPLICATE KEY UPDATE
  `user_id` = VALUES(`user_id`),
  `class_id` = VALUES(`class_id`),
  `course_id` = VALUES(`course_id`),
  `source_type` = VALUES(`source_type`),
  `diagnose_result_json` = VALUES(`diagnose_result_json`),
  `training_context_json` = VALUES(`training_context_json`);

INSERT INTO `generated_question` (
  `generated_question_id`,
  `question_numeric_id`,
  `training_session_id`,
  `question_type`,
  `knowledge_point_id`,
  `module_id`,
  `task_id`,
  `difficulty`,
  `title`,
  `stem`,
  `standard_answer`,
  `reference_answer`,
  `explanation`,
  `source_model`,
  `raw_ai_json`
)
VALUES
  ('teacher_scope_gq_a', 990001, 'teacher_scope_session_a', 'single_choice', 101, 1, 1, 'easy', '教师权限测试题A', '只有权限测试教师A应看到这道题。', 'A', 'A', '权限测试种子A', 'seed', JSON_OBJECT('reviewStatus', 'APPROVED', 'qualityScore', 86)),
  ('teacher_scope_gq_b', 990002, 'teacher_scope_session_b', 'single_choice', 101, 1, 1, 'easy', '教师权限测试题B', '只有权限测试教师B应看到这道题。', 'B', 'B', '权限测试种子B', 'seed', JSON_OBJECT('reviewStatus', 'REJECTED', 'qualityScore', 72))
ON DUPLICATE KEY UPDATE
  `training_session_id` = VALUES(`training_session_id`),
  `question_type` = VALUES(`question_type`),
  `knowledge_point_id` = VALUES(`knowledge_point_id`),
  `module_id` = VALUES(`module_id`),
  `task_id` = VALUES(`task_id`),
  `difficulty` = VALUES(`difficulty`),
  `title` = VALUES(`title`),
  `stem` = VALUES(`stem`),
  `standard_answer` = VALUES(`standard_answer`),
  `reference_answer` = VALUES(`reference_answer`),
  `explanation` = VALUES(`explanation`),
  `source_model` = VALUES(`source_model`),
  `raw_ai_json` = VALUES(`raw_ai_json`);
