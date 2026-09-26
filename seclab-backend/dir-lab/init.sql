-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS dir_lab;
USE dir_lab;

-- 创建文件访问记录表
CREATE TABLE IF NOT EXISTS file_access (
  id INT AUTO_INCREMENT PRIMARY KEY,
  file_path VARCHAR(255) NOT NULL,
  access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ip_address VARCHAR(45) DEFAULT NULL
);

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL,
  email VARCHAR(100) DEFAULT NULL,
  password VARCHAR(32) DEFAULT NULL
);

-- 插入测试用户数据
INSERT INTO users (username, email, password) VALUES 
('admin', 'admin@example.com', 'e10adc3949ba59abbe56e057f20f883e'), -- 密码: 123456
('guest', 'guest@example.com', '084e0343a0486ff05530df6c705c8bb4'), -- 密码: guest
('testuser', 'test@example.com', '098f6bcd4621d373cade4e832627b4f6'); -- 密码: test 