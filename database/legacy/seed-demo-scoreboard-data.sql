-- Non-destructive demo data for the real scoreboard endpoint.
-- This script only inserts or updates rows marked with the demo scoreboard identifiers below.
-- It does not delete, truncate, reset, or rebuild any discussion/community tables.

CREATE DATABASE IF NOT EXISTS `userservice`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS `seclab_profile`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

INSERT INTO `userservice`.`class` (`class_name`, `class_detail`, `is_end`)
SELECT 'SecLab演示班', '排行榜演示数据班级', 0
WHERE NOT EXISTS (
  SELECT 1 FROM `userservice`.`class` WHERE `class_name` = 'SecLab演示班'
);

SET @demo_class_id := (
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
  `is_deleted`
)
SELECT seed.student_number, '00000000000000000000000000000000', seed.user_name, 0,
       'SecLab演示学院', NULL, NULL, NULL, @demo_class_id, b'0', 0
FROM (
  SELECT 'demo_stu_01' AS student_number, 'SQL注入练习者' AS user_name UNION ALL
  SELECT 'demo_stu_02', 'XSS挑战者' UNION ALL
  SELECT 'demo_stu_03', '文件上传训练者' UNION ALL
  SELECT 'demo_stu_04', 'CTF新星' UNION ALL
  SELECT 'demo_stu_05', '代码审计学员' UNION ALL
  SELECT 'demo_stu_06', '应急响应学员'
) seed
WHERE NOT EXISTS (
  SELECT 1
  FROM `userservice`.`user` existing_user
  WHERE existing_user.`user_student_number` = seed.student_number
);

SET @demo_user_01 := (SELECT `user_id` FROM `userservice`.`user` WHERE `user_student_number` = 'demo_stu_01' LIMIT 1);
SET @demo_user_02 := (SELECT `user_id` FROM `userservice`.`user` WHERE `user_student_number` = 'demo_stu_02' LIMIT 1);
SET @demo_user_03 := (SELECT `user_id` FROM `userservice`.`user` WHERE `user_student_number` = 'demo_stu_03' LIMIT 1);
SET @demo_user_04 := (SELECT `user_id` FROM `userservice`.`user` WHERE `user_student_number` = 'demo_stu_04' LIMIT 1);
SET @demo_user_05 := (SELECT `user_id` FROM `userservice`.`user` WHERE `user_student_number` = 'demo_stu_05' LIMIT 1);
SET @demo_user_06 := (SELECT `user_id` FROM `userservice`.`user` WHERE `user_student_number` = 'demo_stu_06' LIMIT 1);

INSERT INTO `seclab_profile`.`training_session` (
  `training_session_id`,
  `user_id`,
  `class_id`,
  `course_id`,
  `profile_snapshot_id`,
  `source_type`,
  `diagnose_result_json`,
  `training_context_json`,
  `created_at`
)
VALUES
  ('demo-scoreboard-session-01', @demo_user_01, @demo_class_id, NULL, 'demo-scoreboard-profile-01', 'scoreboard_demo_seed', JSON_OBJECT('source', 'demo-scoreboard-seed'), JSON_OBJECT('demo', true), DATE_SUB(NOW(6), INTERVAL 6 DAY)),
  ('demo-scoreboard-session-02', @demo_user_02, @demo_class_id, NULL, 'demo-scoreboard-profile-02', 'scoreboard_demo_seed', JSON_OBJECT('source', 'demo-scoreboard-seed'), JSON_OBJECT('demo', true), DATE_SUB(NOW(6), INTERVAL 5 DAY)),
  ('demo-scoreboard-session-03', @demo_user_03, @demo_class_id, NULL, 'demo-scoreboard-profile-03', 'scoreboard_demo_seed', JSON_OBJECT('source', 'demo-scoreboard-seed'), JSON_OBJECT('demo', true), DATE_SUB(NOW(6), INTERVAL 4 DAY)),
  ('demo-scoreboard-session-04', @demo_user_04, @demo_class_id, NULL, 'demo-scoreboard-profile-04', 'scoreboard_demo_seed', JSON_OBJECT('source', 'demo-scoreboard-seed'), JSON_OBJECT('demo', true), DATE_SUB(NOW(6), INTERVAL 3 DAY)),
  ('demo-scoreboard-session-05', @demo_user_05, @demo_class_id, NULL, 'demo-scoreboard-profile-05', 'scoreboard_demo_seed', JSON_OBJECT('source', 'demo-scoreboard-seed'), JSON_OBJECT('demo', true), DATE_SUB(NOW(6), INTERVAL 2 DAY)),
  ('demo-scoreboard-session-06', @demo_user_06, @demo_class_id, NULL, 'demo-scoreboard-profile-06', 'scoreboard_demo_seed', JSON_OBJECT('source', 'demo-scoreboard-seed'), JSON_OBJECT('demo', true), DATE_SUB(NOW(6), INTERVAL 1 DAY))
