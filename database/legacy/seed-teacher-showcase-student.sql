SET NAMES utf8mb4;
USE `seclab_profile`;

-- 修复早期展示数据中因命令行编码错误写入的问号文本。
UPDATE `container_command_event`
SET `output_digest` = CASE MOD(`user_id`, 3)
  WHEN 0 THEN IF(`exit_code` = 0, '恒真与恒假基准稳定，延时条件验证成功', '未观察到稳定延时，缺少恒真与恒假基准对照')
  WHEN 1 THEN IF(`exit_code` = 0, '已在属性上下文触发事件处理器', 'Payload 被 HTML 编码，脚本未执行')
  ELSE IF(`exit_code` = 0, '上传成功，并验证了扩展名与内容解析差异', '服务端检测到脚本内容并拒绝上传')
END
WHERE `source` = 'showcase-seed';

UPDATE `error_event`
SET
  `error_category` = CASE MOD(`user_id`, 3)
    WHEN 0 THEN 'SQL盲注基准判断'
    WHEN 1 THEN 'XSS输出上下文判断'
    ELSE '文件上传内容校验'
  END,
  `raw_excerpt` = CASE MOD(`user_id`, 3)
    WHEN 0 THEN '直接加入延时条件，未先比较恒真与恒假请求'
    WHEN 1 THEN '未区分 HTML 文本上下文与属性上下文'
    ELSE '只修改 Content-Type，未处理文件内容特征'
  END
WHERE `source` = 'showcase-seed';

UPDATE `learning_event`
SET `payload_json` = CASE `event_type`
  WHEN 'LAB_START' THEN JSON_OBJECT('summary', '开始网络安全实验')
  WHEN 'HINT_REQUEST' THEN JSON_OBJECT('summary', '根据错误信息请求针对性提示', 'hint_level', 1)
  WHEN 'LAB_COMPLETE' THEN JSON_OBJECT('summary', '完成本周安全实验并提交实验结果')
  ELSE `payload_json`
END
WHERE `source` = 'showcase-seed';

UPDATE `teacher_intervention`
SET
  `title` = 'SQL盲注判断专项辅导',
  `description` = '针对恒真/恒假基准、延时阈值和结果复测开展专项训练，一周后比较干预前后的错题率与排障表现.'
WHERE `intervention_id` = 1;

-- 陈宇航（第一名学生）的完整演示数据：7 天持续学习、4 次实验、10 次课程作答、5 次 Flag 验证。
UPDATE `lab_session`
SET `status` = 'completed', `end_time` = COALESCE(`end_time`, '2026-07-14 14:24:00')
WHERE `session_id` = 'showcase-lab-261';

INSERT INTO `lab_session` (
  `session_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`,
  `container_name`, `status`, `start_time`, `end_time`
) VALUES
  ('showcase-demo-lab-261-1', 261, 1, 1, 1, 1, 'showcase-sqli-261-1', 'completed', '2026-07-08 09:00:00', '2026-07-08 09:42:00'),
  ('showcase-demo-lab-261-2', 261, 1, 1, 1, 2, 'showcase-sqli-261-2', 'completed', '2026-07-10 14:00:00', '2026-07-10 14:36:00'),
  ('showcase-demo-lab-261-3', 261, 1, 2, 2, 1, 'showcase-xss-261-1', 'completed', '2026-07-12 10:10:00', '2026-07-12 10:55:00'),
  ('showcase-demo-lab-261-4', 261, 1, 1, 5, 1, 'showcase-upload-261-1', 'completed', '2026-07-15 15:20:00', '2026-07-15 16:08:00')
ON DUPLICATE KEY UPDATE `status` = VALUES(`status`), `end_time` = VALUES(`end_time`);

