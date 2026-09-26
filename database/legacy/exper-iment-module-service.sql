-- MySQL dump 10.13  Distrib 9.3.0, for Win64 (x86_64)
--
-- Host: localhost    Database: experimentmoduleservice
-- ------------------------------------------------------
-- Server version	9.3.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `course`
--

DROP TABLE IF EXISTS `course`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `course` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cost_time` int DEFAULT NULL,
  `course_description` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `difficulty` int DEFAULT NULL COMMENT '难度,1-5',
  `image_url` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instructor` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `course_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `schedule` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `course_status` tinyint DEFAULT NULL,
  `tags` longtext COLLATE utf8mb4_unicode_ci,
  `type` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `course`
--

LOCK TABLES `course` WRITE;
/*!40000 ALTER TABLE `course` DISABLE KEYS */;
INSERT INTO `course` VALUES (1,8,'深度解析字符型/数值型注入原理，涵盖联合查询注入、布尔盲注、时间盲注、报错注入等6大攻击类型，实验包含空格绕过、HEX编码绕过、注释符过滤突破等8种防御绕过技术',3,'a9fe8e50-ba21-45ef-abd5-50b717857502-1.SQL注入攻防实战.png','张春华','SQL注入攻防实战','每周一',1,'[\"SQL注入\", \"Web安全\"]','web'),(2,6,'构建反射型XSS钓鱼页面、存储型XSS持久化攻击、DOM型XSS前端漏洞利用三大实验场景，实战演示Cookie窃取、会话劫持、BeEF框架协同攻击',2,'eb678908-4878-4303-94ae-b3434d52612a-2.XSS漏洞深度解析.png','李明轩','XSS漏洞深度解析','每周二',1,'[\"XSS\", \"Web安全\"]','web'),(3,7,'从客户端校验绕过到服务端检测突破，涵盖图片马制作、Content-Type伪造、.htaccess攻击、二次渲染对抗、竞争条件上传等全链条攻击手法',3,'5780e906-42a1-4a88-ad06-d054bbf92735-3.文件上传漏洞突破.png','王伟国','文件上传漏洞突破','每周一',1,'[\"文件上传\", \"Web安全\"]','web'),(4,10,'实战复现Weblogic反序列化漏洞(CVE-2023-21839)、Tomcat AJP协议漏洞(CVE-2020-1938)、JBoss JMXInvokerServlet反序列化三大经典漏洞',4,'be008126-c024-4c85-90d0-80679d070bbf-4.中间件漏洞利用.png','张鹏飞','中间件漏洞利用','每周三',1,'[\"中间件\", \"系统安全\"]','system'),(5,9,'深入解析Shiro RememberMe反序列化、Fastjson JNDI注入、Log4j2远程代码执行(Log4Shell)三大组件漏洞的利用链构造与防御方案',4,'3084b1de-36fd-4e46-a8b1-da4f86928ea0-5.组件漏洞挖掘.png','刘洋','组件漏洞挖掘','每周三',1,'[\"组件漏洞\", \"系统安全\"]','system'),(6,8,'涵盖ThinkPHP多版本RCE漏洞利用、Struts2 OGNL表达式注入、Spring Cloud Gateway远程代码执行(CVE-2022-22947)等框架级漏洞实战',4,'93bc5c26-9d01-476c-9f82-073d6af74e4e-6.框架漏洞利用.png','陈建华','框架漏洞利用','每周四',1,'[\"框架漏洞\", \"Web安全\"]','web'),(7,6,'模拟电商平台实战环境，训练支付金额篡改、平行越权访问、短信炸弹攻击、验证码复用漏洞、空订单生成等12种典型业务场景漏洞挖掘',3,'228721b0-a517-4543-8a53-bb04fcbead31-7.业务逻辑漏洞实战.png','赵丽娜','业务逻辑漏洞实战','每周五',1,'[\"业务逻辑\", \"Web安全\"]','web'),(8,12,'构建完整内网渗透链路：从CS/MSF木马植入→横向移动(PTH/PTT)→域控提权→隧道搭建(SSH/ICMP)→权限维持(黄金票据/影子账户)',5,'87328129-c885-4322-893b-7d42a96e534a-8.内网渗透技术.png','孙浩','内网渗透技术','每周二',1,'[\"内网渗透\", \"网络安全\"]','network'),(9,10,'基于真实CMS源码分析，训练SQL注入点定位、反序列化利用链构造、文件包含漏洞追踪、危险函数回溯等代码审计核心技能',4,'05ba581f-c254-4062-9b08-53b7d950ae21-9.代码审计进阶.png','周杰','代码审计进阶','每周四',1,'[\"代码审计\", \"Web安全\"]','web'),(10,15,'集成Web渗透、二进制逆向、密码破解、隐写分析等竞赛题型，包含2023年最新CTF赛题解析与自动化脚本开发技巧',5,'fe106f4f-0a2b-4d5c-bfd9-5e4533168c02-10.CTF攻防实战.png','吴婷婷','CTF综合实战','每周二',1,'[\"CTF\", \"密码学\"]','crypto'),(11,14,'深度使用Cobalt Strike 4.9进行协同作战，涵盖木马免杀(Shellcode混淆/内存加载)、钓鱼攻击、横向移动、痕迹清理等红队战术',5,'dbae718b-4719-4843-99f6-3cfd83356672-11.红队武器库.png','郑强','红队武器库','每周三',1,'[\"红队\", \"渗透测试\"]','network'),(12,16,'从模糊测试到静态分析，完整漏洞挖掘流程实践：AFL智能模糊测试→IDA Pro逆向分析→GDB动态调试→PoC验证→CVE申请流程',5,'7d700ad9-e623-4644-9aab-b9cf8a98778d-12.漏洞挖掘方法论.png','冯志刚','漏洞挖掘方法论','每周五',1,'[\"漏洞挖掘\", \"系统安全\"]','system'),(13,11,'涵盖传感器网络攻击、智能家居设备漏洞利用、工业控制系统（ICS）攻击与防御、RFID伪造与重放攻击等实战场景',4,'74969611-024a-41c0-8a10-be8274dc1a40-物联网安全.jpg','李华强','物联网安全攻防','每周五',1,'[\"物联网安全\", \"网络安全\"]','network');
/*!40000 ALTER TABLE `course` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `module`
--

DROP TABLE IF EXISTS `module`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `module` (
  `module_id` int NOT NULL AUTO_INCREMENT,
  `difficulty` int DEFAULT NULL,
  `image_id` int DEFAULT NULL,
  `introduction` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `module_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `task_points` longtext COLLATE utf8mb4_unicode_ci,
  `type` longtext COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`module_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `module`
--

LOCK TABLES `module` WRITE;
/*!40000 ALTER TABLE `module` DISABLE KEYS */;
INSERT INTO `module` VALUES (1,2,101,'网络安全基础入门课程','网络安全基础','[]','[\"理论\",\"基础\"]'),(2,3,102,'Web安全漏洞实战演练','Web安全攻防','[]','[\"实战\",\"攻防\"]');
/*!40000 ALTER TABLE `module` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `module_course`
--

DROP TABLE IF EXISTS `module_course`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `module_course` (
  `course_id` int NOT NULL,
  `module_id` int NOT NULL,
  KEY `FKgxoafsp67wnswrtckiv23wovg` (`module_id`),
  KEY `FK12rrfmx7sh0v26b0b2kdr81kl` (`course_id`),
  CONSTRAINT `FK12rrfmx7sh0v26b0b2kdr81kl` FOREIGN KEY (`course_id`) REFERENCES `course` (`id`),
  CONSTRAINT `FKgxoafsp67wnswrtckiv23wovg` FOREIGN KEY (`module_id`) REFERENCES `module` (`module_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `module_course`
--

LOCK TABLES `module_course` WRITE;
/*!40000 ALTER TABLE `module_course` DISABLE KEYS */;
/*!40000 ALTER TABLE `module_course` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'experimentmoduleservice'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-07-18 12:37:02
