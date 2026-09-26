<?php
session_start();
$error = '';
$flag = 'flag{WeakPassword_XSS_Success}'; // 定义flag内容

// 处理登录提交
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $password = trim($_POST['password'] ?? '');
    
    // 验证弱口令（admin/admin）
    if ($username === 'admin' && $password === 'year2000') {
        $_SESSION['logged_in'] = true;
        $_SESSION['username'] = $username;
    } else {
        $error = '用户名或密码错误，请重试';
    }
}

// 检查登录状态
$isLoggedIn = isset($_SESSION['logged_in']) && $_SESSION['logged_in'] === true;
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>弱口令练习挑战</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: "Microsoft YaHei", sans-serif;
    }
    body {
      background: #f5f7fa;
      color: #333;
      line-height: 1.6;
    }
    .container {
      max-width: 600px;
      margin: 50px auto;
      padding: 20px;
    }
    .title {
      font-size: 28px;
      font-weight: bold;
      margin-bottom: 30px;
      color: #000;
      border-bottom: 4px double #000;
      padding-bottom: 10px;
      text-align: center;
    }
    .login-box {
      background: #fff;
      padding: 30px;
      border-radius: 8px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    }
    .step-title {
      font-size: 20px;
      font-weight: bold;
      margin-bottom: 20px;
      color: #303133;
      text-align: center;
    }
    .target-box {
      background: #f8f9fd;
      border-left: 4px solid #faad14;
      padding: 12px 15px;
      margin: 0 0 25px 0;
      border-radius: 0 4px 4px 0;
    }
    .target-box strong {
      color: #faad14;
    }
    .input-group {
      margin-bottom: 20px;
    }
    .input-group label {
      display: block;
      margin-bottom: 8px;
      font-weight: 500;
      color: #303133;
    }
    .input-group input {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #dcdcdc;
      border-radius: 4px;
      font-size: 14px;
      transition: border-color 0.3s;
    }
    .input-group input:focus {
      border-color: #409eff;
      outline: none;
      box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
    }
    .input-group button {
      width: 100%;
      padding: 10px 20px;
      background: #409eff;
      color: #fff;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.3s;
      font-size: 14px;
    }
    .input-group button:hover {
      background: #66b1ff;
    }
    .error-message {
      color: #f5222d;
      margin-bottom: 15px;
      padding: 10px;
      background: #fff1f0;
      border: 1px solid #ffa39e;
      border-radius: 4px;
      display: none;
    }
    .error-message.active {
      display: block;
    }
    .success-box {
      background: #f0f9eb;
      border: 1px solid #b7eb8f;
      border-radius: 4px;
      padding: 20px;
      margin-top: 20px;
      text-align: center;
    }
    .success-title {
      font-weight: bold;
      font-size: 18px;
      margin-bottom: 10px;
      color: #52c41a;
    }
    .hint-btn {
      padding: 8px 15px;
      background: #f0f0f0;
      border: 1px solid #dcdcdc;
      border-radius: 4px;
      cursor: pointer;
      margin: 10px 0;
      transition: all 0.3s;
      font-size: 14px;
    }
    .hint-btn:hover {
      background: #e6e6e6;
    }
    .hint-content {
      display: none;
      padding: 15px;
      background: #fff9e6;
      border: 1px dashed #ffd666;
      border-radius: 4px;
      margin-bottom: 20px;
    }
    .skill-box {
      margin-top: 20px;
      padding: 15px;
      background: #f8f9fd;
      border-radius: 4px;
    }
    .skill-box h3 {
      font-size: 16px;
      margin-bottom: 10px;
      color: #1890ff;
    }
    .skill-box ul {
      list-style: inside;
      line-height: 1.8;
      color: #606266;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="title">弱口令练习挑战</div>
    <div class="login-box">
      <?php if (!$isLoggedIn): ?>
        <div class="step-title">管理员登录</div>
        <div class="target-box">
          <strong>当前目标：</strong>尝试使用弱口令登录管理员后台
        </div>
        <div class="error-message <?php echo $error ? 'active' : ''; ?>"><?php echo $error; ?></div>
        <form method="post">
          <div class="input-group">
            <label for="username">用户名</label>
            <input type="text" id="username" name="username" placeholder="请输入用户名" required>
          </div>
          <div class="input-group">
            <label for="password">密码</label>
            <input type="password" id="password" name="password" placeholder="请输入密码" required>
          </div>
          <div class="input-group">
            <button type="submit">登录</button>
          </div>
        </form>
        <button class="hint-btn" onclick="document.getElementById('hint').style.display = 'block'">显示提示</button>
        <div class="hint-content" id="hint">
          常见的弱口令组合有：<br>
          - 用户名和密码相同（如：admin/admin）<br>
          - 简单数字组合（如：123456）<br>
          - 空密码或默认密码<br>
          - bp还有一套密码字典，你试过吗？
        </div>
      <?php else: ?>
        <div class="success-box">
          <div class="success-title">登录成功！</div>
          <p>恭喜您成功使用弱口令登录系统</p>
          <?php 
          // 登录成功后触发XSS弹窗显示flag
          echo '<script>alert("'.$flag.'");</script>';
          ?>
        </div>
      <?php endif; ?>
      <div class="skill-box">
        <h3>弱口令安全知识</h3>
        <ul>
          <li>弱口令是指容易被猜测或破解的密码，如简单数字、常见单词等</li>
          <li>安全的密码应包含大小写字母、数字和特殊符号，长度至少8位</li>
          <li>不同网站/系统应使用不同的密码，避免"一套密码走天下"</li>
          <li>定期更换密码可以降低密码泄露后的风险</li>
        </ul>
      </div>
    </div>
  </div>
</body>
</html>