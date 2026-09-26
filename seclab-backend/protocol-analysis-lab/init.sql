-- ════════════════════════════════════════════════════════════════
--  Protocol Analysis Lab Database Initialization
--  协议分析实验靶场数据库初始化脚本
-- ════════════════════════════════════════════════════════════════
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET character_set_connection=utf8mb4;

CREATE DATABASE IF NOT EXISTS protocol_lab;
USE protocol_lab;

-- ── 1. Network Packets Table (网络数据包表) ──
CREATE TABLE IF NOT EXISTS packets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp VARCHAR(50) NOT NULL,
    source_ip VARCHAR(50) NOT NULL,
    destination_ip VARCHAR(50) NOT NULL,
    protocol VARCHAR(20) NOT NULL,
    source_port VARCHAR(10),
    destination_port VARCHAR(10),
    length INT NOT NULL,
    flags VARCHAR(20),
    payload TEXT,
    info VARCHAR(255)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

INSERT IGNORE INTO packets (id, timestamp, source_ip, destination_ip, protocol, source_port, destination_port, length, flags, payload, info) VALUES
(1,  '2024-01-15 10:30:00.123456', '192.168.1.100', '192.168.1.200', 'TCP', '49152', '80', 60, 'SYN', '', 'TCP SYN - 三次握手第一步'),
(2,  '2024-01-15 10:30:00.123567', '192.168.1.200', '192.168.1.100', 'TCP', '80', '49152', 60, 'SYN,ACK', '', 'TCP SYN-ACK - 三次握手第二步'),
(3,  '2024-01-15 10:30:00.123678', '192.168.1.100', '192.168.1.200', 'TCP', '49152', '80', 52, 'ACK', '', 'TCP ACK - 三次握手第三步'),
(4,  '2024-01-15 10:30:00.124123', '192.168.1.100', '192.168.1.200', 'HTTP', '49152', '80', 256, '', 'GET /api/users HTTP/1.1\r\nHost: server.com\r\nCookie: session=abc123', 'HTTP GET 请求'),
(5,  '2024-01-15 10:30:00.124567', '192.168.1.200', '192.168.1.100', 'HTTP', '80', '49152', 512, '', 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n{"users":["admin","alice","bob"]}', 'HTTP 响应'),
(6,  '2024-01-15 10:30:01.000000', '10.0.0.5', '10.0.0.10', 'UDP', '53', '53', 72, '', 'DNS 查询: www.example.com', 'DNS 查询'),
(7,  '2024-01-15 10:30:01.000123', '10.0.0.10', '10.0.0.5', 'UDP', '53', '53', 102, '', 'DNS 响应: 93.184.216.34', 'DNS 响应'),
(8,  '2024-01-15 10:30:05.555555', '172.16.0.1', '172.16.0.255', 'ARP', '', '', 42, '', 'ARP 请求: Who has 172.16.0.255?', 'ARP 请求'),
(9,  '2024-01-15 10:30:10.999999', '192.168.1.100', '192.168.1.200', 'TCP', '49152', '80', 52, 'FIN,ACK', '', 'TCP FIN-ACK - 连接关闭'),
(10, '2024-01-15 10:30:11.000000', '192.168.1.200', '192.168.1.100', 'TCP', '80', '49152', 52, 'ACK', '', 'TCP ACK - 确认关闭');

-- ── 2. HTTP Requests Table (HTTP请求记录表) ──
CREATE TABLE IF NOT EXISTS http_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    method VARCHAR(10) NOT NULL,
    path VARCHAR(255) NOT NULL,
    protocol VARCHAR(20) NOT NULL,
    host VARCHAR(100),
    user_agent VARCHAR(255),
    referer VARCHAR(255),
    cookie TEXT,
    body TEXT,
    status_code INT,
    response_headers TEXT,
    response_body TEXT,
    captured_at VARCHAR(50) NOT NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

INSERT IGNORE INTO http_requests (id, method, path, protocol, host, user_agent, referer, cookie, body, status_code, response_headers, response_body, captured_at) VALUES
(1,  'GET', '/', 'HTTP/1.1', 'localhost', 'Mozilla/5.0 (Windows NT 10.0)', NULL, 'session=xyz789', NULL, 200, 'Content-Type: text/html', '<html>Welcome</html>', '2024-01-15 10:00:00'),
(2,  'POST', '/login', 'HTTP/1.1', 'localhost', 'Mozilla/5.0 (Windows NT 10.0)', 'http://localhost/', NULL, 'username=admin&password=secret123', 200, 'Set-Cookie: session=abc123', '{"status":"success"}', '2024-01-15 10:00:05'),
(3,  'GET', '/api/secret', 'HTTP/1.1', 'localhost', 'Mozilla/5.0 (Windows NT 10.0)', NULL, 'session=flag{http_analysis_master_2024}', NULL, 200, 'Content-Type: application/json', '{"secret":"flag{http_analysis_master_2024}"}', '2024-01-15 10:00:10'),
(4,  'GET', '/robots.txt', 'HTTP/1.1', 'localhost', 'curl/7.81.0', NULL, NULL, NULL, 200, 'Content-Type: text/plain', 'Disallow: /admin\nDisallow: /secret', '2024-01-15 10:00:15'),
(5,  'POST', '/api/data', 'HTTP/1.1', 'localhost', 'Python-urllib/3.9', NULL, NULL, '{"data":"sensitive"}', 201, 'Location: /api/data/1', NULL, '2024-01-15 10:00:20');

-- ── 3. Security Events Table (安全事件表) ──
CREATE TABLE IF NOT EXISTS security_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    source_ip VARCHAR(50),
    destination_ip VARCHAR(50),
    description TEXT,
    timestamp VARCHAR(50) NOT NULL,
    flag VARCHAR(100)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

INSERT IGNORE INTO security_events (id, event_type, severity, source_ip, destination_ip, description, timestamp, flag) VALUES
(1,  'Port Scan', 'Medium', '192.168.1.105', '192.168.1.200', '检测到端口扫描行为，扫描了端口 21, 22, 80, 443', '2024-01-15 09:30:00', NULL),
(2,  'SQL Injection', 'High', '192.168.1.106', '192.168.1.200', '检测到SQL注入尝试: SELECT * FROM users WHERE id=1 OR 1=1', '2024-01-15 09:35:00', NULL),
(3,  'XSS Attempt', 'High', '192.168.1.107', '192.168.1.200', '检测到XSS攻击尝试: <script>alert("xss")</script>', '2024-01-15 09:40:00', NULL),
(4,  'Brute Force', 'High', '192.168.1.108', '192.168.1.200', '检测到暴力破解攻击，尝试了 500+ 次登录', '2024-01-15 09:45:00', NULL),
(5,  'Data Exfiltration', 'Critical', '192.168.1.109', '45.33.32.156', '检测到数据泄露行为，敏感数据被发送到外部IP', '2024-01-15 09:50:00', 'flag{security_analysis_expert_2024}');

-- ── 4. Network Sessions Table (网络会话表) ──
CREATE TABLE IF NOT EXISTS network_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    source_ip VARCHAR(50) NOT NULL,
    destination_ip VARCHAR(50) NOT NULL,
    protocol VARCHAR(20) NOT NULL,
    source_port VARCHAR(10),
    destination_port VARCHAR(10),
    start_time VARCHAR(50) NOT NULL,
    end_time VARCHAR(50),
    duration VARCHAR(20),
    packet_count INT,
    byte_count INT,
    status VARCHAR(20) NOT NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

INSERT IGNORE INTO network_sessions (id, session_id, source_ip, destination_ip, protocol, source_port, destination_port, start_time, end_time, duration, packet_count, byte_count, status) VALUES
(1, 'S001', '192.168.1.100', '192.168.1.200', 'TCP', '49152', '80', '2024-01-15 10:30:00.123456', '2024-01-15 10:30:11.000000', '10.876544s', 15, 1200, 'Closed'),
(2, 'S002', '192.168.1.100', '192.168.1.200', 'TCP', '49153', '443', '2024-01-15 10:31:00.000000', NULL, NULL, 8, 800, 'Active'),
(3, 'S003', '10.0.0.5', '10.0.0.10', 'UDP', '53', '53', '2024-01-15 10:30:01.000000', '2024-01-15 10:30:01.000123', '0.000123s', 2, 174, 'Closed');

-- ── 5. Users Table (用户表 - 用于验证) ──
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

INSERT IGNORE INTO users (id, username, password, email, role) VALUES
(1, 'admin', 'admin123', 'admin@protocol-lab.com', 'admin'),
(2, 'analyst', 'analyst2024', 'analyst@protocol-lab.com', 'user'),
(3, 'guest', 'guest', 'guest@protocol-lab.com', 'user');