INSERT INTO `question_submission` (
  `submission_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`,
  `question_id`, `question_uid`, `question_type`, `answer_json`, `standard_answer_json`,
  `is_correct`, `score`, `cost_time`, `question_source`, `knowledge_point_id`, `request_id`, `created_at`
) VALUES
  ('showcase-course-261-01',261,1,1,1,1,91001,'demo-sqli-01','single_choice',JSON_QUOTE('B'),JSON_QUOTE('B'),1,95,46,'course_question',1,'demo-261-01','2026-07-08 09:45:00'),
  ('showcase-course-261-02',261,1,1,1,1,91002,'demo-sqli-02','short_answer',JSON_QUOTE('参数化查询与最小权限'),JSON_QUOTE('参数化查询与最小权限'),1,92,128,'course_question',1,'demo-261-02','2026-07-08 09:52:00'),
  ('showcase-course-261-03',261,1,1,1,2,91003,'demo-blind-01','single_choice',JSON_QUOTE('C'),JSON_QUOTE('C'),1,96,39,'course_question',2,'demo-261-03','2026-07-09 19:20:00'),
  ('showcase-course-261-04',261,1,1,1,2,91004,'demo-blind-02','short_answer',JSON_QUOTE('先建立恒真恒假基准，再判断延时差异'),JSON_QUOTE('先建立恒真恒假基准，再判断延时差异'),1,94,155,'course_question',2,'demo-261-04','2026-07-10 14:40:00'),
  ('showcase-course-261-05',261,1,2,2,1,91005,'demo-xss-01','single_choice',JSON_QUOTE('A'),JSON_QUOTE('A'),1,91,51,'course_question',3,'demo-261-05','2026-07-11 20:05:00'),
  ('showcase-course-261-06',261,1,2,2,1,91006,'demo-xss-02','short_answer',JSON_QUOTE('根据输出上下文选择编码策略'),JSON_QUOTE('根据输出上下文选择编码策略'),1,93,142,'course_question',3,'demo-261-06','2026-07-12 11:02:00'),
  ('showcase-course-261-07',261,1,2,2,2,91007,'demo-csrf-01','single_choice',JSON_QUOTE('D'),JSON_QUOTE('D'),1,90,47,'course_question',4,'demo-261-07','2026-07-13 18:30:00'),
  ('showcase-course-261-08',261,1,1,5,1,91008,'demo-upload-01','short_answer',JSON_QUOTE('扩展名、MIME 与文件内容联合校验'),JSON_QUOTE('扩展名、MIME 与文件内容联合校验'),1,97,169,'course_question',5,'demo-261-08','2026-07-14 21:10:00'),
  ('showcase-course-261-09',261,1,1,5,1,91009,'demo-upload-02','single_choice',JSON_QUOTE('B'),JSON_QUOTE('B'),1,94,43,'course_question',5,'demo-261-09','2026-07-15 16:15:00'),
  ('showcase-course-261-10',261,1,1,5,2,91010,'demo-upload-03','short_answer',JSON_QUOTE('重命名存储并隔离执行权限'),JSON_QUOTE('重命名存储并隔离执行权限'),1,96,134,'course_question',5,'demo-261-10','2026-07-16 19:35:00')
ON DUPLICATE KEY UPDATE `is_correct` = VALUES(`is_correct`), `score` = VALUES(`score`), `answer_json` = VALUES(`answer_json`);

INSERT INTO `flag_submission` (
  `submission_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`,
  `lab_session_id`, `container_name`, `flag_text`, `is_correct`, `score`, `request_id`, `created_at`
) VALUES
  ('showcase-flag-261-01',261,1,1,1,1,'showcase-demo-lab-261-1','showcase-sqli-261-1','flag{baseline_verified}',1,100,'demo-flag-261-01','2026-07-08 09:40:00'),
  ('showcase-flag-261-02',261,1,1,1,2,'showcase-demo-lab-261-2','showcase-sqli-261-2','flag{blind_injection_verified}',1,100,'demo-flag-261-02','2026-07-10 14:34:00'),
  ('showcase-flag-261-03',261,1,2,2,1,'showcase-demo-lab-261-3','showcase-xss-261-1','flag{context_escaped}',1,100,'demo-flag-261-03','2026-07-12 10:52:00'),
  ('showcase-flag-261-04',261,1,1,5,1,'showcase-demo-lab-261-4','showcase-upload-261-1','flag{upload_validated}',1,100,'demo-flag-261-04','2026-07-15 16:05:00'),
  ('showcase-flag-261-05',261,1,1,5,2,'showcase-demo-lab-261-4','showcase-upload-261-1','flag{execution_blocked}',1,100,'demo-flag-261-05','2026-07-16 19:42:00')