ON DUPLICATE KEY UPDATE
  `user_id` = VALUES(`user_id`),
  `class_id` = VALUES(`class_id`),
  `profile_snapshot_id` = VALUES(`profile_snapshot_id`),
  `diagnose_result_json` = VALUES(`diagnose_result_json`),
  `training_context_json` = VALUES(`training_context_json`);

INSERT INTO `seclab_profile`.`generated_question` (
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
  `options_json`,
  `standard_answer`,
  `reference_answer`,
  `explanation`,
  `scoring_rubric_json`,
  `source_model`,
  `raw_ai_json`,
  `created_at`
)
VALUES
  ('demo-scoreboard-question-01', 900001, 'demo-scoreboard-session-01', 'short_answer', 101, 1, 1, 'medium', 'SQL注入判断演示题', '用于排行榜演示的训练题。', NULL, '演示答案', '演示答案', '演示解析', JSON_OBJECT('demo', true), 'demo-seed', JSON_OBJECT('demo', true), DATE_SUB(NOW(6), INTERVAL 6 DAY)),
  ('demo-scoreboard-question-02', 900002, 'demo-scoreboard-session-02', 'short_answer', 201, 2, 1, 'medium', 'XSS上下文判断演示题', '用于排行榜演示的训练题。', NULL, '演示答案', '演示答案', '演示解析', JSON_OBJECT('demo', true), 'demo-seed', JSON_OBJECT('demo', true), DATE_SUB(NOW(6), INTERVAL 5 DAY)),
  ('demo-scoreboard-question-03', 900003, 'demo-scoreboard-session-03', 'short_answer', 501, 5, 1, 'medium', '文件上传绕过演示题', '用于排行榜演示的训练题。', NULL, '演示答案', '演示答案', '演示解析', JSON_OBJECT('demo', true), 'demo-seed', JSON_OBJECT('demo', true), DATE_SUB(NOW(6), INTERVAL 4 DAY)),
  ('demo-scoreboard-question-04', 900004, 'demo-scoreboard-session-04', 'short_answer', 401, 4, 1, 'medium', '命令注入判断演示题', '用于排行榜演示的训练题。', NULL, '演示答案', '演示答案', '演示解析', JSON_OBJECT('demo', true), 'demo-seed', JSON_OBJECT('demo', true), DATE_SUB(NOW(6), INTERVAL 3 DAY)),
  ('demo-scoreboard-question-05', 900005, 'demo-scoreboard-session-05', 'short_answer', 102, 1, 2, 'hard', '盲注排查演示题', '用于排行榜演示的训练题。', NULL, '演示答案', '演示答案', '演示解析', JSON_OBJECT('demo', true), 'demo-seed', JSON_OBJECT('demo', true), DATE_SUB(NOW(6), INTERVAL 2 DAY)),
  ('demo-scoreboard-question-06', 900006, 'demo-scoreboard-session-06', 'short_answer', 301, 3, 1, 'medium', 'CSRF令牌判断演示题', '用于排行榜演示的训练题。', NULL, '演示答案', '演示答案', '演示解析', JSON_OBJECT('demo', true), 'demo-seed', JSON_OBJECT('demo', true), DATE_SUB(NOW(6), INTERVAL 1 DAY))
