SET NAMES utf8mb4;
USE `seclab_profile`;

-- Idempotent showcase evidence for the imported 网络安全232班 students.
-- These rows go through the same profile scorer and insight queries as live data.
INSERT IGNORE INTO `lab_session` (
  `session_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`,
  `container_name`, `status`, `start_time`, `end_time`
)
SELECT
  CONCAT('showcase-lab-', tcs.student_id), tcs.student_id, 1,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 1 END,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 5 END,
  1, CONCAT('showcase-sec-', tcs.student_id), 'stopped',
  TIMESTAMP('2026-07-14 14:00:00') + INTERVAL MOD(tcs.student_id, 24) MINUTE,
  TIMESTAMP('2026-07-14 14:24:00') + INTERVAL MOD(tcs.student_id, 24) MINUTE
FROM `userservice`.`teaching_class_student` tcs
WHERE tcs.teaching_class_id = 1;

INSERT IGNORE INTO `container_command_event` (
  `command_id`, `lab_session_id`, `user_id`, `class_id`, `course_id`,
  `module_id`, `task_id`, `container_name`, `command`, `normalized_command`,
  `cmd_category`, `cwd`, `exit_code`, `duration_ms`, `output_digest`, `source`, `executed_at`
)
SELECT
  CONCAT('showcase-cmd-', tcs.student_id, '-fail'), CONCAT('showcase-lab-', tcs.student_id),
  tcs.student_id, 1,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 1 END,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 5 END,
  1, CONCAT('showcase-sec-', tcs.student_id),
  CASE MOD(tcs.student_id, 3)
    WHEN 0 THEN 'sqlmap -u http://target/item?id=1 --batch --technique=T'
    WHEN 1 THEN 'curl http://target/search?q=<script>alert(1)</script>'
    ELSE 'curl -F file=@shell.php -H Content-Type:image/jpeg http://target/upload'
  END,
  CASE MOD(tcs.student_id, 3)
    WHEN 0 THEN 'sqlmap -u <url> --batch --technique=t'
    WHEN 1 THEN 'curl <url>?q=<payload>'
    ELSE 'curl -f file=@<file> -h content-type:<type> <url>'
  END,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 'sql_injection' WHEN 1 THEN 'xss' ELSE 'file_upload' END,
  '/workspace', 1, 1800,
  CASE MOD(tcs.student_id, 3)
    WHEN 0 THEN '未观察到稳定延时，真假条件缺少基准对照'
    WHEN 1 THEN '响应中 payload 被 HTML 编码，脚本未执行'
    ELSE '服务端检测到 PHP 内容并拒绝上传'
  END,
  'showcase-seed',
  TIMESTAMP('2026-07-14 14:05:00') + INTERVAL MOD(tcs.student_id, 24) MINUTE
FROM `userservice`.`teaching_class_student` tcs
WHERE tcs.teaching_class_id = 1;

INSERT IGNORE INTO `error_event` (
  `error_id`, `lab_session_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`,
  `container_name`, `command_id`, `error_signature`, `error_category`, `raw_excerpt`,
  `severity`, `source`, `occurred_at`
)
SELECT
  CONCAT('showcase-error-', tcs.student_id), CONCAT('showcase-lab-', tcs.student_id),
  tcs.student_id, 1,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 1 END,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 5 END,
  1, CONCAT('showcase-sec-', tcs.student_id), CONCAT('showcase-cmd-', tcs.student_id, '-fail'),
  CASE MOD(tcs.student_id, 3)
    WHEN 0 THEN 'blind-baseline-missing'
    WHEN 1 THEN 'output-context-mismatch'
    ELSE 'upload-content-detected'
  END,
  CASE MOD(tcs.student_id, 3)
    WHEN 0 THEN 'SQL盲注验证步骤'
    WHEN 1 THEN 'XSS输出上下文'
    ELSE '文件上传内容校验'
  END,
  CASE MOD(tcs.student_id, 3)
    WHEN 0 THEN '直接加入延时条件，未先比较恒真与恒假请求'
    WHEN 1 THEN '未区分 HTML 文本上下文与脚本上下文'
    ELSE '只修改 Content-Type，未处理文件内容特征'
  END,
  'medium', 'showcase-seed',
  TIMESTAMP('2026-07-14 14:06:00') + INTERVAL MOD(tcs.student_id, 24) MINUTE
FROM `userservice`.`teaching_class_student` tcs
WHERE tcs.teaching_class_id = 1;

