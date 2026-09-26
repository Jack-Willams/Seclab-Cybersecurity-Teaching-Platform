-- 教师端展示数据：网络安全232班（教学班 ID 1）
-- 目标：32 名学生、40 道生成题、17 条错答、一份可直接展示的班级分析。
-- 只维护 showcase-20260715-* 前缀数据，可重复执行，不删除其他历史数据。

START TRANSACTION;

SET @teaching_class_id := 1;
SET @teacher_id := 1;

-- 行政班跟着教学班走：原来这里写死 3，而 class 3 在 init 脚本里叫「网络安全233班」，
-- 教学班 1 叫「网络安全232班」，两边对不上，排行榜/管理后台就会多出一个不存在的班。
SET @teaching_class_name := (
  SELECT `class_name` FROM `userservice`.`teaching_class`
  WHERE `teaching_class_id` = @teaching_class_id
);

INSERT INTO `userservice`.`class` (`class_name`, `class_detail`, `is_end`)
SELECT @teaching_class_name, '教师端展示数据行政班', 0
WHERE @teaching_class_name IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM `userservice`.`class` WHERE `class_name` = @teaching_class_name
  );

SET @admin_class_id := (
  SELECT `class_id` FROM `userservice`.`class`
  WHERE `class_name` = @teaching_class_name
  ORDER BY `class_id` LIMIT 1
);

DELETE FROM `seclab_profile`.`teacher_typical_question`
WHERE `generated_question_id` LIKE 'showcase-20260715-%';

DELETE FROM `seclab_profile`.`question_knowledge_point`
WHERE `generated_question_id` LIKE 'showcase-20260715-%';

DELETE FROM `seclab_profile`.`generated_question_attempt`
WHERE `attempt_id` LIKE 'showcase-20260715-%';

DELETE FROM `seclab_profile`.`generated_question`
WHERE `generated_question_id` LIKE 'showcase-20260715-%';

DELETE FROM `seclab_profile`.`learning_event`
WHERE `event_id` LIKE 'showcase-20260715-%';

DELETE FROM `seclab_profile`.`training_session`
WHERE `training_session_id` LIKE 'showcase-20260715-%';

DELETE tsa
FROM `seclab_profile`.`teacher_student_analysis` tsa
INNER JOIN `userservice`.`user` u ON u.`user_id` = tsa.`student_id`
WHERE tsa.`teaching_class_id` = @teaching_class_id
  AND u.`user_student_number` BETWEEN '202321040501' AND '202321040532';

DELETE tcs
FROM `userservice`.`teaching_class_student` tcs
INNER JOIN `userservice`.`user` u ON u.`user_id` = tcs.`student_id`
WHERE tcs.`teaching_class_id` = @teaching_class_id
  AND u.`user_student_number` BETWEEN '202321040501' AND '202321040532';

DELETE FROM `userservice`.`user`
WHERE `user_student_number` BETWEEN '202321040501' AND '202321040532';

