<?php
// 处理跨域和编码
header("Content-Type: text/plain; charset=utf-8");

if (isset($_POST['step'])) {
    $step = $_POST['step'];
    $ip = $_POST['ip'] ?? '';
    
    // 根据步骤执行不同的命令（保持原有逻辑）
    $cmd = "ping " . $ip;
    // 执行命令并捕获输出
    ob_start(); // 开始输出缓冲
    system($cmd);
    $output = ob_get_clean(); // 获取缓冲的输出内容
    echo $output; // 返回结果给前端
}

// 处理flag验证
if (isset($_POST['action']) && $_POST['action'] === 'verifyFlag') {
    $userFlag = $_POST['flagInput'] ?? '';
    // 读取正确的flag
    ob_start();
    system('cat /flag');
    $correctFlag = trim(ob_get_clean());
    
    if ($userFlag === $correctFlag) {
        echo "flag正确！";
    } else {
        echo "flag错误，请重新尝试。";
    }
}
?>
