<?php
// 数据库连接测试页面

// 显示所有错误
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

echo "<h1>数据库连接测试</h1>";

// 数据库连接参数
$host = 'db';
$user = 'root';
$pass = '123456';
$dbname = 'sqli_lab';

echo "<h2>连接参数:</h2>";
echo "主机: $host<br>";
echo "用户: $user<br>";
echo "密码: ******<br>";
echo "数据库: $dbname<br>";

// 尝试连接
echo "<h2>连接测试:</h2>";
try {
    $conn = new mysqli($host, $user, $pass, $dbname);
    
    if ($conn->connect_error) {
        throw new Exception("连接失败: " . $conn->connect_error);
    }
    
    echo "<div style='color:green'>数据库连接成功!</div>";
    
    // 测试查询
    echo "<h2>数据库查询测试:</h2>";
    $sql = "SHOW TABLES";
    $result = $conn->query($sql);
    
    if ($result) {
        echo "<div style='color:green'>查询成功!</div>";
        echo "<h3>数据库表:</h3>";
        echo "<ul>";
        while ($row = $result->fetch_row()) {
            echo "<li>" . $row[0] . "</li>";
        }
        echo "</ul>";
        
        // 查询用户表
        $sql = "SELECT * FROM users LIMIT 5";
        $result = $conn->query($sql);
        
        if ($result) {
            echo "<h3>用户表数据:</h3>";
            echo "<table border='1'><tr><th>ID</th><th>用户名</th></tr>";
            while ($row = $result->fetch_assoc()) {
                echo "<tr><td>" . $row["id"] . "</td><td>" . $row["username"] . "</td></tr>";
            }
            echo "</table>";
        } else {
            echo "<div style='color:red'>查询用户表失败: " . $conn->error . "</div>";
        }
    } else {
        echo "<div style='color:red'>查询失败: " . $conn->error . "</div>";
    }
    
    $conn->close();
} catch (Exception $e) {
    echo "<div style='color:red'>错误: " . $e->getMessage() . "</div>";
}

// 显示主机信息
echo "<h2>主机信息:</h2>";
echo "PHP版本: " . phpversion() . "<br>";
echo "主机名: " . gethostname() . "<br>";
echo "IP地址: " . $_SERVER['SERVER_ADDR'] . "<br>";

// DNS测试
echo "<h2>DNS测试:</h2>";
echo "解析 'db' 主机名: ";
$ip = gethostbyname('db');
if ($ip != 'db') {
    echo "<div style='color:green'>成功 ($ip)</div>";
} else {
    echo "<div style='color:red'>失败 (无法解析)</div>";
}

// 网络连接测试
echo "<h2>网络连接测试:</h2>";
$fp = @fsockopen('db', 3306, $errno, $errstr, 5);
if ($fp) {
    echo "<div style='color:green'>可以连接到数据库端口 (db:3306)</div>";
    fclose($fp);
} else {
    echo "<div style='color:red'>无法连接到数据库端口: $errstr ($errno)</div>";
}
?> 