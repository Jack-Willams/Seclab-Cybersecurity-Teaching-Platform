USE `userservice`;

INSERT INTO `module` (
  `module_id`,
  `difficulty`,
  `image_id`,
  `introduction`,
  `module_name`,
  `type`
)
SELECT 1, 3, NULL, LEFT('学习Web安全的基本概念和常见漏洞类型，包括SQL注入、XSS等。适合安全学习的入门者。', 255), 'SQL注入基础实验', 'Web安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = 'SQL注入基础实验');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 2, 2, NULL, LEFT('学习XSS跨站脚本攻击的原理、分类和防御方法，包括反射型、存储型和DOM型XSS。', 255), 'XSS跨站脚本攻击实验', 'Web安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = 'XSS跨站脚本攻击实验');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 3, 3, NULL, LEFT('学习CSRF攻击的原理和防御方法，包括Token验证、同源检查等安全措施。', 255), 'CSRF跨站请求伪造实验', 'Web安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = 'CSRF跨站请求伪造实验');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 4, 2, NULL, LEFT('学习命令注入漏洞的原理、危害和防御方法，实践各种命令注入攻击技术。', 255), '命令注入漏洞实验', 'Web安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = '命令注入漏洞实验');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 5, 3, NULL, LEFT('学习文件上传漏洞的原理和利用方法，包括绕过客户端验证、服务器端验证等技术。', 255), '文件上传漏洞实验', 'Web安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = '文件上传漏洞实验');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 6, 3, NULL, LEFT('学习目录遍历漏洞的原理和利用方法，包括路径遍历、敏感文件读取、目录遍历绕过等技术。通过实战演练掌握目录遍历漏洞的发现、利用和防护方法。', 255), '目录遍历', 'Web安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = '目录遍历');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 7, 4, NULL, LEFT('通过静态代码分析和动态测试发现第三方组件安全隐患，深入解析Shiro RememberMe反序列化、Fastjson JNDI注入、Log4j2远程代码执行等高危组件漏洞', 255), '组件漏洞挖掘', 'Web安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = '组件漏洞挖掘');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 8, 3, NULL, LEFT('基于真实电商平台业务流程，系统训练水平越权、垂直越权、支付金额篡改、订单重放攻击等典型业务逻辑漏洞的发现与利用方法', 255), '业务逻辑漏洞实战', 'Web安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = '业务逻辑漏洞实战');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 9, 5, NULL, LEFT('从外网突破到内网控制的完整渗透链路实践，包括边界突破、域环境信息收集、横向移动、域控提权等高级内网渗透技术', 255), '内网渗透技术', '网络攻防'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = '内网渗透技术');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 10, 4, NULL, LEFT('使用静态分析与动态调试相结合的方法，基于真实开源CMS项目源码，系统训练漏洞点定位、参数流追踪、调用链分析等代码审计核心技能', 255), '代码审计进阶', '系统安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = '代码审计进阶');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 11, 5, NULL, LEFT('通过实战演练最新CTF赛题，全面提升Web渗透、二进制逆向、密码学、隐写分析等多领域安全技能，掌握高效解题思路与自动化工具开发方法', 255), 'CTF综合实战', 'CTF'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = 'CTF综合实战');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 12, 5, NULL, LEFT('系统学习红队实战武器装备的使用与定制，包括Cobalt Strike高级功能应用、木马免杀技术、社会工程学钓鱼攻击、网络侦查等红队核心战术与技术', 255), '红队武器库', '网络攻防'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = '红队武器库');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 13, 5, NULL, LEFT('系统讲解从发现到利用的完整漏洞挖掘流程，包括模糊测试技术应用、静态代码分析方法、动态调试技巧、漏洞验证与利用开发以及CVE申请全过程', 255), '漏洞挖掘方法论', '系统安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = '漏洞挖掘方法论');

INSERT INTO `module` (`module_id`, `difficulty`, `image_id`, `introduction`, `module_name`, `type`)
SELECT 14, 5, NULL, LEFT('整漏洞挖掘流程，包包括Thinkphp多种典型漏洞利用、Struts2多种典型漏洞利用、Spring框架典型漏洞利用、若依框架典型漏洞利用等实验内容', 255), '第三方框架漏洞', '系统安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `module` WHERE `module_name` = '第三方框架漏洞');
