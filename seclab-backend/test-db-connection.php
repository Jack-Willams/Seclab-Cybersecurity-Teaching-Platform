<?php
// 数据库连接测试脚本
echo "=== 数据库连接测试 ===\n";

// 测试配置
$configs = [
    'xss_lab' => ['host' => 'localhost', 'port' => 8092, 'dbname' => 'xss_lab'],
    'csrf_lab' => ['host' => 'localhost', 'port' => 8093, 'dbname' => 'csrf_lab'],
    'upload_lab' => ['host' => 'localhost', 'port' => 8094, 'dbname' => 'upload_lab'],
    'traversal_lab' => ['host' => 'localhost', 'port' => 8095, 'dbname' => 'traversal_lab'],
    'sqli_lab' => ['host' => 'localhost', 'port' => 8091, 'dbname' => 'sqli_lab']
];

$username = 'root';
$password = '123456';

foreach ($configs as $lab_name => $config) {
    echo "\n测试 $lab_name:\n";
    
    try {
        // 尝试直接连接MySQL
        $pdo = new PDO("mysql:host={$config['host']};port={$config['port']};dbname={$config['dbname']};charset=utf8", $username, $password);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        
        // 测试查询
        $stmt = $pdo->query("SELECT 1 as test");
        $result = $stmt->fetch();
        
        echo "✓ 连接成功 - 端口 {$config['port']}\n";
        
    } catch (PDOException $e) {
        echo "✗ 连接失败: " . $e->getMessage() . "\n";
    }
}

echo "\n=== 测试完成 ===\n";
?> 