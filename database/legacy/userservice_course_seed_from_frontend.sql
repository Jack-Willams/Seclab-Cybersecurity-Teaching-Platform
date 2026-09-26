USE `userservice`;

INSERT INTO `course` (
  `id`,
  `course_description`,
  `course_name`,
  `course_status`,
  `difficulty`,
  `image_url`,
  `instructor`,
  `tags`,
  `type`
)
SELECT
  1,
  '本课程详细讲解SQL注入攻击的原理、分类和防御技术。通过实际案例演示如何发现和利用SQL注入漏洞，以及如何通过参数化查询、输入验证和最小权限原则等方法防止SQL注入攻击，保障Web应用的数据安全。',
  'SQL注入攻击',
  1,
  3,
  '/1.SQL注入攻防实战.png',
  'SecLab 教研组',
  'SQL注入,Web安全,数据库安全',
  'Web安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `course` WHERE `course_name` = 'SQL注入攻击');

INSERT INTO `course` (`id`, `course_description`, `course_name`, `course_status`, `difficulty`, `image_url`, `instructor`, `tags`, `type`)
SELECT 2, '本课程深入剖析跨站脚本(XSS)和跨站请求伪造(CSRF)攻击的原理和防御方法。通过实例演示反射型XSS、存储型XSS和DOM型XSS攻击，以及CSRF攻击的实施过程，帮助学习者掌握Web前端安全防护的关键技术。', 'XSS与CSRF攻击', 1, 2, '/2.XSS漏洞深度解析.png', 'SecLab 教研组', 'XSS,CSRF,Web安全', 'Web安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `course` WHERE `course_name` = 'XSS与CSRF攻击');

INSERT INTO `course` (`id`, `course_description`, `course_name`, `course_status`, `difficulty`, `image_url`, `instructor`, `tags`, `type`)
SELECT 3, '本课程介绍入侵检测系统(IDS)和入侵防御系统(IPS)的工作原理和部署策略。通过分析网络流量和系统行为，识别和防御各类网络攻击，包括异常检测、特征匹配和行为分析等技术，帮助学习者构建有效的网络安全防护体系。', 'IDS和IPS系统', 1, 3, '/3.文件上传漏洞突破 .png', 'SecLab 教研组', 'IDS,IPS,网络安全', '网络安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `course` WHERE `course_name` = 'IDS和IPS系统');

INSERT INTO `course` (`id`, `course_description`, `course_name`, `course_status`, `difficulty`, `image_url`, `instructor`, `tags`, `type`)
SELECT 4, '本课程深入分析高级持续性威胁(APT)攻击的特点和防御策略。通过实际APT攻击案例分析，介绍攻击者的战术、技术和程序(TTP)，以及如何建立有效的威胁情报和安全防御体系，提升组织抵御高级威胁的能力。', 'APT攻击分析', 1, 4, '/4.中间件漏洞利用.png', 'SecLab 教研组', 'APT,高级威胁,网络安全', '高级威胁'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `course` WHERE `course_name` = 'APT攻击分析');

INSERT INTO `course` (`id`, `course_description`, `course_name`, `course_status`, `difficulty`, `image_url`, `instructor`, `tags`, `type`)
SELECT 5, '本课程详细讲解网络防火墙的原理、类型和配置方法。包括包过滤防火墙、状态检测防火墙、应用层防火墙和下一代防火墙的特点与部署策略，以及访问控制列表(ACL)、NAT配置、VPN集成等实用技术，帮助学习者掌握网络边界防护的核心技能。', '防火墙技术', 1, 3, '/5.组件漏洞挖掘.png', 'SecLab 教研组', '防火墙,网络安全,边界防护', '网络安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `course` WHERE `course_name` = '防火墙技术');

INSERT INTO `course` (`id`, `course_description`, `course_name`, `course_status`, `difficulty`, `image_url`, `instructor`, `tags`, `type`)
SELECT 6, '本课程详细介绍古典密码学的基本原理、常见加密与解密方法及其历史背景。内容涵盖凯撒密码、仿射密码、维吉尼亚密码等经典算法，通过实战演练，掌握古典密码的加密、破解与分析技巧，提升密码学基础素养和安全意识。', '古典密码学', 1, 3, '/6.框架漏洞利用.png', 'SecLab 教研组', '目录遍历,Web安全,路径遍历', 'Web安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `course` WHERE `course_name` = '古典密码学');