INSERT INTO `userservice`.`user` (
  `user_student_number`, `user_password`, `user_name`, `user_gender`,
  `user_academy`, `user_email`, `class_id_class_id`,
  `is_admin`, `user_role`, `is_deleted`
) VALUES
  ('202321040501', 'e10adc3949ba59abbe56e057f20f883e', '陈宇航', 1, '网络空间安全学院', '202321040501@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040502', 'e10adc3949ba59abbe56e057f20f883e', '周雨桐', 0, '网络空间安全学院', '202321040502@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040503', 'e10adc3949ba59abbe56e057f20f883e', '王子睿', 1, '网络空间安全学院', '202321040503@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040504', 'e10adc3949ba59abbe56e057f20f883e', '林佳宁', 0, '网络空间安全学院', '202321040504@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040505', 'e10adc3949ba59abbe56e057f20f883e', '张博文', 1, '网络空间安全学院', '202321040505@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040506', 'e10adc3949ba59abbe56e057f20f883e', '吴思琪', 0, '网络空间安全学院', '202321040506@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040507', 'e10adc3949ba59abbe56e057f20f883e', '郑凯', 1, '网络空间安全学院', '202321040507@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040508', 'e10adc3949ba59abbe56e057f20f883e', '赵欣怡', 0, '网络空间安全学院', '202321040508@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040509', 'e10adc3949ba59abbe56e057f20f883e', '刘子涵', 0, '网络空间安全学院', '202321040509@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040510', 'e10adc3949ba59abbe56e057f20f883e', '孙浩然', 1, '网络空间安全学院', '202321040510@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040511', 'e10adc3949ba59abbe56e057f20f883e', '李沐阳', 1, '网络空间安全学院', '202321040511@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040512', 'e10adc3949ba59abbe56e057f20f883e', '黄诗涵', 0, '网络空间安全学院', '202321040512@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040513', 'e10adc3949ba59abbe56e057f20f883e', '徐嘉诚', 1, '网络空间安全学院', '202321040513@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040514', 'e10adc3949ba59abbe56e057f20f883e', '何雨欣', 0, '网络空间安全学院', '202321040514@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040515', 'e10adc3949ba59abbe56e057f20f883e', '高梓轩', 1, '网络空间安全学院', '202321040515@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040516', 'e10adc3949ba59abbe56e057f20f883e', '罗梦琪', 0, '网络空间安全学院', '202321040516@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040517', 'e10adc3949ba59abbe56e057f20f883e', '唐俊杰', 1, '网络空间安全学院', '202321040517@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040518', 'e10adc3949ba59abbe56e057f20f883e', '梁若曦', 0, '网络空间安全学院', '202321040518@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040519', 'e10adc3949ba59abbe56e057f20f883e', '宋承泽', 1, '网络空间安全学院', '202321040519@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040520', 'e10adc3949ba59abbe56e057f20f883e', '马依诺', 0, '网络空间安全学院', '202321040520@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040521', 'e10adc3949ba59abbe56e057f20f883e', '胡俊熙', 1, '网络空间安全学院', '202321040521@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040522', 'e10adc3949ba59abbe56e057f20f883e', '郭语彤', 0, '网络空间安全学院', '202321040522@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040523', 'e10adc3949ba59abbe56e057f20f883e', '袁浩宇', 1, '网络空间安全学院', '202321040523@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040524', 'e10adc3949ba59abbe56e057f20f883e', '邓婉清', 0, '网络空间安全学院', '202321040524@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040525', 'e10adc3949ba59abbe56e057f20f883e', '许泽宇', 1, '网络空间安全学院', '202321040525@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040526', 'e10adc3949ba59abbe56e057f20f883e', '曹心怡', 0, '网络空间安全学院', '202321040526@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040527', 'e10adc3949ba59abbe56e057f20f883e', '彭奕辰', 1, '网络空间安全学院', '202321040527@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040528', 'e10adc3949ba59abbe56e057f20f883e', '曾可欣', 0, '网络空间安全学院', '202321040528@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040529', 'e10adc3949ba59abbe56e057f20f883e', '萧景程', 1, '网络空间安全学院', '202321040529@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040530', 'e10adc3949ba59abbe56e057f20f883e', '程悦然', 0, '网络空间安全学院', '202321040530@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040531', 'e10adc3949ba59abbe56e057f20f883e', '沈嘉乐', 1, '网络空间安全学院', '202321040531@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0),
  ('202321040532', 'e10adc3949ba59abbe56e057f20f883e', '杜若彤', 0, '网络空间安全学院', '202321040532@stu.seclab.edu.cn', @admin_class_id, b'0', 'STUDENT', 0)
ON DUPLICATE KEY UPDATE
  `user_name` = VALUES(`user_name`),
  `user_gender` = VALUES(`user_gender`),
  `user_academy` = VALUES(`user_academy`),
  `user_email` = VALUES(`user_email`),
  `class_id_class_id` = VALUES(`class_id_class_id`),
  `is_admin` = b'0',
  `user_role` = 'STUDENT',
  `is_deleted` = 0;

INSERT INTO `userservice`.`teaching_class_student`
  (`teaching_class_id`, `student_id`, `source`, `joined_at`)
SELECT @teaching_class_id, u.`user_id`, 'EXCEL_IMPORT', NOW(6) - INTERVAL 30 DAY
FROM `userservice`.`user` u
WHERE u.`user_student_number` BETWEEN '202321040501' AND '202321040532'
ON DUPLICATE KEY UPDATE `source` = VALUES(`source`), `joined_at` = VALUES(`joined_at`);

DELETE FROM `userservice`.`teaching_class_course`
WHERE `teaching_class_id` = @teaching_class_id;

INSERT INTO `userservice`.`teaching_class_course`
  (`teaching_class_id`, `course_id`, `teaching_order`, `planned_start_date`, `planned_end_date`, `created_at`, `updated_at`)
VALUES
  (@teaching_class_id, 12, 1, '2026-09-07', '2026-09-18', NOW(6), NOW(6)),
  (@teaching_class_id, 1, 2, '2026-09-21', '2026-10-09', NOW(6), NOW(6)),
  (@teaching_class_id, 2, 3, '2026-10-12', '2026-10-23', NOW(6), NOW(6)),
  (@teaching_class_id, 10, 4, '2026-10-26', '2026-11-06', NOW(6), NOW(6)),
  (@teaching_class_id, 5, 5, '2026-11-09', '2026-11-20', NOW(6), NOW(6)),
  (@teaching_class_id, 6, 6, '2026-11-23', '2026-12-04', NOW(6), NOW(6)),
  (@teaching_class_id, 7, 7, '2026-12-07', '2026-12-18', NOW(6), NOW(6)),
  (@teaching_class_id, 8, 8, '2026-12-21', '2027-01-08', NOW(6), NOW(6));

DROP TEMPORARY TABLE IF EXISTS `showcase_students`;
CREATE TEMPORARY TABLE `showcase_students` AS
SELECT
  ROW_NUMBER() OVER (ORDER BY u.`user_student_number`) AS `seq`,
  u.`user_id`,
  u.`user_student_number`
FROM `userservice`.`user` u
WHERE u.`user_student_number` BETWEEN '202321040501' AND '202321040532';

DROP TEMPORARY TABLE IF EXISTS `showcase_question_templates`;
CREATE TEMPORARY TABLE `showcase_question_templates` (
  `seq` INT PRIMARY KEY,
  `knowledge_point_id` BIGINT NOT NULL,
  `module_id` BIGINT NOT NULL,
  `task_id` BIGINT NOT NULL,
  `difficulty` VARCHAR(32) NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `stem` TEXT NOT NULL,
  `reference_answer` TEXT NOT NULL,
  `explanation` TEXT NOT NULL
);

INSERT INTO `showcase_question_templates` VALUES
  (1, 101, 1, 1, 'medium', 'UNION 查询列数判断', '在不知道原查询列数时，如何使用 ORDER BY 确定 UNION SELECT 的列数？', '从 ORDER BY 1 开始递增，首次报错的序号减一即为原查询列数。', 'ORDER BY 引用的列序号超过结果列数时数据库会报错，可据此确定边界。'),
  (2, 102, 1, 2, 'hard', '时间盲注基准验证', '使用 IF(condition,SLEEP(3),0) 判断条件前，为什么要先测量正常请求的响应时间？', '先取得多次正常请求的响应时间基线，再比较条件成立和不成立时的延迟差异。', '建立基准并重复测量可以降低网络波动造成的误判。'),
  (3, 201, 2, 1, 'medium', 'HTML 属性上下文编码', '用户输入进入 HTML 属性值时，为什么只过滤 script 标签仍不能阻止 XSS？', '攻击者可用引号结束属性值并注入事件属性，应按属性上下文编码并限制危险协议。', '不同输出位置需要不同编码策略，属性边界字符同样关键。'),
  (4, 301, 2, 2, 'medium', 'CSRF Token 会话绑定', 'CSRF Token 为什么需要与用户会话绑定并由服务端校验？', '绑定会话可确认令牌属于当前用户，服务端必须比较请求令牌与会话中的预期值。', '只在页面放置随机值但不做服务端校验不能形成防护。'),
  (5, 401, 3, 1, 'medium', '无空格命令执行排查', '当输入中的空格被过滤时，如何从防御角度验证命令是否仍可被拼接执行？', '检查 IFS、变量展开和重定向等替代空格方式，并在服务端使用参数化调用和白名单。', '黑名单过滤容易遗漏等价表达，防御应避免把用户输入交给 shell 解析。'),
  (6, 402, 3, 2, 'hard', '命令黑名单绕过原因', '为什么仅屏蔽分号和常见命令名称不足以防止命令注入？', 'shell 还支持管道、换行、变量展开和编码拼接，应改用无 shell 的安全 API。', '枚举危险字符无法覆盖全部语法，根本措施是隔离数据与命令结构。'),
  (7, 501, 4, 1, 'medium', '上传文件类型校验', '仅检查 Content-Type 为什么不足以阻止恶意文件上传？请给出两项后端措施。', 'Content-Type 可伪造；后端应校验内容特征、重命名文件、隔离存储并禁止执行权限。', '客户端提供的元数据不可信，需要内容校验与安全存储共同控制。'),
  (8, 601, 5, 1, 'medium', '目录遍历路径归一化', '校验用户路径前为什么要先进行 URL 解码和路径归一化？', '编码和重复分隔符可能掩盖 ../，应先解码归一化，再确认最终路径位于允许目录。', '在原始字符串上做黑名单检查会漏掉等价路径表达。');

INSERT INTO `seclab_profile`.`training_session` (
  `training_session_id`, `user_id`, `class_id`, `course_id`, `source_type`,
  `diagnose_result_json`, `training_context_json`, `created_at`
)
SELECT
  CONCAT('showcase-20260715-ts-', s.`user_student_number`),
  s.`user_id`, @teaching_class_id,
  CASE WHEN MOD(s.`seq`, 2) = 0 THEN 2 ELSE 1 END,
  'personalized_training',
  JSON_OBJECT('weakKnowledgePoints', JSON_ARRAY(101 + MOD(s.`seq`, 8))),
  JSON_OBJECT('source', 'student_profile', 'teachingClassId', @teaching_class_id),
  NOW(6) - INTERVAL (33 - s.`seq`) HOUR
FROM `showcase_students` s;

INSERT INTO `seclab_profile`.`generated_question` (
  `generated_question_id`, `question_numeric_id`, `training_session_id`, `question_type`,
  `knowledge_point_id`, `module_id`, `task_id`, `difficulty`, `title`, `stem`,
  `options_json`, `standard_answer`, `reference_answer`, `explanation`,
  `source_model`, `raw_ai_json`, `created_at`
)
SELECT
  CONCAT('showcase-20260715-q-', LPAD(s.`seq`, 2, '0')),
  88000000 + s.`seq`,
  CONCAT('showcase-20260715-ts-', s.`user_student_number`),
  'short_answer', t.`knowledge_point_id`, t.`module_id`, t.`task_id`, t.`difficulty`,
  t.`title`, t.`stem`, NULL, NULL, t.`reference_answer`, t.`explanation`,
  'dify', JSON_OBJECT('generationReason', '根据该生最近一次实验中的具体错误生成'),
  NOW(6) - INTERVAL (41 - s.`seq`) HOUR
FROM `showcase_students` s
INNER JOIN `showcase_question_templates` t ON t.`seq` = MOD(s.`seq` - 1, 8) + 1;

INSERT INTO `seclab_profile`.`generated_question` (
  `generated_question_id`, `question_numeric_id`, `training_session_id`, `question_type`,
  `knowledge_point_id`, `module_id`, `task_id`, `difficulty`, `title`, `stem`,
  `options_json`, `standard_answer`, `reference_answer`, `explanation`,
  `source_model`, `raw_ai_json`, `created_at`
)
SELECT
  CONCAT('showcase-20260715-q-', LPAD(32 + s.`seq`, 2, '0')),
  88000032 + s.`seq`,
  CONCAT('showcase-20260715-ts-', s.`user_student_number`),
  'short_answer', t.`knowledge_point_id`, t.`module_id`, t.`task_id`, t.`difficulty`,
  CONCAT(t.`title`, '（巩固）'), CONCAT('结合一次实验现象说明：', t.`stem`),
  NULL, NULL, t.`reference_answer`, t.`explanation`,
  'dify', JSON_OBJECT('generationReason', '针对首次作答暴露的问题生成巩固题'),
  NOW(6) - INTERVAL (9 - s.`seq`) HOUR
FROM `showcase_students` s
INNER JOIN `showcase_question_templates` t ON t.`seq` = MOD(s.`seq` + 2, 8) + 1
WHERE s.`seq` <= 8;

INSERT INTO `seclab_profile`.`generated_question_attempt` (
  `attempt_id`, `training_session_id`, `generated_question_id`, `user_id`,
  `answer_json`, `is_correct`, `score`, `cost_time`, `submitted_at`
)
SELECT
  REPLACE(gq.`generated_question_id`, '-q-', '-attempt-'),
  gq.`training_session_id`, gq.`generated_question_id`, ts.`user_id`,
  JSON_QUOTE(CASE WHEN gq.`question_numeric_id` <= 88000017
    THEN '只写出了部分步骤，缺少验证依据。'
    ELSE gq.`reference_answer` END),
  CASE WHEN gq.`question_numeric_id` <= 88000017 THEN 0 ELSE 1 END,
  CASE WHEN gq.`question_numeric_id` <= 88000017
    THEN 52 + MOD(gq.`question_numeric_id`, 17)
    ELSE 88 + MOD(gq.`question_numeric_id`, 12) END,
  45 + MOD(gq.`question_numeric_id`, 160),
  gq.`created_at` + INTERVAL 20 MINUTE
FROM `seclab_profile`.`generated_question` gq
INNER JOIN `seclab_profile`.`training_session` ts
  ON ts.`training_session_id` = gq.`training_session_id`
WHERE gq.`generated_question_id` LIKE 'showcase-20260715-q-%';

INSERT INTO `seclab_profile`.`learning_event` (
  `event_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`,
  `event_type`, `event_time`, `payload_json`, `source`
)
SELECT
  CONCAT('showcase-20260715-event-lab-', LPAD(s.`seq`, 2, '0')),
  s.`user_id`, @teaching_class_id, CASE WHEN MOD(s.`seq`, 2) = 0 THEN 2 ELSE 1 END,
  MOD(s.`seq` - 1, 5) + 1, 1, 'LAB_COMPLETE',
  NOW(6) - INTERVAL (34 - s.`seq`) HOUR,
  JSON_OBJECT('summary', '完成本周安全实验并提交实验结果'), 'student-web'
FROM `showcase_students` s;

INSERT INTO `seclab_profile`.`learning_event` (
  `event_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`,
  `event_type`, `event_time`, `payload_json`, `source`
)
SELECT
  CONCAT('showcase-20260715-event-review-', LPAD(s.`seq`, 2, '0')),
  s.`user_id`, @teaching_class_id, CASE WHEN MOD(s.`seq`, 2) = 0 THEN 2 ELSE 1 END,
  MOD(s.`seq` - 1, 5) + 1, 1,
  CASE WHEN MOD(s.`seq`, 3) = 0 THEN 'HINT_REQUEST' ELSE 'AI_INTERACTION' END,
  NOW(6) - INTERVAL (32 - s.`seq`) HOUR,
  JSON_OBJECT('summary', '根据实验错误请求针对性练习并完成复盘'), 'student-web'
FROM `showcase_students` s;

INSERT INTO `seclab_profile`.`teacher_class_analysis` (
  `teaching_class_id`, `requested_by`, `analysis_status`, `data_cutoff_at`,
  `analysis_json`, `source_stats_json`, `last_attempt_at`,
  `last_error_message`, `generated_at`
) VALUES (
  @teaching_class_id, @teacher_id, 'READY', NOW(6),
  JSON_OBJECT(
    'overallComment', '本班对常见 Web 漏洞原理已有基本认识，但在判断输入进入的具体上下文、根据报错调整验证步骤方面仍有明显共性问题。建议下一次课先用两道学生生成题作对比讲解，再安排短时排错练习。',
    'commonProblems', JSON_ARRAY(
      JSON_OBJECT(
        'title', 'XSS 输出上下文判断不稳定',
        'studentCount', 11,
        'evidence', '11 名学生生成了相关题目，近期作答中有 9 次错误，主要混淆 HTML 文本、属性与脚本上下文。',
        'teacherAction', '课堂上并列展示文本、属性和脚本三种输出位置，让学生先标注上下文再选择编码方式。',
        'questionIds', JSON_ARRAY('showcase-20260715-q-03', 'showcase-20260715-q-11')
      ),
      JSON_OBJECT(
        'title', '盲注验证步骤缺少基准对照',
        'studentCount', 8,
        'evidence', '8 名学生的生成题集中在条件构造，常见问题是直接加入延时语句，没有先确认真假分支差异。',
        'teacherAction', '先演示恒真、恒假两个基准请求，再让学生补全延时条件和判断依据。',
        'questionIds', JSON_ARRAY('showcase-20260715-q-02', 'showcase-20260715-q-10')
      )
    )
  ),
  JSON_OBJECT('studentCount', 32, 'generatedQuestionCount', 40, 'incorrectCount', 17),
  NOW(6), NULL, NOW(6)
)
ON DUPLICATE KEY UPDATE
  `requested_by` = VALUES(`requested_by`),
  `analysis_status` = 'READY',
  `data_cutoff_at` = VALUES(`data_cutoff_at`),
  `analysis_json` = VALUES(`analysis_json`),
  `source_stats_json` = VALUES(`source_stats_json`),
  `last_attempt_at` = VALUES(`last_attempt_at`),
  `last_error_message` = NULL,
  `generated_at` = VALUES(`generated_at`);

DROP TEMPORARY TABLE IF EXISTS `showcase_question_templates`;
DROP TEMPORARY TABLE IF EXISTS `showcase_students`;

COMMIT;
