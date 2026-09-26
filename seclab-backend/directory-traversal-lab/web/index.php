<?php
session_start();

// 数据库连接
$host = getenv('DB_HOST') ?: 'db';
$dbname = getenv('DB_NAME') ?: 'traversal_lab';
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

// 处理文件下载
$file_content = '';
$file_path = '';
$success = false;

if (isset($_GET['file']) && isset($_SESSION['user'])) {
    $file = $_GET['file'];
    
    // 故意不进行路径过滤，用于实验
    $file_path = 'files/' . $file;
    
    if (file_exists($file_path) && is_readable($file_path)) {
        $file_content = file_get_contents($file_path);
        
        // 检查是否成功
        switch ($step) {
            case 1:
                // 基础目录遍历 - 读取系统文件
                if (strpos($file, '../') !== false) {
                    $success = true;
                }
                break;
            case 2:
                // 绕过路径过滤
                if (strpos($file, '..%2F') !== false || strpos($file, '....//') !== false) {
                    $success = true;
                }
                break;
            case 3:
                // 读取敏感文件
                if (strpos($file_content, 'flag{') !== false) {
                    $success = true;
                }
                break;
        }
    } else {
        $error = "文件不存在或无法访问";
    }
}

// 获取文件列表
$files = [];
if (isset($_SESSION['user'])) {
    $stmt = $pdo->query("SELECT * FROM file_records ORDER BY created_at DESC");
    $files = $stmt->fetchAll(PDO::FETCH_ASSOC);
}

