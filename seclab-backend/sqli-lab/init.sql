-- ByteShop SQLi Lab Database Initialization
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET character_set_connection=utf8mb4;

CREATE DATABASE IF NOT EXISTS sqli_lab;
USE sqli_lab;

-- ── 1. Users Table (5 cols: id, username, password, email, created_at) ──
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50)  NOT NULL,
    password VARCHAR(255) NOT NULL,
    email    VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

INSERT IGNORE INTO users (id, username, password, email) VALUES
(1,  'admin',      'admin123',            'admin@byteshop.com'),
(2,  'alice',      'alice2024',           'alice@byteshop.com'),
(3,  'bob',        'b0bSecure!',          'bob@byteshop.com'),
(4,  'charlie',    'charlie99',           'charlie@byteshop.com'),
(5,  'guest',      'guest',               'guest@byteshop.com'),
(999,'admin_root', 'ByteShop@Secret#2024','flag{union_sqli_pwn3d_2024} <admin_root@byteshop.internal>');

-- ── 2. Products Table (4 cols for UNION practice) ──────────────────────
CREATE TABLE IF NOT EXISTS products (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    name     VARCHAR(100)    NOT NULL,
    price    VARCHAR(20)     NOT NULL,
    category VARCHAR(50)     NOT NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

INSERT IGNORE INTO products (id, name, price, category) VALUES
(1,  'iPhone 15 Pro',        '9999.00',  'electronics'),
(2,  'MacBook Air M3',       '10999.00', 'electronics'),
(3,  'AirPods Pro 2',        '1799.00',  'electronics'),
(4,  'Nike Air Max 2024',    '899.00',   'shoes'),
(5,  'Adidas Ultraboost 23', '799.00',   'shoes'),
(6,  'Levi 501 Jeans',       '459.00',   'clothing'),
(7,  'North Face Jacket',    '1299.00',  'clothing'),
(8,  'Sony WH-1000XM5',      '2299.00',  'electronics'),
(9,  'Samsung Galaxy S24',   '7999.00',  'electronics'),
(10, 'Mechanical Keyboard',  '599.00',   'accessories');
