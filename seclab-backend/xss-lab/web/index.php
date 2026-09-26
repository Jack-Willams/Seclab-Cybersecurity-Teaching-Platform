<?php
session_start();

// 数据库连接
$host = getenv('DB_HOST') ?: 'db';
$dbname = getenv('DB_NAME') ?: 'xss_lab';
$username = getenv('DB_USER') ?: 'root';
$password = getenv('DB_PASS') ?: '123456';

try {
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch(PDOException $e) {
    die("连接失败: " . $e->getMessage());
}

// 步骤控制变量
$step = isset($_GET['step']) ? intval($_GET['step']) : 1;
if ($step < 1) $step = 1;
if ($step > 3) $step = 3;

// 处理留言提交
$success = false;
$input = '';
$message = '';

if ($_POST && isset($_POST['username']) && isset($_POST['message'])) {
    $username = $_POST['username'];
    $message = $_POST['message'];
    $input = $message;
    
    // 这里故意不进行XSS过滤，用于实验
    $stmt = $pdo->prepare("INSERT INTO messages (username, message) VALUES (?, ?)");
    $stmt->execute([$username, $message]);
    
    // 检查是否成功
    switch ($step) {
        case 1:
            // 基础XSS - 弹窗
            if (strpos($message, '<script>') !== false && strpos($message, 'alert') !== false) {
                $success = true;
            }
            break;
        case 2:
            // 图片XSS
            if (strpos($message, '<img') !== false && strpos($message, 'onerror') !== false) {
                $success = true;
            }
            break;
        case 3:
            // Cookie窃取
            if (strpos($message, 'document.cookie') !== false) {
                $success = true;
            }
            break;
    }
    
    header("Location: index.php?step=$step&success=" . ($success ? '1' : '0') . "&input=" . urlencode($input));
    exit();
}

// 获取所有留言
$stmt = $pdo->query("SELECT * FROM messages ORDER BY created_at DESC");
$messages = $stmt->fetchAll(PDO::FETCH_ASSOC);

// 步骤标题和说明
$steps = [
    1 => [
        'title' => '基础XSS - 弹窗攻击',
        'desc' => '跨站脚本攻击（XSS）是一种注入攻击，攻击者可以在网页中插入恶意脚本。尝试使用JavaScript弹窗来验证XSS漏洞。',
        'hint' => "尝试输入: <code>&lt;script&gt;alert('XSS')&lt;/script&gt;</code>",
        'goal' => '目标：在留言中插入JavaScript弹窗代码',
        'form_label' => '留言内容'
    ],
    2 => [
        'title' => '图片XSS - 事件处理器',
        'desc' => '使用HTML标签的事件处理器属性来执行JavaScript代码。img标签的onerror事件可以在图片加载失败时触发。',
        'hint' => "尝试输入: <code>&lt;img src=x onerror=alert('XSS')&gt;</code>",
        'goal' => '目标：使用img标签的onerror事件执行JavaScript',
        'form_label' => '留言内容'
    ],
    3 => [
        'title' => 'Cookie窃取 - 数据泄露',
        'desc' => 'XSS攻击可以用来窃取用户的敏感信息，如Cookie。尝试构造一个能够窃取Cookie的恶意脚本。',
        'hint' => "尝试输入: <code>&lt;script&gt;alert(document.cookie)&lt;/script&gt;</code>",
        'goal' => '目标：构造窃取Cookie的XSS代码',
        'form_label' => '留言内容'
    ]
];

// 检查是否成功
if (isset($_GET['success'])) {
    $success = $_GET['success'] == '1';
    $input = isset($_GET['input']) ? $_GET['input'] : '';
}
?>

<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XSS跨站脚本攻击实验 - 步骤 <?php echo $step; ?></title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #0f172a;
            color: #e2e8f0;
        }
        .container {
            background: #1e293b;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            margin-bottom: 20px;
        }
        h1 {
            color: #38bdf8;
            text-align: center;
            margin-bottom: 30px;
        }
        h2 {
            color: #22d3ee;
            border-bottom: 2px solid #38bdf8;
            padding-bottom: 10px;
        }
        .step-navigation {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .btn {
            background-color: #64748b;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            text-align: center;
            flex: 1;
            margin: 0 5px;
            transition: background-color 0.3s;
        }
        .btn:hover {
            background-color: #38bdf8;
        }
        .btn.active {
            background-color: #2563eb;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #94a3b8;
        }
        input[type="text"], textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #475569;
            border-radius: 4px;
            box-sizing: border-box;
            background-color: #334155;
            color: #e2e8f0;
        }
        button {
            background-color: #38bdf8;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background-color: #2563eb;
        }
        .message {
            border: 1px solid #475569;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            background-color: #334155;
        }
        .message-header {
            font-weight: bold;
            color: #38bdf8;
            margin-bottom: 5px;
        }
        .message-content {
            color: #cbd5e1;
        }
        .message-time {
            font-size: 12px;
            color: #64748b;
            margin-top: 5px;
        }
        .warning {
            background-color: #dc2626;
            border: 1px solid #ef4444;
            color: #fecaca;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .goal-box {
            background-color: rgba(59, 130, 246, 0.1);
            border-left: 4px solid #38bdf8;
            padding: 12px;
            margin: 16px 0;
            font-weight: bold;
        }
        .success-message {
            background-color: rgba(16, 185, 129, 0.1);
            border-left: 4px solid #10b981;
            padding: 15px;
            margin: 16px 0;
            animation: fadeIn 0.5s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .hint {
            background-color: rgba(245, 158, 11, 0.1);
            border-left: 4px solid #f59e0b;
            padding: 12px;
            margin: 16px 0;
        }
        .nav {
            margin-bottom: 20px;
        }
        .nav a {
            color: #38bdf8;
            text-decoration: none;
        }
        .nav a:hover {
            text-decoration: underline;
        }
        .flag-container {
            background-color: #1a1e2e;
            border: 2px solid #38bdf8;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
            text-align: center;
            animation: glow 2s infinite alternate;
        }
        @keyframes glow {
            from { box-shadow: 0 0 5px #38bdf8; }
            to { box-shadow: 0 0 20px #38bdf8; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>XSS跨站脚本攻击实验</h1>
        
        <div class="nav">
            <a href="index.html">&larr; 返回靶机控制台</a>
        </div>
        
        <div class="warning">
            <strong>⚠️ 安全警告：</strong>这是一个用于学习XSS漏洞的实验环境。请勿在生产环境中使用。
        </div>

        <!-- 步骤导航 -->
        <div class="step-navigation">
            <?php foreach ([1,2,3] as $i): ?>
                <a href="?step=<?php echo $i; ?>" class="btn <?php echo $i == $step ? 'active' : ''; ?>">第<?php echo $i; ?>步</a>
            <?php endforeach; ?>
        </div>

        <div class="container">
            <h2><?php echo $steps[$step]['title']; ?></h2>
            <p><?php echo $steps[$step]['desc']; ?></p>

            <div class="goal-box">
                <?php echo $steps[$step]['goal']; ?>
            </div>

            <?php if ($success && $step < 3): ?>
                <div class="success-message">
                    <h3>🎓 挑战成功！</h3>
                    <p>恭喜！你成功完成了本步骤的挑战。</p>
                    <a href="?step=<?php echo $step + 1; ?>" class="btn">继续下一步</a>
                </div>
            <?php endif; ?>

            <h3>留言板</h3>
            <form method="POST" action="?step=<?php echo $step; ?>">
                <div class="form-group">
                    <label for="username">用户名:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="message"><?php echo $steps[$step]['form_label']; ?>:</label>
                    <textarea id="message" name="message" rows="4" required><?php echo htmlspecialchars($input); ?></textarea>
                </div>
                <button type="submit">提交留言</button>
            </form>

            <h3>留言列表</h3>
            <?php if (empty($messages)): ?>
                <p>暂无留言</p>
            <?php else: ?>
                <?php foreach ($messages as $message): ?>
                    <div class="message">
                        <div class="message-header"><?php echo htmlspecialchars($message['username']); ?></div>
                        <div class="message-content"><?php echo $message['message']; ?></div>
                        <div class="message-time"><?php echo $message['created_at']; ?></div>
                    </div>
                <?php endforeach; ?>
            <?php endif; ?>

            <?php if ($success && $step == 3): ?>
                <div class="flag-container">
                    <h2>🏁 恭喜你完成所有挑战！</h2>
                    <p style="font-size:1.2em;color:#22d3ee;font-weight:bold;">Flag: <code>flag{xss_master_2024}</code></p>
                    <p style="color:#38bdf8;">将此Flag提交到CTF平台以获得积分</p>
                </div>
            <?php endif; ?>

            <div class="hint">
                <h3>提示：</h3>
                <p><?php echo $steps[$step]['hint']; ?></p>
            </div>
        </div>

        <div class="container">
            <h3>XSS攻击技巧</h3>
            <p>XSS（跨站脚本攻击）是一种常见的Web安全漏洞，了解以下技巧会很有帮助：</p>
            <ul>
                <li>使用 <code>&lt;script&gt;</code> 标签执行JavaScript代码</li>
                <li>使用HTML事件处理器如 <code>onerror</code>、<code>onload</code>、<code>onclick</code></li>
                <li>使用 <code>document.cookie</code> 窃取用户Cookie</li>
                <li>使用 <code>document.location</code> 重定向到恶意网站</li>
            </ul>
        </div>
    </div>
</body>
</html> 