ON DUPLICATE KEY UPDATE
  `training_session_id` = VALUES(`training_session_id`),
  `knowledge_point_id` = VALUES(`knowledge_point_id`),
  `module_id` = VALUES(`module_id`),
  `task_id` = VALUES(`task_id`),
  `raw_ai_json` = VALUES(`raw_ai_json`);

INSERT INTO `seclab_profile`.`generated_question_attempt` (
  `attempt_id`,
  `training_session_id`,
  `generated_question_id`,
  `user_id`,
  `answer_json`,
  `is_correct`,
  `score`,
  `cost_time`,
  `submission_id`,
  `profile_rebuild_snapshot_id`,
  `submitted_at`
)
VALUES
  ('demo-scoreboard-attempt-01-01', 'demo-scoreboard-session-01', 'demo-scoreboard-question-01', @demo_user_01, JSON_OBJECT('demo', true), 1, 96.00, 88, NULL, 'demo-scoreboard-profile-01', DATE_SUB(NOW(6), INTERVAL 12 HOUR)),
  ('demo-scoreboard-attempt-01-02', 'demo-scoreboard-session-01', 'demo-scoreboard-question-01', @demo_user_01, JSON_OBJECT('demo', true), 1, 93.00, 92, NULL, 'demo-scoreboard-profile-01', DATE_SUB(NOW(6), INTERVAL 10 HOUR)),
  ('demo-scoreboard-attempt-02-01', 'demo-scoreboard-session-02', 'demo-scoreboard-question-02', @demo_user_02, JSON_OBJECT('demo', true), 1, 91.00, 110, NULL, 'demo-scoreboard-profile-02', DATE_SUB(NOW(6), INTERVAL 16 HOUR)),
  ('demo-scoreboard-attempt-02-02', 'demo-scoreboard-session-02', 'demo-scoreboard-question-02', @demo_user_02, JSON_OBJECT('demo', true), 1, 88.00, 120, NULL, 'demo-scoreboard-profile-02', DATE_SUB(NOW(6), INTERVAL 14 HOUR)),
  ('demo-scoreboard-attempt-03-01', 'demo-scoreboard-session-03', 'demo-scoreboard-question-03', @demo_user_03, JSON_OBJECT('demo', true), 1, 84.00, 130, NULL, 'demo-scoreboard-profile-03', DATE_SUB(NOW(6), INTERVAL 20 HOUR)),
  ('demo-scoreboard-attempt-03-02', 'demo-scoreboard-session-03', 'demo-scoreboard-question-03', @demo_user_03, JSON_OBJECT('demo', true), 0, 72.00, 150, NULL, 'demo-scoreboard-profile-03', DATE_SUB(NOW(6), INTERVAL 18 HOUR)),
  ('demo-scoreboard-attempt-04-01', 'demo-scoreboard-session-04', 'demo-scoreboard-question-04', @demo_user_04, JSON_OBJECT('demo', true), 1, 86.00, 100, NULL, 'demo-scoreboard-profile-04', DATE_SUB(NOW(6), INTERVAL 26 HOUR)),
  ('demo-scoreboard-attempt-05-01', 'demo-scoreboard-session-05', 'demo-scoreboard-question-05', @demo_user_05, JSON_OBJECT('demo', true), 0, 66.00, 170, NULL, 'demo-scoreboard-profile-05', DATE_SUB(NOW(6), INTERVAL 30 HOUR)),
  ('demo-scoreboard-attempt-06-01', 'demo-scoreboard-session-06', 'demo-scoreboard-question-06', @demo_user_06, JSON_OBJECT('demo', true), 1, 80.00, 118, NULL, 'demo-scoreboard-profile-06', DATE_SUB(NOW(6), INTERVAL 36 HOUR))
ON DUPLICATE KEY UPDATE
  `user_id` = VALUES(`user_id`),
  `answer_json` = VALUES(`answer_json`),
  `is_correct` = VALUES(`is_correct`),
  `score` = VALUES(`score`),
  `profile_rebuild_snapshot_id` = VALUES(`profile_rebuild_snapshot_id`),
  `submitted_at` = VALUES(`submitted_at`);