// 步骤标题和说明
$steps = [
    1 => [
        'title' => '基础目录遍历 - 路径遍历',
        'desc' => '目录遍历漏洞允许攻击者访问服务器上的任意文件。尝试使用路径遍历技术读取系统文件。',
        'hint' => "尝试访问: <code>../../../etc/passwd</code>",
        'goal' => '目标：使用路径遍历读取系统文件',
        'form_label' => '文件访问'
    ],
    2 => [
        'title' => '绕过路径过滤',
        'desc' => '一些网站会过滤路径中的特殊字符，但过滤不够严格。尝试绕过路径过滤机制。',
        'hint' => "尝试使用URL编码或双点绕过: <code>..%2F..%2F..%2Fetc/passwd</code>",
        'goal' => '目标：绕过路径过滤读取系统文件',
        'form_label' => '文件访问'
    ],
    3 => [
        'title' => '敏感文件读取',
        'desc' => '目录遍历攻击的最终目标是读取敏感信息。尝试读取包含Flag的敏感文件。',
        'hint' => "尝试读取配置文件或其他敏感文件",
        'goal' => '目标：读取包含Flag的敏感文件',
        'form_label' => '敏感文件访问'
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
    <title>目录遍历漏洞实验 - 步骤 <?php echo $step; ?></title>
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
        input[type="text"], input[type="password"] {
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
        .file-item {
            border: 1px solid #475569;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            background-color: #334155;
        }
        .file-link {
            color: #38bdf8;
            text-decoration: none;
        }
        .file-link:hover {
            text-decoration: underline;
        }
        .file-content {
            background-color: #334155;
            border: 1px solid #475569;
            padding: 15px;
            border-radius: 4px;
            white-space: pre-wrap;
            font-family: monospace;
            max-height: 400px;
            overflow-y: auto;
        }
        .two-column {
            display: flex;
            gap: 20px;
        }
        .column {
            flex: 1;
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
        pre {
            background-color: #334155;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            border: 1px solid #475569;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>目录遍历漏洞实验</h1>
        
        <div class="nav">
            <a href="index.html">&larr; 返回靶机控制台</a>
        </div>
        
        <div class="warning">
            <strong>⚠️ 安全警告：</strong>这是一个用于学习目录遍历漏洞的实验环境。请勿在生产环境中使用。
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
                    <li>admin / admin123</li>
                    <li>user1 / password123</li>
                    <li>test / test123</li>
                </ul>

            <?php else: ?>
                <!-- 用户信息 -->
                <div class="user-info">
                    <h3>欢迎，<?php echo htmlspecialchars($_SESSION['user']['username']); ?>！</h3>
                    <a href="?logout=1" style="color: #ef4444;">退出登录</a>
                </div>

                <?php if ($error): ?>
                    <div class="error"><?php echo $error; ?></div>
                <?php endif; ?>

                <div class="two-column">
                    <div class="column">
                        <!-- 文件列表 -->
                        <h3>可访问的文件</h3>
                        <?php if (empty($files)): ?>
                            <p>暂无文件</p>
                        <?php else: ?>
                            <?php foreach ($files as $file): ?>
                                <div class="file-item">
                                    <strong>文件名:</strong> <?php echo htmlspecialchars($file['filename']); ?><br>
                                    <strong>路径:</strong> <?php echo htmlspecialchars($file['file_path']); ?><br>
                                    <strong>大小:</strong> <?php echo number_format($file['file_size']); ?> bytes<br>
                                    <strong>描述:</strong> <?php echo htmlspecialchars($file['description']); ?><br>
                                    <strong>访问链接:</strong> 
                                    <a href="?file=<?php echo urlencode($file['filename']); ?>&step=<?php echo $step; ?>" class="file-link">
                                        查看文件
                                    </a>
                                </div>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </div>

                    <div class="column">
                        <!-- 文件内容显示 -->
                        <?php if ($file_content !== ''): ?>
                            <h3>文件内容: <?php echo htmlspecialchars(basename($file_path)); ?></h3>
                            <div class="file-content"><?php echo htmlspecialchars($file_content); ?></div>
                        <?php endif; ?>
                    </div>
                </div>

                <?php if ($success && $step == 3): ?>
                    <div class="flag-container">
                        <h2>🏁 恭喜你完成所有挑战！</h2>
                        <p style="font-size:1.2em;color:#22d3ee;font-weight:bold;">Flag: <code>flag{directory_traversal_master_2024}</code></p>
                        <p style="color:#38bdf8;">将此Flag提交到CTF平台以获得积分</p>
                    </div>
                <?php endif; ?>

                <h3>目录遍历漏洞实验提示</h3>
                <p>尝试访问以下路径来测试目录遍历漏洞：</p>
                <ul>
                    <li><code>?file=../../../etc/passwd</code> - 读取系统用户文件</li>
                    <li><code>?file=../../../etc/hosts</code> - 读取主机文件</li>
                    <li><code>?file=../../../proc/version</code> - 读取系统版本信息</li>
                    <li><code>?file=../../../var/log/apache2/access.log</code> - 读取Apache日志</li>
                    <li><code>?file=../../../var/www/html/index.php</code> - 读取其他PHP文件</li>
                </ul>

                <h3>绕过技巧</h3>
                <ul>
                    <li>使用 <code>..%2F..%2F..%2F</code> (URL编码)</li>
                    <li>使用 <code>....//....//....//</code> (双点)</li>
                    <li>使用 <code>..%252F..%252F..%252F</code> (双重URL编码)</li>
                    <li>使用 <code>..%c0%af..%c0%af..%c0%af</code> (UTF-8编码)</li>
                </ul>

                <h3>示例攻击URL</h3>
                <pre><code>http://localhost:8095/index.php?file=../../../etc/passwd
http://localhost:8095/index.php?file=..%2F..%2F..%2Fetc%2Fpasswd
http://localhost:8095/index.php?file=....//....//....//etc/passwd</code></pre>
            <?php endif; ?>

            <div class="hint">
                <h3>提示：</h3>
                <p><?php echo $steps[$step]['hint']; ?></p>
            </div>
        </div>

        <div class="container">
            <h3>目录遍历漏洞技巧</h3>
            <p>目录遍历漏洞是一种常见的Web安全漏洞，了解以下技巧会很有帮助：</p>
            <ul>
                <li>使用 <code>../</code> 进行路径遍历</li>
                <li>使用URL编码绕过过滤</li>
                <li>使用双重编码绕过WAF</li>
                <li>读取系统配置文件获取敏感信息</li>
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