-- Local bootstrap for experiment-module-service when it is configured to use
-- the userservice database in application.yml.

CREATE DATABASE IF NOT EXISTS `userservice`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `userservice`;

CREATE TABLE IF NOT EXISTS `course` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `cost_time` INT DEFAULT NULL,
  `course_description` VARCHAR(1024) NOT NULL,
  `difficulty` INT DEFAULT NULL,
  `image_url` VARCHAR(255) DEFAULT NULL,
  `instructor` VARCHAR(255) DEFAULT NULL,
  `created_by` BIGINT NULL,
  `course_name` VARCHAR(255) NOT NULL,
  `schedule` VARCHAR(255) DEFAULT NULL,
  `course_status` TINYINT DEFAULT 1,
  `tags` LONGTEXT DEFAULT NULL,
  `type` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_course_status_type` (`course_status`, `type`),
  KEY `idx_course_creator_status` (`created_by`, `course_status`),
  CONSTRAINT `fk_course_creator`
    FOREIGN KEY (`created_by`) REFERENCES `user` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `module` (
  `module_id` INT NOT NULL AUTO_INCREMENT,
  `difficulty` INT DEFAULT NULL,
  `image_id` INT DEFAULT NULL,
  `introduction` VARCHAR(1024) DEFAULT NULL,
  `module_name` VARCHAR(255) DEFAULT NULL,
  `task_points` LONGTEXT DEFAULT NULL,
  `type` LONGTEXT DEFAULT NULL,
  PRIMARY KEY (`module_id`),
  KEY `idx_module_difficulty` (`difficulty`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 老库自愈：`course` 建表语句用的是 CREATE TABLE IF NOT EXISTS，已存在的表不会补新列，
-- 而 experiment-module-service 是 ddl-auto: none，Hibernate 也不会补。这里显式补齐 created_by。
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'course' AND COLUMN_NAME = 'created_by'
);
SET @ddl := IF(@col_exists = 0,
  'ALTER TABLE `course` ADD COLUMN `created_by` BIGINT NULL AFTER `instructor`, ADD KEY `idx_course_creator_status` (`created_by`, `course_status`)',
  'DO 0');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

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

-- 课程目录以学生端 src/mock/catalogPresentation.ts 的 PRESENTATION_COURSE_SEEDS 为准，
-- 保证教师端「课程库」与学生端课程名、分类完全一致（前端按课程名做合并匹配）。
-- id 1/2/3 已被 teaching_class_course 与作答数据引用，只做原地更新，不重新编号。
INSERT INTO `course`
  (`id`, `course_description`, `difficulty`, `image_url`, `instructor`, `course_name`, `course_status`, `tags`, `type`)
VALUES
  (1, '系统讲解 SQL 注入原理、利用方式与常见防护策略。', 3, '1.SQL注入攻防实战.png', '李伟', 'SQL注入攻击', 1, '["SQL注入", "Web安全", "数据库安全"]', 'Web安全'),
  (2, '围绕 XSS 与 CSRF 攻击链路，训练前端安全分析与防护能力。', 2, '2.XSS漏洞深度解析.png', '李伟', 'XSS与CSRF攻击', 1, '["XSS", "CSRF", "前端安全"]', 'Web安全'),
  -- id 3「文件上传漏洞」已按 2026-08-08 的目录基线从课程列表移除，所以这里不再维护它
  -- （同名的靶场实验保留，那是另一回事）。前端种子里也没有这门课，而合并是以种子为主干，
  -- 所以即使库里还留着这一行，学生端课程列表也不会显示它。
  --
  -- 本脚本是 INSERT ... ON DUPLICATE KEY UPDATE，不会删老库里已存在的 id=3。
  -- 目前本地库**刻意保留**着它，因为 teaching_class_course 里有 3 条排课引用，
  -- 其中「网络安全231」只排了这一门，直接删会变成 0 门课的空班。
  -- 真要清干净：先把那 3 行改挂到别的课（或删掉），再 DELETE FROM course WHERE id=3。
  (4, '介绍 IDS 与 IPS 的工作机制、部署方法与流量分析思路。', 3, 'cover-ids-ips.png', '李伟', 'IDS和IPS系统', 1, '["IDS", "IPS", "网络安全"]', '网络安全'),
  (5, '通过案例分析理解 APT 攻击链路、战术特征与应对方式。', 4, 'cover-apt.png', '李伟', 'APT攻击分析', 1, '["APT", "威胁分析", "安全运营"]', '高级威胁'),
  (6, '学习防火墙原理、规则配置和网络边界防护方法。', 3, 'cover-firewall.png', '李伟', '防火墙技术', 1, '["防火墙", "边界防护", "网络安全"]', '网络安全'),
  (7, '掌握古典密码体制、手工破译思路与密码学基础概念。', 2, 'cover-classic-crypto.png', '李伟', '古典密码学', 1, '["密码学", "古典密码", "安全基础"]', '密码学'),
  (8, '介绍公钥密码体系、密钥管理、证书与 PKI 基础。', 3, 'cover-pubkey.png', '李伟', '公钥密码简介', 1, '["公钥密码", "PKI", "证书体系"]', '密码学'),
  (9, '深入理解 RSA 的数学原理、密钥生成与典型应用。', 4, 'cover-rsa.png', '李伟', 'RSA公钥加密方案', 1, '["RSA", "非对称加密", "密码学"]', '密码学'),
  (10, '学习数字签名、身份认证和证书验证相关核心技术。', 4, 'cover-signature.png', '李伟', '数字签名技术', 1, '["数字签名", "身份认证", "密码学"]', '密码学'),
  (11, '建立操作系统安全机制、访问控制与系统加固的整体认知。', 3, 'cover-os-security.png', '李伟', '操作系统安全概述', 1, '["操作系统安全", "访问控制", "系统加固"]', '系统安全'),
  (12, '学习可信计算、TPM、可信启动与远程证明等关键概念。', 4, 'cover-trusted-computing.png', '李伟', '可信计算技术', 1, '["可信计算", "TPM", "系统安全"]', '系统安全'),
  (13, '梳理网络安全基础概念、威胁类型与整体防护框架。', 3, 'cover-network-security.png', '李伟', '网络安全概述', 1, '["网络安全", "安全架构", "防护体系"]', '网络安全'),
  (14, '讲解栈缓冲区溢出的原理、内存布局与利用思路，带你入门二进制安全（PWN）。', 4, 'cover-stack-overflow.png', '李伟', '栈溢出', 1, '["栈溢出", "二进制安全", "PWN"]', '二进制安全'),
  (15, '讲解堆内存管理与堆溢出漏洞原理，介绍 chunk 结构、malloc/free 机制与常见堆利用手法。', 5, 'cover-heap-overflow.png', '李伟', '堆溢出', 1, '["堆溢出", "二进制安全", "PWN"]', '二进制安全'),
  (16, '讲解格式化字符串漏洞的成因与利用，掌握任意地址读写与信息泄露技巧。', 4, 'cover-format-string.png', '李伟', '格式化字符串', 1, '["格式化字符串", "二进制安全", "PWN"]', '二进制安全'),
  -- image_url 故意留 NULL：前端合并时 `imageUrl: remote.imageUrl || base.imageUrl`，
  -- 留空才会回落到种子里的 `/协议分析实战.png`，不必在这里操心 image-service 的路径拼接规则。
  (17, '使用 Wireshark 深度分析 HTTP/TCP/UDP 协议，理解明文嗅探与 HTTPS 防护。', 3, NULL, '李伟', '协议分析实战', 1, '["协议分析", "Wireshark", "网络安全"]', '网络安全')
ON DUPLICATE KEY UPDATE
  `course_description` = VALUES(`course_description`),
  `difficulty` = VALUES(`difficulty`),
  `instructor` = VALUES(`instructor`),
  `course_name` = VALUES(`course_name`),
  `course_status` = VALUES(`course_status`),
  `tags` = VALUES(`tags`),
  `type` = VALUES(`type`);

INSERT INTO `module`
  (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
VALUES
  (1, 3, 101, '在靶场中完成 SQL 注入定位、验证和参数化修复。', 'SQL 注入基础实验', '["SQL注入","Web安全"]'),
  (2, 2, 102, '完成 XSS 与 CSRF 攻击验证并比较不同防护方式。', 'XSS 与 CSRF 基础实验', '["XSS","CSRF","Web安全"]'),
  (3, 3, 103, '分析上传校验缺陷并给出后端校验与隔离建议。', '文件上传安全实验', '["文件上传","Web安全"]')
ON DUPLICATE KEY UPDATE
  `difficulty` = VALUES(`difficulty`),
  `introduction` = VALUES(`introduction`),
  `module_name` = VALUES(`module_name`),
  `type` = VALUES(`type`);

-- 这里原来写的是 (1,2),(2,3),(3,4)，三条映射整体错位一位：
--   SQL 注入基础实验 -> XSS与CSRF攻击 / XSS 与 CSRF 基础实验 -> 文件上传漏洞 / 文件上传安全实验 -> IDS和IPS系统
-- 而且上面的 DELETE 只清正确的那三对，等于每跑一次脚本就把对的删掉、再把错的写回去。
-- 2026-08-08 修正。DELETE 改成按 module_id 清，跑几次都能收敛到正确映射。
--
-- 「文件上传安全实验」原属的「文件上传漏洞」课程已按目录基线删除（见上方 course 注释），
-- 靶场本身保留，改挂同为 Web 安全的「XSS与CSRF攻击」。
DELETE FROM `module_course` WHERE `module_id` IN (1, 2, 3);

INSERT IGNORE INTO `module_course` (`module_id`, `course_id`) VALUES
  (1, 1),
  (2, 2),
  (3, 2);
