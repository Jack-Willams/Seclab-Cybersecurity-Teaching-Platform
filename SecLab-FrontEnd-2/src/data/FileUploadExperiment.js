// 文件上传漏洞实验模拟数据
export const FileUploadExperiment = {
  id: 5,
  name: '文件上传漏洞实验',
  introduction: '本实验将帮助你理解文件上传漏洞的原理、利用方式及防御措施',
  difficulty: 3,
  taskPoints: [
    {
      id: 1,
      name: '文件上传漏洞基础',
      description: '了解文件上传漏洞的基本概念和风险',
      score: 5,
      document: '## 文件上传漏洞基础\n\n文件上传漏洞是指Web应用程序在处理用户上传的文件时，由于验证或过滤不充分，导致攻击者能够上传恶意文件并执行，从而获取服务器控制权或访问敏感数据的一种安全漏洞。\n\n### 漏洞原理\n\n文件上传漏洞主要存在于允许用户上传文件的Web应用中，如论坛、社交网站、内容管理系统等。当应用程序未对上传的文件进行足够的安全检查时，攻击者可以上传具有危险功能的文件（如WebShell）。一旦这些文件被服务器接受并可访问，攻击者就能远程执行代码。\n\n### 常见风险\n\n1. **WebShell上传**：攻击者上传包含服务器端代码的文件，获取服务器控制权\n2. **XSS攻击**：上传包含恶意JavaScript的HTML或SVG文件\n3. **客户端攻击**：上传包含恶意代码的Flash或Java文件\n4. **服务器端包含(SSI)注入**：利用服务器端包含技术执行命令\n5. **文件系统访问**：通过目录遍历等技术访问服务器上的敏感文件\n\n### 常见文件类型与风险\n\n| 文件类型 | 常见扩展名 | 风险描述 |\n|---------|----------|--------|\n| PHP文件 | .php, .php5, .phtml | 可在服务器上执行任意PHP代码 |\n| ASP/ASPX文件 | .asp, .aspx | 可在Windows服务器上执行代码 |\n| JSP文件 | .jsp | 可在Java服务器上执行代码 |\n| HTML/JS文件 | .html, .js | 可执行XSS攻击 |\n| Shell脚本 | .sh, .bash | 可在Linux/Unix系统上执行命令 |\n| 可执行文件 | .exe, .dll | 可在服务器上执行任意程序 |\n| 图片文件 | .jpg, .png, .gif | 可能包含隐藏的代码(例如PHP代码嵌入EXIF数据) |',
      questions: [
        {
          id: 1,
          content: '文件上传漏洞可能导致哪些安全风险？',
          score: 2,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['服务器资源消耗', '远程代码执行', '数据库连接超时', '网络流量增加']
        },
        {
          id: 2,
          content: '以下哪种文件类型上传后可能导致服务器被控制？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['.txt文本文件', '.pdf文档文件', '.php网站脚本文件', '.csv数据文件']
        }
      ]
    },
    {
      id: 2,
      name: '文件上传漏洞利用',
      description: '学习常见的文件上传漏洞利用技术',
      score: 7,
      document: '## 文件上传漏洞利用技术\n\n在识别到目标应用存在文件上传功能后，攻击者可能使用各种技术尝试绕过安全限制并上传恶意文件。\n\n### 基本WebShell上传\n\n最直接的利用方式是上传包含服务器端脚本的文件，例如PHP WebShell:\n\n```php\n<?php\n// 简单的一句话木马\neval($_REQUEST[\'cmd\']);\n?>\n```\n\n或功能更完善的WebShell:\n\n```php\n<?php\nif(isset($_REQUEST[\'cmd\'])){\n    $cmd = $_REQUEST[\'cmd\'];\n    system($cmd);\n}\n?>\n```\n\n### 绕过文件类型验证\n\n1. **修改Content-Type**\n   - 通过拦截请求，将`Content-Type`从`application/x-php`改为`image/jpeg`\n\n2. **修改文件扩展名**\n   - 使用不常见但可执行的扩展名：`.php5`, `.phtml`, `.php.jpg`\n   - 利用服务器配置漏洞：某些服务器配置可能允许`.php.jpg`文件作为PHP执行\n\n3. **大小写混合**\n   - 某些系统区分大小写：`.PhP`, `.pHp`\n\n4. **空字节注入**\n   - 在某些语言实现中：`shell.php%00.jpg` 可能被解释为 `shell.php`\n\n### 绕过内容验证\n\n1. **图片马**\n   - 在合法图片文件中嵌入PHP代码\n   ```\n   GIF89a\n   <?php system($_GET[\'cmd\']); ?>\n   ```\n   - 在图片EXIF数据中插入代码\n\n2. **多重文件上传**\n   - 利用压缩文件上传多个文件\n   - 使用不同类型的文件组合攻击\n\n3. **文件包含组合攻击**\n   - 结合本地文件包含(LFI)漏洞:\n     1. 上传包含恶意代码的文件，如日志文件\n     2. 通过LFI漏洞包含该文件，执行代码\n\n### 后门维持\n\n成功上传WebShell后，攻击者可能：\n\n1. 创建隐藏的管理账号\n2. 安装更复杂的后门程序\n3. 设置定时任务保持访问\n4. 横向移动攻击内网其他系统',
      questions: [
        {
          id: 1,
          content: '要绕过仅检查文件扩展名的上传限制，攻击者可能使用什么技术？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['增大文件大小', '修改Content-Type头', '使用特殊字符加密文件', '将文件压缩后上传']
        },
        {
          id: 2,
          content: '以下哪种PHP代码片段最可能被用作WebShell？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['<?php phpinfo(); ?>', '<?php echo "Hello World"; ?>', '<?php system($_GET["cmd"]); ?>', '<?php $a = 1 + 1; echo $a; ?>']
        }
      ]
    },
    {
      id: 3,
      name: '文件上传漏洞防御',
      description: '学习防御文件上传漏洞的安全措施',
      score: 8,
      document: '## 文件上传漏洞防御\n\n防御文件上传漏洞需要采用多层次的安全措施，单一的防御方法通常可以被绕过。以下是一些有效的防御策略：\n\n### 1. 文件类型验证\n\n**使用白名单而非黑名单**\n```php\n// 不安全的黑名单方法\n$blacklist = array("php", "php5", "phtml");\nif(in_array($extension, $blacklist)) {\n    die("不允许上传该类型文件");\n}\n\n// 更安全的白名单方法\n$whitelist = array("jpg", "jpeg", "png", "gif");\nif(!in_array($extension, $whitelist)) {\n    die("只允许上传图片文件");\n}\n```\n\n**验证文件内容而非仅检查扩展名**\n```php\n// 检查文件的真实类型\n$finfo = finfo_open(FILEINFO_MIME_TYPE);\n$mime = finfo_file($finfo, $_FILES[\'userfile\'][\'tmp_name\']);\nfinfo_close($finfo);\n\n$allowed_types = array(\'image/jpeg\', \'image/png\', \'image/gif\');\nif (!in_array($mime, $allowed_types)) {\n    die("只允许上传图片文件");\n}\n```\n\n### 2. 文件名处理\n\n**重命名上传的文件**\n```php\n// 使用随机文件名防止覆盖和预测\n$new_filename = md5(uniqid(rand(), true)) . \'.jpg\';\n```\n\n**存储路径处理**\n```php\n// 将文件存储在网站根目录之外\n$upload_dir = "/var/www/uploads/";\n// 或使用数据库存储并通过脚本提供文件\n```\n\n### 3. 文件内容检查\n\n**扫描文件内容中的恶意代码**\n```php\n// 检查图片文件中是否包含PHP代码\n$contents = file_get_contents($_FILES[\'userfile\'][\'tmp_name\']);\nif (preg_match(\'/\\<\\?php/i\', $contents)) {\n    die("检测到恶意内容");\n}\n```\n\n**移除可能的恶意内容**\n```php\n// 对于图片，可以重新生成图片以移除隐藏代码\nif ($mime == \'image/jpeg\') {\n    $image = imagecreatefromjpeg($_FILES[\'userfile\'][\'tmp_name\']);\n    imagejpeg($image, $upload_dir . $new_filename, 90);\n    imagedestroy($image);\n} else {\n    // 处理其他允许的类型\n}\n```\n\n### 4. 文件执行权限控制\n\n**Web服务器配置**\n\nApache配置：\n```\n<Directory "/var/www/uploads">\n    php_flag engine off\n    Options -Indexes -ExecCGI\n    AddHandler default-handler .php .php5 .phtml\n</Directory>\n```\n\nNginx配置：\n```\nlocation /uploads {\n    location ~ \\.php$ {\n        deny all;\n    }\n}\n```\n\n**使用不同域或CDN提供上传的文件**\n\n将用户上传的文件存储在单独的域或CDN上，与主应用程序分离。\n\n### 5. 其他安全措施\n\n**文件大小限制**\n```php\nif ($_FILES[\'userfile\'][\'size\'] > 1000000) {\n    die("文件大小超过限制");\n}\n```\n\n**文件上传速率限制**\n\n防止DoS攻击和批量上传恶意文件。\n\n**使用第三方存储服务**\n\n考虑使用Amazon S3等第三方存储服务，它们通常有额外的安全措施。\n\n**定期扫描上传目录**\n\n使用安全扫描工具定期检查上传目录，查找可能的恶意文件。\n\n### 最佳实践总结\n\n1. 组合多种验证方法\n2. 使用白名单方法验证文件类型\n3. 检查文件内容，而不只是扩展名\n4. 重命名上传的文件，使用不可预测的名称\n5. 存储文件在安全位置，最好在网站根目录外\n6. 限制上传目录的执行权限\n7. 使用适当的文件权限\n8. 考虑使用单独的域或CDN\n9. 实施文件大小和上传频率限制',
      questions: [
        {
          id: 1,
          content: '防御文件上传漏洞时，关于文件类型验证的最佳做法是什么？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['使用黑名单禁止危险文件类型', '使用白名单限制允许的文件类型', '完全禁止文件上传功能', '只允许上传加密文件']
        },
        {
          id: 2,
          content: '以下哪个措施能有效防止上传的PHP文件被执行？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['将上传的文件重命名为.txt', '在上传目录中禁用PHP引擎', '将所有上传文件设为只读', '定期删除上传文件']
        }
      ]
    },
    {
      id: 4,
      name: '文件上传漏洞实例',
      description: '分析真实的文件上传漏洞案例',
      score: 10,
      document: '## 文件上传漏洞实例分析\n\n通过分析实际的文件上传漏洞案例，我们可以更深入地理解攻击手法和防御策略。\n\n### 案例一：简单的文件类型验证绕过\n\n**漏洞代码：**\n\n```php\n<?php\n// 文件上传处理脚本\n$uploaddir = \'uploads/\';\n$uploadfile = $uploaddir . basename($_FILES[\'userfile\'][\'name\']);\n\n// 检查文件扩展名\n$ext = pathinfo($_FILES[\'userfile\'][\'name\'], PATHINFO_EXTENSION);\nif($ext != "jpg" && $ext != "jpeg" && $ext != "png" && $ext != "gif") {\n    echo "只允许上传图片文件!";\n    exit();\n}\n\n// 检查Content-Type\nif($_FILES[\'userfile\'][\'type\'] != "image/jpeg" && \n   $_FILES[\'userfile\'][\'type\'] != "image/png" && \n   $_FILES[\'userfile\'][\'type\'] != "image/gif") {\n    echo "只允许上传图片文件!";\n    exit();\n}\n\nif (move_uploaded_file($_FILES[\'userfile\'][\'tmp_name\'], $uploadfile)) {\n    echo "文件上传成功\\n";\n} else {\n    echo "上传失败!\\n";\n}\n?>\n```\n\n**攻击方法：**\n\n1. 攻击者创建一个包含PHP代码的文件 `shell.php.jpg`\n2. 使用Burp Suite等工具拦截上传请求\n3. 修改文件名为 `shell.php`\n4. 修改Content-Type为 `image/jpeg`\n5. 服务器接受了这个看似是图片实为PHP的文件\n6. 攻击者现在可以访问并执行上传的PHP文件\n\n**防御改进：**\n\n```php\n<?php\n// 改进的文件上传处理脚本\n$uploaddir = \'uploads/\';\n\n// 生成随机文件名\n$new_filename = md5(uniqid(rand(), true));\n\n// 检查文件真实类型\n$finfo = finfo_open(FILEINFO_MIME_TYPE);\n$file_mime = finfo_file($finfo, $_FILES[\'userfile\'][\'tmp_name\']);\nfinfo_close($finfo);\n\n// 白名单检查\n$allowed_types = array(\'image/jpeg\', \'image/png\', \'image/gif\');\nif(!in_array($file_mime, $allowed_types)) {\n    echo "只允许上传图片文件!";\n    exit();\n}\n\n// 基于MIME类型设置正确的扩展名\n$extensions = array(\n    \'image/jpeg\' => \'.jpg\',\n    \'image/png\' => \'.png\',\n    \'image/gif\' => \'.gif\'\n);\n$ext = $extensions[$file_mime];\n\n// 完整的新文件名\n$uploadfile = $uploaddir . $new_filename . $ext;\n\n// 检查文件内容\n$file_content = file_get_contents($_FILES[\'userfile\'][\'tmp_name\']);\nif(preg_match("/<\\?php|eval\\(|system\\(|exec\\(/i", $file_content)) {\n    echo "检测到潜在危险内容!";\n    exit();\n}\n\n// 重新生成图片以移除潜在的恶意代码\nif($file_mime == \'image/jpeg\') {\n    $image = imagecreatefromjpeg($_FILES[\'userfile\'][\'tmp_name\']);\n    if(!$image) {\n        echo "无效的图片文件!\\n";\n        exit();\n    }\n    imagejpeg($image, $uploadfile, 90);\n    imagedestroy($image);\n}\nelseif($file_mime == \'image/png\') {\n    $image = imagecreatefrompng($_FILES[\'userfile\'][\'tmp_name\']);\n    if(!$image) {\n        echo "无效的图片文件!\\n";\n        exit();\n    }\n    imagepng($image, $uploadfile, 9);\n    imagedestroy($image);\n}\nelseif($file_mime == \'image/gif\') {\n    $image = imagecreatefromgif($_FILES[\'userfile\'][\'tmp_name\']);\n    if(!$image) {\n        echo "无效的图片文件!\\n";\n        exit();\n    }\n    imagegif($image, $uploadfile);\n    imagedestroy($image);\n}\n\necho "文件上传成功，保存为: " . basename($uploadfile) . "\\n";\n?>\n```\n\n### 案例二：.htaccess文件上传攻击\n\n**攻击方法：**\n\n1. 攻击者上传自定义的.htaccess文件\n2. .htaccess包含以下内容：\n   ```\n   AddType application/x-httpd-php .jpg\n   ```\n3. 此配置使服务器将.jpg文件作为PHP文件处理\n4. 攻击者随后上传包含PHP代码的图片文件\n5. 服务器将该图片作为PHP代码执行\n\n**防御方法：**\n\n1. 禁止上传.htaccess和其他配置文件\n2. 在服务器全局配置中禁用对上传目录的.htaccess支持\n   ```\n   <Directory "/var/www/uploads">\n       AllowOverride None\n   </Directory>\n   ```\n\n### 案例三：文件包含漏洞结合\n\n**攻击场景：**\n\n1. 网站存在文件包含漏洞：\n   ```php\n   <?php include($_GET[\'page\'] . ".php"); ?>\n   ```\n\n2. 网站允许上传文件，但禁止PHP扩展名\n\n3. 攻击者上传包含PHP代码的图片文件 `evil.jpg`\n\n4. 攻击者利用空字节注入：\n   ```\n   http://example.com/?page=uploads/evil.jpg%00\n   ```\n\n5. PHP解释器读取到空字节前的内容，实际包含的是 `uploads/evil.jpg`\n\n**防御方法：**\n\n1. 修复文件包含漏洞，使用白名单：\n   ```php\n   <?php\n   $allowed_pages = array("home", "about", "contact");\n   if(in_array($_GET[\'page\'], $allowed_pages)) {\n       include($_GET[\'page\'] . ".php");\n   } else {\n       include("home.php");\n   }\n   ?>\n   ```\n\n2. 更新PHP版本（PHP 5.3.4及更高版本已修复空字节注入漏洞）',
      questions: [
        {
          id: 1,
          content: '在案例一中，攻击者是如何绕过文件类型验证的？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['使用自动化工具批量上传文件', '修改文件名和Content-Type', '利用SQL注入漏洞', '破解服务器密码后直接上传文件']
        },
        {
          id: 2,
          content: '在案例二中，攻击者上传.htaccess文件的目的是什么？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['绕过登录验证', '修改服务器时间', '使服务器将图片文件当作PHP执行', '删除服务器上的其他文件']
        }
      ]
    },
    {
      id: 5,
      name: '文件上传漏洞实验环境',
      description: '在靶机环境中实践文件上传漏洞的识别和利用',
      score: 10,
      document: `# 文件上传漏洞实验环境

## 实验简介

本实验环境提供了一个简单的图片上传网站，你将在这个环境中学习如何识别和利用文件上传漏洞，以及了解如何防御此类漏洞。

**注意：本实验环境仅用于教育目的。** 所有操作都在受控环境中进行，这些技术在未经授权的情况下使用是违法的。

## 实验目标

1. 理解文件上传漏洞的原理
2. 学习常见的文件上传限制绕过技术
3. 掌握文件上传漏洞的利用方法
4. 了解文件上传漏洞的防御措施

## 实验环境说明

实验环境包含：
- 一个图片分享网站，允许用户上传图片
- 具有不同安全级别的上传功能
- 一个隐藏在服务器中的flag文件

## 实验步骤

### 第一步：了解上传功能

1. 访问实验网站，熟悉图片上传功能
2. 尝试上传正常的图片文件（jpg, png, gif）
3. 观察上传后文件的存储位置和访问URL

### 第二步：分析安全限制

1. 尝试上传非图片文件，如.txt或.html文件
2. 观察网站的响应和错误信息
3. 分析网站可能实施的安全检查（扩展名检查、MIME类型检查等）

### 第三步：绕过安全限制

根据发现的安全措施，尝试以下技术：

1. **文件扩展名绕过**
   - 尝试使用不同的扩展名组合（如shell.php.jpg）
   - 尝试大小写混合（如shell.pHP）

2. **MIME类型绕过**
   - 使用Burp Suite等工具修改请求中的Content-Type

3. **内容检查绕过**
   - 在图片文件中嵌入PHP代码
   - 使用图片马（在合法图片中包含PHP代码）

### 第四步：利用上传的WebShell

1. 成功上传WebShell后，访问该文件
2. 使用WebShell执行系统命令
3. 寻找并读取flag文件的内容

## 实验小贴士

- 有时候服务器端的检查可能与客户端的检查不同
- 观察上传的文件如何被处理和存储可以提供有价值的线索
- 如果一种绕过技术失败，不要气馁，尝试组合多种技术
- 记住查看服务器返回的错误信息，可能包含有用的提示

## 实验评分标准

实验评分基于以下几个方面：
1. 成功识别文件上传限制（3分）
2. 成功绕过上传限制并上传WebShell（3分）
3. 成功利用WebShell获取flag（4分）

## 安全提醒

请记住：
- 文件上传漏洞利用在未授权的实际系统上是违法的
- 负责任地披露发现的漏洞
- 将所学知识用于构建更安全的应用程序

现在，开始你的实验吧！`,
      questions: [
        {
          id: 1,
          content: '请描述文件上传漏洞的基本原理 (在本前端模拟实验的上下文中)',
          score: 3,
          requiresTarget: false,
          type: 'open-ended-without-answer'
        },
        {
          id: 2,
          content: "以下哪种方法最可能成功绕过仅检查文件扩展名的上传限制？",
          score: 3,
          requiresTarget: false,
          type: 'single-choice',
          options: ["添加更多数据使文件变大", "修改浏览器User-Agent", "将PHP文件重命名为shell.php.jpg然后在上传请求中改回shell.php", "压缩文件后上传"]
        },
        {
          id: 3,
          content: '请描述你成功上传WebShell并获取flag的过程。写出你使用的技术、上传的文件内容以及发现的flag值。',
          score: 4,
          requiresTarget: false,
          type: 'open-ended-with-answer'
        }
      ]
    }
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440004'
  }
}; 