INSERT INTO `seclab_profile`.`learning_event` (
  `event_id`,
  `user_id`,
  `class_id`,
  `course_id`,
  `module_id`,
  `task_id`,
  `question_id`,
  `lab_session_id`,
  `event_type`,
  `event_time`,
  `payload_json`,
  `source`,
  `request_id`
)
VALUES
  ('demo-scoreboard-event-01', @demo_user_01, @demo_class_id, NULL, 1, 1, 900001, NULL, 'TRAINING_GENERATED_QUESTION_SUBMIT', DATE_SUB(NOW(6), INTERVAL 12 HOUR), JSON_OBJECT('demo_seed', 'scoreboard'), 'scoreboard_demo_seed', 'demo-scoreboard-event-01'),
  ('demo-scoreboard-event-02', @demo_user_02, @demo_class_id, NULL, 2, 1, 900002, NULL, 'TRAINING_GENERATED_QUESTION_SUBMIT', DATE_SUB(NOW(6), INTERVAL 16 HOUR), JSON_OBJECT('demo_seed', 'scoreboard'), 'scoreboard_demo_seed', 'demo-scoreboard-event-02'),
  ('demo-scoreboard-event-03', @demo_user_03, @demo_class_id, NULL, 5, 1, 900003, NULL, 'TRAINING_GENERATED_QUESTION_SUBMIT', DATE_SUB(NOW(6), INTERVAL 20 HOUR), JSON_OBJECT('demo_seed', 'scoreboard'), 'scoreboard_demo_seed', 'demo-scoreboard-event-03'),
  ('demo-scoreboard-event-04', @demo_user_04, @demo_class_id, NULL, 4, 1, 900004, NULL, 'TRAINING_GENERATED_QUESTION_SUBMIT', DATE_SUB(NOW(6), INTERVAL 26 HOUR), JSON_OBJECT('demo_seed', 'scoreboard'), 'scoreboard_demo_seed', 'demo-scoreboard-event-04'),
  ('demo-scoreboard-event-05', @demo_user_05, @demo_class_id, NULL, 1, 2, 900005, NULL, 'TRAINING_GENERATED_QUESTION_SUBMIT', DATE_SUB(NOW(6), INTERVAL 30 HOUR), JSON_OBJECT('demo_seed', 'scoreboard'), 'scoreboard_demo_seed', 'demo-scoreboard-event-05'),
  ('demo-scoreboard-event-06', @demo_user_06, @demo_class_id, NULL, 3, 1, 900006, NULL, 'TRAINING_GENERATED_QUESTION_SUBMIT', DATE_SUB(NOW(6), INTERVAL 36 HOUR), JSON_OBJECT('demo_seed', 'scoreboard'), 'scoreboard_demo_seed', 'demo-scoreboard-event-06')
ON DUPLICATE KEY UPDATE
  `user_id` = VALUES(`user_id`),
  `class_id` = VALUES(`class_id`),
  `event_time` = VALUES(`event_time`),
  `payload_json` = VALUES(`payload_json`);

