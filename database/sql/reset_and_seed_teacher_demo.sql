-- 教师端演示环境重置与真实课堂种子数据。
-- 用途：清除历史测试学生、画像、训练和教学班数据，再写入一组可追溯的课堂数据。
-- 前置：已执行 database/sql/user-service-local-init.sql、
--       database/sql/experiment-module-service-local-init.sql、
--       database/sql/init_seclab_profile.sql。
-- 注意：此脚本会删除全部 STUDENT 账号及其学习数据，只能在演示/开发库手动执行。

SET FOREIGN_KEY_CHECKS = 0;

USE `seclab_profile`;
DELETE FROM `teacher_typical_question`;
DELETE FROM `teacher_class_analysis`;
DELETE FROM `generated_question_attempt`;
DELETE FROM `question_knowledge_point` WHERE `generated_question_id` IS NOT NULL;
DELETE FROM `generated_question`;
DELETE FROM `training_session`;
DELETE FROM `class_profile_student_metric`;
DELETE FROM `class_profile_snapshot`;
DELETE FROM `student_profile_feature_daily`;
DELETE FROM `student_profile_snapshot`;
DELETE FROM `ai_context_injection`;
DELETE FROM `ai_tool_call`;
DELETE FROM `ai_message`;
DELETE FROM `ai_conversation`;
DELETE FROM `error_event`;
DELETE FROM `container_file_event`;
DELETE FROM `container_command_event`;
DELETE FROM `challenge_completion_event`;
DELETE FROM `flag_submission`;
DELETE FROM `lab_session`;
DELETE FROM `question_submission`;
DELETE FROM `learning_event`;

USE `userservice`;
DELETE FROM `teaching_class_import_batch`;
DELETE FROM `teaching_class_course`;
DELETE FROM `teaching_class_student`;
DELETE FROM `teaching_class`;
DELETE FROM `user` WHERE `user_role` = 'STUDENT';

INSERT INTO `class` (`class_name`, `class_detail`, `is_end`)
VALUES ('网络空间安全232班', '网络空间安全专业2023级2班', 0)
ON DUPLICATE KEY UPDATE `class_detail` = VALUES(`class_detail`), `is_end` = 0;

SET @admin_class_id := (
  SELECT `class_id` FROM `class` WHERE `class_name` = '网络空间安全232班' LIMIT 1
);

INSERT INTO `user` (
  `user_student_number`, `user_password`, `user_name`, `user_gender`,
  `user_academy`, `user_email`, `user_tel`, `class_id_class_id`,
  `is_admin`, `user_role`, `is_deleted`
) VALUES (
  'T20260001', 'e10adc3949ba59abbe56e057f20f883e', '李伟', 1,
  '网络空间安全学院', 'liwei@seclab.edu.cn', '13800138000', @admin_class_id,
  b'0', 'TEACHER', 0
) ON DUPLICATE KEY UPDATE
  `user_name` = VALUES(`user_name`), `user_academy` = VALUES(`user_academy`),
  `user_email` = VALUES(`user_email`), `user_role` = 'TEACHER', `is_deleted` = 0;

SET @teacher_id := (
  SELECT `user_id` FROM `user` WHERE `user_student_number` = 'T20260001' LIMIT 1
);