ON DUPLICATE KEY UPDATE `is_correct` = VALUES(`is_correct`), `score` = VALUES(`score`);

INSERT INTO `container_command_event` (
  `command_id`, `lab_session_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`,
  `container_name`, `command`, `normalized_command`, `cmd_category`, `cwd`, `exit_code`,
  `duration_ms`, `output_digest`, `source`, `executed_at`
) VALUES
  ('showcase-demo-cmd-261-01','showcase-demo-lab-261-1',261,1,1,1,1,'showcase-sqli-261-1','curl -i http://target/item?id=1','curl -i <url>','sql_injection','/workspace',0,210,'确认参数入口与响应基准','showcase-seed','2026-07-08 09:05:00'),
  ('showcase-demo-cmd-261-02','showcase-demo-lab-261-1',261,1,1,1,1,'showcase-sqli-261-1','sqlmap -u http://target/item?id=1 --batch --dbs','sqlmap -u <url> --batch --dbs','sql_injection','/workspace',0,2500,'识别数据库类型并完成注入验证','showcase-seed','2026-07-08 09:18:00'),
  ('showcase-demo-cmd-261-03','showcase-demo-lab-261-2',261,1,1,1,2,'showcase-sqli-261-2','curl -w %{time_total} http://target/item?id=1','curl -w <metric> <url>','sql_injection','/workspace',0,350,'记录正常请求基准耗时','showcase-seed','2026-07-10 14:05:00'),
  ('showcase-demo-cmd-261-04','showcase-demo-lab-261-2',261,1,1,1,2,'showcase-sqli-261-2','sqlmap -u http://target/item?id=1 --technique=T --time-sec=3','sqlmap -u <url> --technique=t --time-sec=<n>','sql_injection','/workspace',0,3400,'恒真/恒假请求差异稳定，盲注判断成立','showcase-seed','2026-07-10 14:22:00'),
  ('showcase-demo-cmd-261-05','showcase-demo-lab-261-3',261,1,2,2,1,'showcase-xss-261-1','curl http://target/search?q=test','curl <url>?q=<value>','xss','/workspace',0,180,'确认输入回显位置','showcase-seed','2026-07-12 10:15:00'),
  ('showcase-demo-cmd-261-06','showcase-demo-lab-261-3',261,1,2,2,1,'showcase-xss-261-1','curl http://target/profile?name=<img src=x onerror=alert(1)>','curl <url>?name=<payload>','xss','/workspace',0,220,'属性上下文 Payload 验证成功','showcase-seed','2026-07-12 10:32:00'),
  ('showcase-demo-cmd-261-07','showcase-demo-lab-261-4',261,1,1,5,1,'showcase-upload-261-1','file avatar.phtml.jpg','file <path>','file_upload','/workspace',0,90,'识别为包含脚本内容的混合文件','showcase-seed','2026-07-15 15:25:00'),
  ('showcase-demo-cmd-261-08','showcase-demo-lab-261-4',261,1,1,5,1,'showcase-upload-261-1','curl -F file=@avatar.phtml.jpg http://target/upload','curl -f file=@<file> <url>','file_upload','/workspace',1,480,'服务端内容校验拦截上传','showcase-seed','2026-07-15 15:34:00'),
  ('showcase-demo-cmd-261-09','showcase-demo-lab-261-4',261,1,1,5,1,'showcase-upload-261-1','curl -F file=@avatar.jpg http://target/upload','curl -f file=@<image> <url>','file_upload','/workspace',0,430,'合法图片上传成功','showcase-seed','2026-07-15 15:46:00'),
  ('showcase-demo-cmd-261-10','showcase-demo-lab-261-4',261,1,1,5,2,'showcase-upload-261-1','curl -I http://target/uploads/avatar.jpg','curl -i <uploaded-url>','file_upload','/workspace',0,160,'上传目录禁止脚本执行，响应头符合预期','showcase-seed','2026-07-15 15:58:00'),
  ('showcase-demo-cmd-261-11','showcase-demo-lab-261-2',261,1,1,1,2,'showcase-sqli-261-2','python verify_delay.py --samples 5','python <script> --samples <n>','sql_injection','/workspace',0,5100,'连续 5 次采样均通过阈值验证','showcase-seed','2026-07-16 19:05:00'),
  ('showcase-demo-cmd-261-12','showcase-demo-lab-261-2',261,1,1,1,2,'showcase-sqli-261-2','pytest -q tests/test_blind_sqli.py','pytest -q <test>','verification','/workspace',0,1900,'专项复测 6 项全部通过','showcase-seed','2026-07-16 19:18:00')