INSERT INTO `course` (`id`, `course_description`, `course_name`, `course_status`, `difficulty`, `image_url`, `instructor`, `tags`, `type`)
SELECT 7, '本课程详细讲解公钥密码体系的基本原理和应用场景。介绍非对称加密的数学基础、密钥管理、数字证书和PKI体系，以及RSA、ECC等常用公钥算法的工作机制，帮助学习者理解现代密码学中最重要的概念和技术。', '公钥密码简介', 1, 3, '/7.业务逻辑漏洞实战.png', 'SecLab 教研组', '公钥密码,非对称加密,密码学', '密码学'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `course` WHERE `course_name` = '公钥密码简介');

INSERT INTO `course` (`id`, `course_description`, `course_name`, `course_status`, `difficulty`, `image_url`, `instructor`, `tags`, `type`)
SELECT 8, '本课程深入剖析RSA公钥加密算法的数学原理、实现细节和安全性分析。包括素数生成、密钥生成、加密解密过程、数字签名应用，以及常见攻击方法和防御措施，帮助学习者全面掌握这一最广泛使用的公钥密码系统。', 'RSA公钥加密方案', 1, 4, '/8.内网渗透技术.png', 'SecLab 教研组', 'RSA,公钥密码,密码学', '密码学'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `course` WHERE `course_name` = 'RSA公钥加密方案');

INSERT INTO `course` (`id`, `course_description`, `course_name`, `course_status`, `difficulty`, `image_url`, `instructor`, `tags`, `type`)
SELECT 9, '本课程详细介绍数字签名的原理、算法和应用。包括RSA签名、DSA、ECDSA等签名算法的工作机制，数字证书与PKI体系，以及时间戳、盲签名等高级签名技术，帮助学习者理解数字签名在信息安全中的重要作用和实现方法。', '数字签名技术', 1, 4, '/9.代码审计进阶.png', 'SecLab 教研组', '数字签名,PKI,密码学', '密码学'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `course` WHERE `course_name` = '数字签名技术');

INSERT INTO `course` (`id`, `course_description`, `course_name`, `course_status`, `difficulty`, `image_url`, `instructor`, `tags`, `type`)
SELECT 10, '本课程全面介绍操作系统安全的核心概念和防护技术。包括访问控制、权限管理、认证机制、内核安全、内存保护等基础安全机制，以及常见操作系统的安全配置和加固方法，帮助学习者建立系统安全的整体认识。', '操作系统安全概述', 1, 3, '/10.CTF攻防实战.png', 'SecLab 教研组', '操作系统安全,系统安全,访问控制', '系统安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `course` WHERE `course_name` = '操作系统安全概述');

INSERT INTO `course` (`id`, `course_description`, `course_name`, `course_status`, `difficulty`, `image_url`, `instructor`, `tags`, `type`)
SELECT 11, '本课程深入讲解可信计算的基本原理和关键技术。包括可信平台模块(TPM)、可信启动、远程证明、密封存储等可信计算机制，以及可信计算在云计算、物联网等领域的应用，帮助学习者理解构建可信系统的方法和挑战。', '可信计算技术', 1, 4, '/11.红队武器库.png', 'SecLab 教研组', '可信计算,系统安全,TPM', '系统安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `course` WHERE `course_name` = '可信计算技术');

INSERT INTO `course` (`id`, `course_description`, `course_name`, `course_status`, `difficulty`, `image_url`, `instructor`, `tags`, `type`)
SELECT 12, '本课程全面介绍网络安全的基本概念、威胁类型和防护策略。包括网络攻击分类、网络协议安全、边界防护、入侵检测与防御、安全运维等核心内容，帮助学习者建立网络安全的整体认识和防护思路。', '网络安全概述', 1, 3, '/12.漏洞挖掘方法论.png', 'SecLab 教研组', '网络安全,安全架构,威胁防护', '网络安全'
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM `course` WHERE `course_name` = '网络安全概述');