INSERT IGNORE INTO `learning_event` (
  `event_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`,
  `lab_session_id`, `event_type`, `event_time`, `payload_json`, `source`
)
SELECT
  CONCAT('showcase-replay-start-', tcs.student_id), tcs.student_id, 1,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 1 END,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 5 END,
  1, CONCAT('showcase-lab-', tcs.student_id), 'LAB_START',
  TIMESTAMP('2026-07-14 14:00:00') + INTERVAL MOD(tcs.student_id, 24) MINUTE,
  JSON_OBJECT('summary', '开始网络安全实验'), 'showcase-seed'
FROM `userservice`.`teaching_class_student` tcs
WHERE tcs.teaching_class_id = 1;

INSERT IGNORE INTO `learning_event` (
  `event_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`,
  `lab_session_id`, `event_type`, `event_time`, `payload_json`, `source`
)
SELECT
  CONCAT('showcase-replay-hint-', tcs.student_id), tcs.student_id, 1,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 1 END,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 5 END,
  1, CONCAT('showcase-lab-', tcs.student_id), 'HINT_REQUEST',
  TIMESTAMP('2026-07-14 14:10:00') + INTERVAL MOD(tcs.student_id, 24) MINUTE,
  JSON_OBJECT('summary', '根据错误信息请求针对性提示', 'hint_level', 1), 'showcase-seed'
FROM `userservice`.`teaching_class_student` tcs
WHERE tcs.teaching_class_id = 1;

INSERT IGNORE INTO `container_command_event` (
  `command_id`, `lab_session_id`, `user_id`, `class_id`, `course_id`,
  `module_id`, `task_id`, `container_name`, `command`, `normalized_command`,
  `cmd_category`, `cwd`, `exit_code`, `duration_ms`, `output_digest`, `source`, `executed_at`
)
SELECT
  CONCAT('showcase-cmd-', tcs.student_id, '-success'), CONCAT('showcase-lab-', tcs.student_id),
  tcs.student_id, 1,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 1 END,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 5 END,
  1, CONCAT('showcase-sec-', tcs.student_id),
  CASE MOD(tcs.student_id, 3)
    WHEN 0 THEN 'sqlmap -u http://target/item?id=1 --batch --technique=T --time-sec=3'
    WHEN 1 THEN 'curl http://target/profile?name=<img src=x onerror=alert(1)>'
    ELSE 'curl -F file=@avatar.phtml.jpg -H Content-Type:image/jpeg http://target/upload'
  END,
  CASE MOD(tcs.student_id, 3)
    WHEN 0 THEN 'sqlmap -u <url> --batch --technique=t --time-sec=<n>'
    WHEN 1 THEN 'curl <url>?name=<context-payload>'
    ELSE 'curl -f file=@<polyglot> -h content-type:<type> <url>'
  END,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 'sql_injection' WHEN 1 THEN 'xss' ELSE 'file_upload' END,
  '/workspace', 0, 2300,
  CASE MOD(tcs.student_id, 3)
    WHEN 0 THEN '恒真/恒假基准稳定，延时条件验证成功'
    WHEN 1 THEN '在属性上下文触发事件处理器'
    ELSE '上传成功并验证解析差异'
  END,
  'showcase-seed',
  TIMESTAMP('2026-07-14 14:18:00') + INTERVAL MOD(tcs.student_id, 24) MINUTE
FROM `userservice`.`teaching_class_student` tcs
WHERE tcs.teaching_class_id = 1;

INSERT IGNORE INTO `challenge_completion_event` (
  `user_id`, `class_id`, `course_id`, `module_id`, `task_id`, `lab_session_id`,
  `completion_status`, `total_time_seconds`, `total_ai_ask_count`, `created_at`
)
SELECT
  tcs.student_id, 1,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 1 END,
  CASE MOD(tcs.student_id, 3) WHEN 0 THEN 1 WHEN 1 THEN 2 ELSE 5 END,
  1, CONCAT('showcase-lab-', tcs.student_id), 'completed', 1440, 1,
  TIMESTAMP('2026-07-14 14:24:00') + INTERVAL MOD(tcs.student_id, 24) MINUTE
FROM `userservice`.`teaching_class_student` tcs
WHERE tcs.teaching_class_id = 1
  AND NOT EXISTS (
    SELECT 1 FROM `challenge_completion_event` cce
    WHERE cce.lab_session_id = CONCAT('showcase-lab-', tcs.student_id)
  );
