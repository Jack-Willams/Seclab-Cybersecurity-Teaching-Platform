-- 目录遍历实验数据库初始化脚本
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET character_set_connection=utf8mb4;

USE traversal_lab;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建文件记录表
CREATE TABLE IF NOT EXISTS file_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 插入测试数据
INSERT INTO users (username, password, email) VALUES
('admin', 'admin123', 'admin@example.com'),
('user1', 'password123', 'user1@example.com'),
('test', 'test123', 'test@example.com');

-- 插入文件记录
INSERT INTO file_records (filename, file_path, file_size, description) VALUES
('public.txt', 'files/public.txt', 1024, '公开文件'),
('secret.txt', 'files/secret.txt', 512, '秘密文件'),
('config.txt', 'files/config.txt', 256, '配置文件'); 