INSERT INTO `seclab_profile`.`student_profile_snapshot` (
  `snapshot_id`,
  `user_id`,
  `class_id`,
  `course_id`,
  `computed_at`,
  `knowledge_mastery_score`,
  `troubleshooting_score`,
  `autonomy_score`,
  `ai_collaboration_score`,
  `engagement_score`,
  `overall_score`,
  `profile_summary_json`,
  `source_range_start`,
  `source_range_end`
)
VALUES
  ('demo-scoreboard-profile-01', @demo_user_01, @demo_class_id, NULL, DATE_SUB(NOW(6), INTERVAL 12 HOUR), 94.00, 88.00, 86.00, 82.00, 91.00, 89.60, JSON_OBJECT('demo_seed', 'scoreboard', 'raw_stats', JSON_OBJECT('training_question_submit_count', 2, 'generated_question_attempt_count', 2, 'event_count', 1), 'evidence', JSON_OBJECT('questionSubmitCount', 2, 'eventCount', 1)), DATE_SUB(NOW(6), INTERVAL 6 DAY), DATE_SUB(NOW(6), INTERVAL 12 HOUR)),
  ('demo-scoreboard-profile-02', @demo_user_02, @demo_class_id, NULL, DATE_SUB(NOW(6), INTERVAL 16 HOUR), 90.00, 84.00, 85.00, 80.00, 88.00, 85.90, JSON_OBJECT('demo_seed', 'scoreboard', 'raw_stats', JSON_OBJECT('training_question_submit_count', 2, 'generated_question_attempt_count', 2, 'event_count', 1), 'evidence', JSON_OBJECT('questionSubmitCount', 2, 'eventCount', 1)), DATE_SUB(NOW(6), INTERVAL 5 DAY), DATE_SUB(NOW(6), INTERVAL 16 HOUR)),
  ('demo-scoreboard-profile-03', @demo_user_03, @demo_class_id, NULL, DATE_SUB(NOW(6), INTERVAL 20 HOUR), 82.00, 83.00, 81.00, 76.00, 86.00, 81.75, JSON_OBJECT('demo_seed', 'scoreboard', 'raw_stats', JSON_OBJECT('training_question_submit_count', 2, 'generated_question_attempt_count', 2, 'event_count', 1), 'evidence', JSON_OBJECT('questionSubmitCount', 2, 'eventCount', 1)), DATE_SUB(NOW(6), INTERVAL 4 DAY), DATE_SUB(NOW(6), INTERVAL 20 HOUR)),
  ('demo-scoreboard-profile-04', @demo_user_04, @demo_class_id, NULL, DATE_SUB(NOW(6), INTERVAL 26 HOUR), 80.00, 86.00, 78.00, 79.00, 82.00, 81.00, JSON_OBJECT('demo_seed', 'scoreboard', 'raw_stats', JSON_OBJECT('training_question_submit_count', 1, 'generated_question_attempt_count', 1, 'event_count', 1), 'evidence', JSON_OBJECT('questionSubmitCount', 1, 'eventCount', 1)), DATE_SUB(NOW(6), INTERVAL 3 DAY), DATE_SUB(NOW(6), INTERVAL 26 HOUR)),
  ('demo-scoreboard-profile-05', @demo_user_05, @demo_class_id, NULL, DATE_SUB(NOW(6), INTERVAL 30 HOUR), 76.00, 79.00, 74.00, 72.00, 80.00, 76.35, JSON_OBJECT('demo_seed', 'scoreboard', 'raw_stats', JSON_OBJECT('training_question_submit_count', 1, 'generated_question_attempt_count', 1, 'event_count', 1), 'evidence', JSON_OBJECT('questionSubmitCount', 1, 'eventCount', 1)), DATE_SUB(NOW(6), INTERVAL 2 DAY), DATE_SUB(NOW(6), INTERVAL 30 HOUR)),
  ('demo-scoreboard-profile-06', @demo_user_06, @demo_class_id, NULL, DATE_SUB(NOW(6), INTERVAL 36 HOUR), 78.00, 74.00, 72.00, 76.00, 79.00, 75.80, JSON_OBJECT('demo_seed', 'scoreboard', 'raw_stats', JSON_OBJECT('training_question_submit_count', 1, 'generated_question_attempt_count', 1, 'event_count', 1), 'evidence', JSON_OBJECT('questionSubmitCount', 1, 'eventCount', 1)), DATE_SUB(NOW(6), INTERVAL 1 DAY), DATE_SUB(NOW(6), INTERVAL 36 HOUR))
ON DUPLICATE KEY UPDATE
  `user_id` = VALUES(`user_id`),
  `class_id` = VALUES(`class_id`),
  `computed_at` = VALUES(`computed_at`),
  `knowledge_mastery_score` = VALUES(`knowledge_mastery_score`),
  `troubleshooting_score` = VALUES(`troubleshooting_score`),
  `autonomy_score` = VALUES(`autonomy_score`),
  `ai_collaboration_score` = VALUES(`ai_collaboration_score`),
  `engagement_score` = VALUES(`engagement_score`),
  `overall_score` = VALUES(`overall_score`),
  `profile_summary_json` = VALUES(`profile_summary_json`),
  `source_range_start` = VALUES(`source_range_start`),
  `source_range_end` = VALUES(`source_range_end`);