ON DUPLICATE KEY UPDATE `output_digest` = VALUES(`output_digest`), `exit_code` = VALUES(`exit_code`);

INSERT INTO `container_file_event` (
  `file_event_id`, `lab_session_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`,
  `container_name`, `file_path`, `file_ext`, `action`, `size_before`, `size_after`, `sha256`,
  `is_key_file`, `source`, `request_id`, `changed_at`
) VALUES
  ('showcase-file-261-01','showcase-demo-lab-261-2',261,1,1,1,2,'showcase-sqli-261-2','/workspace/verify_delay.py','py','CREATE',0,860,NULL,1,'showcase-seed','demo-file-261-01','2026-07-10 14:15:00'),
  ('showcase-file-261-02','showcase-demo-lab-261-2',261,1,1,1,2,'showcase-sqli-261-2','/workspace/baseline.csv','csv','CREATE',0,420,NULL,0,'showcase-seed','demo-file-261-02','2026-07-10 14:28:00'),
  ('showcase-file-261-03','showcase-demo-lab-261-3',261,1,2,2,1,'showcase-xss-261-1','/workspace/context-notes.md','md','CREATE',0,680,NULL,0,'showcase-seed','demo-file-261-03','2026-07-12 10:40:00'),
  ('showcase-file-261-04','showcase-demo-lab-261-4',261,1,1,5,1,'showcase-upload-261-1','/workspace/upload-checklist.md','md','CREATE',0,920,NULL,1,'showcase-seed','demo-file-261-04','2026-07-15 15:50:00'),
  ('showcase-file-261-05','showcase-demo-lab-261-2',261,1,1,1,2,'showcase-sqli-261-2','/workspace/test_blind_sqli.py','py','CREATE',0,740,NULL,1,'showcase-seed','demo-file-261-05','2026-07-16 19:12:00')
ON DUPLICATE KEY UPDATE `size_after` = VALUES(`size_after`), `changed_at` = VALUES(`changed_at`);

INSERT INTO `ai_conversation` (
  `conversation_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`, `lab_session_id`,
  `status`, `source`, `start_time`, `last_message_at`
) VALUES ('showcase-ai-conv-261',261,1,1,1,2,'showcase-demo-lab-261-2','active','showcase-seed','2026-07-10 14:08:00','2026-07-10 14:20:00')
ON DUPLICATE KEY UPDATE `last_message_at` = VALUES(`last_message_at`);