INSERT INTO `user` (
  `user_student_number`, `user_password`, `user_name`, `user_gender`,
  `user_academy`, `user_email`, `class_id_class_id`, `is_admin`, `user_role`, `is_deleted`
) VALUES
  ('202321040501', 'e10adc3949ba59abbe56e057f20f883e', '陈宇航', 1, '网络空间安全学院', '202321040501@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040502', 'e10adc3949ba59abbe56e057f20f883e', '周雨桐', 0, '网络空间安全学院', '202321040502@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040503', 'e10adc3949ba59abbe56e057f20f883e', '王子睿', 1, '网络空间安全学院', '202321040503@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040504', 'e10adc3949ba59abbe56e057f20f883e', '林佳宁', 0, '网络空间安全学院', '202321040504@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040505', 'e10adc3949ba59abbe56e057f20f883e', '张博文', 1, '网络空间安全学院', '202321040505@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040506', 'e10adc3949ba59abbe56e057f20f883e', '吴思琪', 0, '网络空间安全学院', '202321040506@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040507', 'e10adc3949ba59abbe56e057f20f883e', '郑凯', 1, '网络空间安全学院', '202321040507@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040508', 'e10adc3949ba59abbe56e057f20f883e', '赵欣怡', 0, '网络空间安全学院', '202321040508@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0);

INSERT INTO `teaching_class` (
  `class_name`, `academic_year`, `semester`, `teacher_id`,
  `start_date`, `end_date`, `status`
) VALUES (
  '网络安全工程实践-01班', '2026-2027', 1, @teacher_id,
  '2026-09-07', '2027-01-08', 'ACTIVE'
);

SET @teaching_class_id := LAST_INSERT_ID();

INSERT INTO `teaching_class_student` (`teaching_class_id`, `student_id`, `source`)
SELECT @teaching_class_id, `user_id`, 'EXCEL_IMPORT'
FROM `user`
WHERE `user_student_number` BETWEEN '202321040501' AND '202321040508';

INSERT INTO `teaching_class_course` (
  `teaching_class_id`, `course_id`, `teaching_order`, `planned_start_date`, `planned_end_date`
) VALUES
  (@teaching_class_id, 1, 1, '2026-09-07', '2026-09-18'),
  (@teaching_class_id, 2, 2, '2026-09-21', '2026-10-09'),
  (@teaching_class_id, 3, 3, '2026-10-12', '2026-10-23'),
  (@teaching_class_id, 4, 4, '2026-10-26', '2026-11-06'),
  (@teaching_class_id, 5, 5, '2026-11-09', '2026-11-20'),
  (@teaching_class_id, 6, 6, '2026-11-23', '2026-12-04'),
  (@teaching_class_id, 7, 7, '2026-12-07', '2026-12-18'),
  (@teaching_class_id, 8, 8, '2026-12-21', '2027-01-08');

SET @s1 := (SELECT `user_id` FROM `user` WHERE `user_student_number` = '202321040501');
SET @s2 := (SELECT `user_id` FROM `user` WHERE `user_student_number` = '202321040502');
SET @s3 := (SELECT `user_id` FROM `user` WHERE `user_student_number` = '202321040503');
SET @s4 := (SELECT `user_id` FROM `user` WHERE `user_student_number` = '202321040504');
SET @s5 := (SELECT `user_id` FROM `user` WHERE `user_student_number` = '202321040505');
SET @s6 := (SELECT `user_id` FROM `user` WHERE `user_student_number` = '202321040506');
SET @s7 := (SELECT `user_id` FROM `user` WHERE `user_student_number` = '202321040507');
SET @s8 := (SELECT `user_id` FROM `user` WHERE `user_student_number` = '202321040508');

USE `seclab_profile`;

INSERT INTO `training_session` (
  `training_session_id`, `user_id`, `class_id`, `course_id`,
  `source_type`, `diagnose_result_json`, `training_context_json`, `created_at`
) VALUES
  ('train-2026-0901-a1', @s1, @teaching_class_id, 2, 'personalized_training', JSON_OBJECT('weakKnowledgePoints', JSON_ARRAY(101)), JSON_OBJECT('source', 'student_profile'), NOW(6) - INTERVAL 6 DAY),
  ('train-2026-0901-a2', @s2, @teaching_class_id, 2, 'personalized_training', JSON_OBJECT('weakKnowledgePoints', JSON_ARRAY(101)), JSON_OBJECT('source', 'student_profile'), NOW(6) - INTERVAL 5 DAY),
  ('train-2026-0901-a3', @s3, @teaching_class_id, 2, 'personalized_training', JSON_OBJECT('weakKnowledgePoints', JSON_ARRAY(102)), JSON_OBJECT('source', 'student_profile'), NOW(6) - INTERVAL 4 DAY),
  ('train-2026-0901-a4', @s4, @teaching_class_id, 3, 'personalized_training', JSON_OBJECT('weakKnowledgePoints', JSON_ARRAY(201)), JSON_OBJECT('source', 'student_profile'), NOW(6) - INTERVAL 3 DAY),
  ('train-2026-0901-a5', @s5, @teaching_class_id, 3, 'personalized_training', JSON_OBJECT('weakKnowledgePoints', JSON_ARRAY(201)), JSON_OBJECT('source', 'student_profile'), NOW(6) - INTERVAL 2 DAY),
  ('train-2026-0901-a6', @s6, @teaching_class_id, 4, 'personalized_training', JSON_OBJECT('weakKnowledgePoints', JSON_ARRAY(501)), JSON_OBJECT('source', 'student_profile'), NOW(6) - INTERVAL 1 DAY),
  ('train-2026-0901-a7', @s7, @teaching_class_id, 7, 'personalized_training', JSON_OBJECT('weakKnowledgePoints', JSON_ARRAY(301)), JSON_OBJECT('source', 'student_profile'), NOW(6) - INTERVAL 12 HOUR),
  ('train-2026-0901-a8', @s8, @teaching_class_id, 2, 'personalized_training', JSON_OBJECT('weakKnowledgePoints', JSON_ARRAY(101)), JSON_OBJECT('source', 'student_profile'), NOW(6) - INTERVAL 2 HOUR);

INSERT INTO `generated_question` (
  `generated_question_id`, `question_numeric_id`, `training_session_id`, `question_type`,
  `knowledge_point_id`, `module_id`, `task_id`, `difficulty`, `title`, `stem`,
  `options_json`, `standard_answer`, `reference_answer`, `explanation`,
  `source_model`, `raw_ai_json`, `created_at`
) VALUES
  ('gq-real-001', 920001, 'train-2026-0901-a1', 'short_answer', 101, 1, 1, 'medium', 'UNION 查询列数判断', '在不知道原查询列数时，如何使用 ORDER BY 确定 UNION SELECT 的列数？', NULL, NULL, '从 ORDER BY 1 开始递增，首次报错的序号减一即为原查询列数。', 'ORDER BY 引用的列序号超过结果列数时数据库会报错，因此可以据此确定边界。', 'dify', JSON_OBJECT('generationReason', '该生在 UNION SELECT 列数匹配步骤中连续两次失败。'), NOW(6) - INTERVAL 6 DAY),
  ('gq-real-002', 920002, 'train-2026-0901-a2', 'single_choice', 101, 1, 1, 'medium', 'UNION 查询回显位置', '已知原查询有 3 列，哪条语句最适合判断页面中的回显位置？', JSON_ARRAY('UNION SELECT 1,2,3', 'UNION SELECT NULL', 'ORDER BY 4', 'SELECT * FROM users'), 'A', 'UNION SELECT 1,2,3', '使用可辨识的常量可以观察哪些列被输出到页面。', 'dify', JSON_OBJECT('generationReason', '该生能确定列数，但未能定位可回显列。'), NOW(6) - INTERVAL 5 DAY),
  ('gq-real-003', 920003, 'train-2026-0901-a3', 'short_answer', 102, 1, 2, 'hard', '时间盲注条件判断', '说明 IF(condition,SLEEP(3),0) 在时间盲注中的判断依据，并写出减少误判的一种方法。', NULL, NULL, '条件成立时响应延迟约 3 秒；可重复请求并比较多次响应时间，设置合理阈值。', '通过条件分支控制延迟，再用多次测量降低网络波动影响。', 'dify', JSON_OBJECT('generationReason', '该生对布尔条件与响应延迟的对应关系理解不稳定。'), NOW(6) - INTERVAL 4 DAY),
  ('gq-real-004', 920004, 'train-2026-0901-a4', 'short_answer', 201, 2, 1, 'medium', 'HTML 属性上下文编码', '用户输入被放入 HTML 属性值时，为什么仅替换尖括号仍不能完整防止 XSS？', NULL, NULL, '攻击者仍可能使用引号结束属性值并注入新属性或事件处理器，应进行属性上下文编码并限制危险协议。', '不同输出上下文需要不同编码策略，属性边界字符同样关键。', 'dify', JSON_OBJECT('generationReason', '该生在属性上下文中只考虑了标签注入。'), NOW(6) - INTERVAL 3 DAY),
  ('gq-real-005', 920005, 'train-2026-0901-a5', 'single_choice', 201, 2, 1, 'easy', 'XSS 输出编码位置', '防止存储型 XSS 时，最关键的输出编码应在何处执行？', JSON_ARRAY('数据写入数据库前统一删除符号', '根据最终输出上下文在渲染时编码', '只在前端提交时编码', '只设置 HttpOnly'), 'B', '根据最终输出上下文在渲染时编码', '编码方式由 HTML、属性、JavaScript 等最终输出上下文决定。', 'dify', JSON_OBJECT('generationReason', '该生把输入过滤和输出编码混为一谈。'), NOW(6) - INTERVAL 2 DAY),
  ('gq-real-006', 920006, 'train-2026-0901-a6', 'short_answer', 501, 3, 1, 'medium', '上传文件校验策略', '仅检查 Content-Type 为什么不足以阻止恶意文件上传？请给出两项后端补充措施。', NULL, NULL, 'Content-Type 可由客户端伪造；后端应校验文件内容特征、重命名文件、隔离存储并禁止执行权限。', '客户端提供的元数据不可信，需要内容校验和安全存储共同控制。', 'dify', JSON_OBJECT('generationReason', '该生在上传实验中只检查了请求头。'), NOW(6) - INTERVAL 1 DAY),
  ('gq-real-007', 920007, 'train-2026-0901-a7', 'short_answer', 301, 3, 1, 'medium', 'CSRF 令牌绑定', 'CSRF 令牌为什么需要与用户会话绑定，并在服务端验证？', NULL, NULL, '绑定会话可确保令牌属于当前用户且难以被攻击站点获取；服务端必须比较请求令牌与会话中的预期值。', '仅在页面放置随机值但不做服务端校验不能形成防护。', 'dify', JSON_OBJECT('generationReason', '该生能描述攻击流程，但遗漏了令牌的会话绑定。'), NOW(6) - INTERVAL 12 HOUR),
  ('gq-real-008', 920008, 'train-2026-0901-a8', 'short_answer', 101, 1, 1, 'medium', '参数化查询防注入', '参数化查询如何把用户输入与 SQL 结构分离？哪些场景仍需白名单校验？', NULL, NULL, '数据库预先编译 SQL 结构并把输入作为参数值绑定；表名、列名、排序方向等不能参数化的结构位置仍需白名单。', '参数绑定保护值位置，但动态标识符与关键字仍需单独限制。', 'dify', JSON_OBJECT('generationReason', '该生知道使用预编译，但对动态排序字段的处理不清楚。'), NOW(6) - INTERVAL 2 HOUR);

INSERT INTO `generated_question_attempt` (
  `attempt_id`, `training_session_id`, `generated_question_id`, `user_id`,
  `answer_json`, `is_correct`, `score`, `cost_time`, `submitted_at`
) VALUES
  ('attempt-real-001', 'train-2026-0901-a1', 'gq-real-001', @s1, JSON_QUOTE('逐个增加 ORDER BY 后面的数字，报错时就是列数。'), 0, 62, 148, NOW(6) - INTERVAL 5 DAY),
  ('attempt-real-002', 'train-2026-0901-a2', 'gq-real-002', @s2, JSON_QUOTE('A'), 1, 100, 43, NOW(6) - INTERVAL 4 DAY),
  ('attempt-real-003', 'train-2026-0901-a3', 'gq-real-003', @s3, JSON_QUOTE('条件成立就延迟三秒。'), 0, 58, 206, NOW(6) - INTERVAL 3 DAY),
  ('attempt-real-004', 'train-2026-0901-a4', 'gq-real-004', @s4, JSON_QUOTE('还要过滤 script 标签。'), 0, 45, 184, NOW(6) - INTERVAL 2 DAY),
  ('attempt-real-005', 'train-2026-0901-a5', 'gq-real-005', @s5, JSON_QUOTE('B'), 1, 100, 35, NOW(6) - INTERVAL 1 DAY),
  ('attempt-real-006', 'train-2026-0901-a6', 'gq-real-006', @s6, JSON_QUOTE('检查后缀并限制大小。'), 0, 55, 132, NOW(6) - INTERVAL 18 HOUR),
  ('attempt-real-007', 'train-2026-0901-a7', 'gq-real-007', @s7, JSON_QUOTE('让攻击者猜不到令牌。'), 0, 60, 97, NOW(6) - INTERVAL 8 HOUR);

INSERT INTO `learning_event` (
  `event_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`,
  `event_type`, `event_time`, `payload_json`, `source`
) VALUES
  ('event-real-001', @s1, @teaching_class_id, 2, 1, 1, 'LAB_COMPLETE', NOW(6) - INTERVAL 5 DAY, JSON_OBJECT('summary', '完成 SQL 注入基础实验'), 'student-web'),
  ('event-real-002', @s2, @teaching_class_id, 2, 1, 1, 'CHALLENGE_COMPLETE', NOW(6) - INTERVAL 4 DAY, JSON_OBJECT('summary', '完成 UNION 注入回显定位'), 'student-web'),
  ('event-real-003', @s3, @teaching_class_id, 2, 1, 2, 'HINT_REQUEST', NOW(6) - INTERVAL 3 DAY, JSON_OBJECT('summary', '请求时间盲注判断提示'), 'student-web'),
  ('event-real-004', @s4, @teaching_class_id, 3, 2, 1, 'AI_INTERACTION', NOW(6) - INTERVAL 2 DAY, JSON_OBJECT('summary', '询问属性上下文编码方式'), 'student-web'),
  ('event-real-005', @s5, @teaching_class_id, 3, 2, 1, 'LAB_COMPLETE', NOW(6) - INTERVAL 1 DAY, JSON_OBJECT('summary', '完成 XSS 输出编码实验'), 'student-web'),
  ('event-real-006', @s6, @teaching_class_id, 4, 3, 1, 'FLAG_SUBMIT_FAILED', NOW(6) - INTERVAL 18 HOUR, JSON_OBJECT('summary', '文件上传实验提交未通过'), 'student-web'),
  ('event-real-007', @s7, @teaching_class_id, 7, 3, 1, 'AI_INTERACTION', NOW(6) - INTERVAL 8 HOUR, JSON_OBJECT('summary', '询问 CSRF 令牌验证位置'), 'student-web'),
  ('event-real-008', @s8, @teaching_class_id, 2, 1, 1, 'LAB_START', NOW(6) - INTERVAL 90 MINUTE, JSON_OBJECT('summary', '进入 SQL 注入防护实验'), 'student-web');

SET FOREIGN_KEY_CHECKS = 1;

SELECT @teacher_id AS teacher_id, @teaching_class_id AS teaching_class_id,
       8 AS seeded_students, 8 AS seeded_generated_questions;