INSERT INTO `ai_message` (
  `message_id`, `conversation_id`, `role`, `content`, `content_length`, `event_name`,
  `hint_level`, `contains_context`, `contains_error_excerpt`, `raw_payload_json`, `created_at`
) VALUES
  ('showcase-ai-msg-261-01','showcase-ai-conv-261','user','恒真请求约 0.12 秒，加入延时条件后仍是 0.15 秒。我已经重复 3 次，应该怎样建立可靠基准？',49,'message','guided',1,1,JSON_OBJECT('purpose','提供错误信息并请求排障思路'),'2026-07-10 14:08:00'),
  ('showcase-ai-msg-261-02','showcase-ai-conv-261','assistant','先分别构造恒真和恒假请求，各采样 5 次；确认正常抖动范围后，再把延时阈值设置为基准上界的两倍以上。',52,'message','guided',1,0,JSON_OBJECT('purpose','提供验证步骤而非直接答案'),'2026-07-10 14:10:00'),
  ('showcase-ai-msg-261-03','showcase-ai-conv-261','user','按建议采样后，恒真均值 0.13 秒、恒假均值 0.12 秒、延时请求均值 3.16 秒；我准备再写脚本复测。',57,'message','guided',1,0,JSON_OBJECT('purpose','反馈验证结果并继续行动'),'2026-07-10 14:20:00')
ON DUPLICATE KEY UPDATE `content` = VALUES(`content`), `contains_context` = VALUES(`contains_context`);

INSERT INTO `ai_context_injection` (`conversation_id`, `message_id`, `context_type`, `context_summary`, `context_size`, `raw_context_json`, `created_at`)
SELECT 'showcase-ai-conv-261','showcase-ai-msg-261-01','error_context','包含请求耗时、重复次数和失败现象',128,JSON_OBJECT('baseline','0.12s','delayed','0.15s'),'2026-07-10 14:08:00'
WHERE NOT EXISTS (SELECT 1 FROM `ai_context_injection` WHERE `conversation_id`='showcase-ai-conv-261' AND `message_id`='showcase-ai-msg-261-01');

INSERT INTO `learning_event` (
  `event_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`, `lab_session_id`,
  `event_type`, `event_time`, `payload_json`, `source`
) VALUES
  ('showcase-demo-ai-261-01',261,1,1,1,2,'showcase-demo-lab-261-2','AI_INTERACTION','2026-07-10 14:08:00',JSON_OBJECT('summary','携带请求耗时和失败现象向 AI 请求排障思路'),'showcase-seed'),
  ('showcase-demo-hint-261-01',261,1,1,1,2,'showcase-demo-lab-261-2','HINT_REQUEST','2026-07-10 14:10:00',JSON_OBJECT('summary','获得恒真/恒假基准与多次采样提示','hint_level',1),'showcase-seed'),
  ('showcase-demo-ai-261-02',261,1,1,1,2,'showcase-demo-lab-261-2','AI_INTERACTION','2026-07-10 14:20:00',JSON_OBJECT('summary','反馈采样数据并说明下一步复测计划'),'showcase-seed'),
  ('showcase-demo-complete-261-01',261,1,1,1,2,'showcase-demo-lab-261-2','LAB_COMPLETE','2026-07-10 14:36:00',JSON_OBJECT('summary','完成盲注基准判断、Payload 调整和自动化复测'),'showcase-seed')
ON DUPLICATE KEY UPDATE `payload_json` = VALUES(`payload_json`), `event_time` = VALUES(`event_time`);

UPDATE `teacher_intervention_student`
SET
  `baseline_snapshot_json` = JSON_OBJECT(
    'snapshotId', 'showcase-baseline-261',
    'computedAt', '2026-07-09T18:00:00',
    'scores', JSON_OBJECT('overall', 71.8, 'knowledgeMastery', 68, 'troubleshooting', 63, 'autonomy', 75, 'aiCollaboration', 72, 'engagement', 78)
  ),
  `latest_snapshot_json` = JSON_OBJECT(
    'snapshotId', 'showcase-latest-261',
    'computedAt', '2026-07-16T20:00:00',
    'scores', JSON_OBJECT('overall', 92.36, 'knowledgeMastery', 87.5, 'troubleshooting', 100, 'autonomy', 89.5, 'aiCollaboration', 88.1, 'engagement', 100)
  ),
  `assignment_status` = 'COMPLETED',
  `training_session_id` = 'showcase-intervention-261',
  `started_at` = '2026-07-10 14:00:00',
  `completed_at` = '2026-07-16 20:00:00'
WHERE `intervention_id` = 1 AND `student_id` = 261;
