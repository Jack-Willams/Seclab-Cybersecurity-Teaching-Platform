// SQL注入实验模拟数据
export const SQLInjectionExperiment = {
  id: 1,
  name: 'SQL注入基础实验',
  introduction: '本实验将帮助你理解SQL注入漏洞的原理和基本利用方法',
  difficulty: 3,
  taskPoints: [
    {
      id: 1,
      name: '基础SQL语法',
      description: '学习基本SQL查询语句结构和语法，为理解注入打下基础',
      score: 5,
      document:
        '## SQL基础语法\n\n在开始学习SQL注入之前，首先需要理解基本的SQL语法结构。SQL(Structured Query Language)是一种用于管理关系型数据库的标准化语言。\n\n### 基本SQL语句\n\n1. **SELECT语句** - 用于从数据库中检索数据\n```sql\nSELECT 列名 FROM 表名 WHERE 条件;\n```\n\n2. **INSERT语句** - 用于向数据库添加新记录\n```sql\nINSERT INTO 表名 (列1, 列2) VALUES (值1, 值2);\n```\n\n3. **UPDATE语句** - 用于修改数据库中的记录\n```sql\nUPDATE 表名 SET 列名=新值 WHERE 条件;\n```\n\n4. **DELETE语句** - 用于删除数据库中的记录\n```sql\nDELETE FROM 表名 WHERE 条件;\n```\n\n了解这些基础语法对于理解SQL注入的工作原理至关重要。',
      questions: [
        {
          id: 1,
          content: '以下哪个是用于从数据库获取数据的SQL语句？',
          score: 2,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['INSERT', 'SELECT', 'UPDATE', 'DELETE'],
          answer: [1] // SELECT
        },
        {
          id: 2,
          content: 'WHERE子句在SQL查询中的作用是什么？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['指定要检索的列', '指定要查询的表', '过滤满足特定条件的行', '对结果进行排序'],
          answer: [2] // 过滤满足特定条件的行
        }
      ]
    },
    {
      id: 2,
      name: '数据库类型识别',
      description: '学习如何识别不同类型数据库的特征和指纹信息',
      score: 7,
      document:
        '## 数据库类型识别\n\n在进行SQL注入之前，识别目标系统使用的数据库类型是非常重要的，因为不同类型的数据库有不同的语法和特性。\n\n### 常见数据库类型识别方法\n\n1. **错误信息分析**\n当网站显示数据库错误时，错误信息中通常包含数据库类型的线索。\n\n2. **版本注释语法**\n不同数据库的注释语法不同：\n- MySQL: `-- 注释` 或 `#注释`\n- SQL Server: `-- 注释` 或 `/*注释*/`\n- Oracle: `-- 注释`\n- PostgreSQL: `-- 注释` 或 `/*注释*/`\n\n3. **内置函数差异**\n不同数据库的函数名不同：\n- MySQL: `version()`, `user()`\n- SQL Server: `@@version`, `system_user`\n- Oracle: `v$version`, `user`\n- PostgreSQL: `version()`, `current_user`\n\n通过测试这些函数，可以确定数据库类型。',
      questions: [
        {
          id: 1,
          content: 'MySQL数据库中获取版本信息的函数是？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['@@version', 'version()', 'getVersion()', 'v$version'],
          answer: [0] // @@version
        },
        {
          id: 2,
          content: '以下哪种注释语法是MySQL特有的？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['-- 注释', '/* 注释 */', '# 注释', '// 注释'],
          answer: [0] // -- 注释
        }
      ]
    },
    {
      id: 3,
      name: '注入点检测方法',
      description: '掌握常见注入点检测技术和错误信息分析方法',
      score: 8,
      document:
        "## 注入点检测方法\n\n找到可能存在SQL注入漏洞的输入点是成功利用该漏洞的第一步。\n\n### 常用检测方法\n\n1. **单引号测试**\n在输入中添加单引号`'`，如果返回数据库错误，则可能存在注入点。\n\n2. **逻辑测试**\n使用`AND 1=1`和`AND 1=2`进行测试。如果前者返回正常结果而后者返回异常或无结果，则可能存在注入点。\n\n3. **时间延迟测试**\n使用`SLEEP()`或`pg_sleep()`等函数测试是否可以控制响应时间，尤其适用于盲注场景。\n\n4. **错误信息分析**\n仔细分析错误信息中的数据库类型、表名、列名等信息，为后续注入提供线索。",
      questions: [
        {
          id: 1,
          content: '以下哪种方法最适合用来初步判断是否存在SQL注入漏洞？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['输入大量随机字符', '尝试输入单引号', '使用JavaScript代码', '修改HTTP头信息'],
          answer: [1] // 尝试输入单引号
        },
        {
          id: 2,
          content: '使用`AND 1=2`进行注入测试，预期的结果是什么？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['返回所有记录', '返回第一条记录', '返回错误信息', '不返回任何记录'],
          answer: [3] // 不返回任何记录
        }
      ]
    },
    {
      id: 4,
      name: '理解SQL注入原理',
      description: '学习SQL注入的基本概念和攻击原理',
      score: 10,
      document:
        '## SQL注入的背景和基本操作\n' +
        '\n' +
        '### 背景\n' +
        '\n' +
        '在互联网应用早期，开发者为了快速开发和方便操作数据库，常常直接将用户输入的数据拼接进SQL查询语句中。 这种做法在当时看似便捷，但随着网络安全意识的提升，人们逐渐意识到这种方式存在巨大的安全隐患，这就是 **SQL注入漏洞** 的根源。\n' +
        '\n' +
        '**核心问题：**  开发者**信任**并直接使用了用户输入的数据来构建SQL查询，而没有对这些数据进行充分的 **安全过滤和转义**。\n' +
        '\n' +
        '**想象一下一个场景：**\n' +
        '\n' +
        '你正在访问一个网站，网站有一个登录页面，需要你输入用户名和密码。网站后端可能会用类似这样的SQL语句来验证你的身份：\n' +
        '\n' +
        '```sql\n' +
        "SELECT * FROM users WHERE username = '你输入的用户名' AND password = '你输入的密码';\n" +
        '```\n' +
        '\n' +
        '如果开发者没有对 "你输入的用户名" 和 "你输入的密码" 进行安全处理，那么攻击者就可以利用这一点，构造特殊的输入，改变原本SQL语句的含义，从而达到非法目的。\n' +
        '\n' +
        '### 基本操作原理\n' +
        '\n' +
        'SQL注入的本质就是 **欺骗数据库服务器**，让它执行攻击者预期的恶意SQL代码，而不是开发者原本设定的查询逻辑。\n' +
        '\n' +
        '**攻击流程通常包括以下步骤：**\n' +
        '\n' +
        '1. **寻找注入点：** 攻击者首先需要找到应用程序中哪些地方接受用户输入，并且这些输入会被拼接到SQL查询语句中。常见的注入点包括：\n' +
        '    * **Web表单:**  例如登录表单、搜索框、注册表单等。\n' +
        '    * **URL参数:**  例如 `http://example.com/products.php?id=1` 中的 `id` 参数。\n' +
        '    * **HTTP头:**  例如 `User-Agent`、`Cookie` 等。\n' +
        '\n' +
        '2. **判断注入类型和漏洞：**  找到注入点后，攻击者会尝试输入一些特殊字符或SQL语句，观察应用程序的反应（例如错误信息、页面内容变化），以此来判断是否存在SQL注入漏洞，并尝试确定漏洞的类型（例如数字型、字符型、搜索型等）。\n' +
        '\n' +
        '3. **构造恶意SQL语句：**  根据注入点和漏洞类型，攻击者开始构造恶意的SQL语句。 常见的攻击目标包括：\n' +
        '    * **绕过身份验证:**  例如在登录页面，通过注入SQL语句绕过用户名和密码验证。\n' +
        '    * **获取敏感数据:**  例如查询数据库中的用户表、订单表等敏感信息。\n' +
        '    * **修改或删除数据:**  例如修改用户信息、删除订单数据等。\n' +
        '    * **执行系统命令:**  在某些情况下，攻击者甚至可以利用SQL注入漏洞执行操作系统命令，完全控制服务器。\n' +
        '\n' +
        '**一个简单的SQL注入例子 (针对字符型注入点)：**\n' +
        '\n' +
        '假设有如下易受攻击的 PHP 代码：\n' +
        '\n' +
        '```php\n' +
        '<?php\n' +
        "$username = $_GET['username'];\n" +
        '$query = "SELECT * FROM users WHERE username = \'$username\'";\n' +
        '// ... 执行查询 ...\n' +
        '?>\n' +
        '```\n' +
        '\n' +
        '如果攻击者在 URL 中输入：\n' +
        '\n' +
        "`http://example.com/vulnerable.php?username=admin' OR '1'='1`\n" +
        '\n' +
        '那么拼接后的 SQL 语句会变成：\n' +
        '\n' +
        '```sql\n' +
        "SELECT * FROM users WHERE username = 'admin' OR '1'='1'\n" +
        '```\n' +
        '\n' +
        "由于 `OR '1'='1'` 永远为真，这条 SQL 语句会返回 `users` 表中所有的数据，即使攻击者不知道 `admin` 用户的密码，也能绕过身份验证，获取所有用户信息。\n" +
        '\n' +
        '**更进一步的例子 (获取数据库版本信息)：**\n' +
        '\n' +
        '攻击者可以在 `username` 参数中注入如下语句：\n' +
        '\n' +
        "`http://example.com/vulnerable.php?username=admin' UNION SELECT version() --`\n" +
        '\n' +
        '拼接后的 SQL 语句可能变成 (取决于数据库类型)：\n' +
        '\n' +
        '```sql\n' +
        "SELECT * FROM users WHERE username = 'admin' UNION SELECT version() --'\n" +
        '```\n' +
        '\n' +
        '`UNION SELECT version()` 会将数据库版本信息作为结果集返回，攻击者就可以从中获取数据库类型和版本信息，为后续更深入的攻击做准备。 `--` 是 SQL 的注释符，用于注释掉后面的语句，防止语法错误。\n' +
        '\n' +
        '###  总结\n' +
        '\n' +
        'SQL注入是一种利用应用程序对用户输入处理不当，将恶意SQL代码注入到数据库查询语句中，从而达到非法目的的网络攻击手段。  理解其背景和基本操作原理，是防范SQL注入攻击的第一步。\n',
      questions: [
        {
          id: 1,
          content: 'SQL注入漏洞产生的根本原因是？',
          score: 2,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['数据库软件本身存在漏洞', '操作系统安全配置不足', '应用程序未对用户输入进行充分的安全处理', '网络防火墙配置不当'],
          answer: [2] // 应用程序未对用户输入进行充分的安全处理
        },
        {
          id: 2,
          content: '以下哪个是SQL注入攻击的主要目标？',
          score: 1,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['数据库服务器', 'Web服务器', '客户端浏览器', '操作系统'],
          answer: [0] // 数据库服务器
        },
        {
          id: 3,
          content: '攻击者通过SQL注入可以实现以下哪些目的？',
          score: 1,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['绕过身份验证', '获取数据库敏感数据', '修改或删除数据库数据', '以上所有'],
          answer: [0, 1, 2, 3] // 以上所有
        },
        {
          id: 4,
          content: '在URL参数 `http://example.com/products.php?id=1` 中，哪个部分最有可能成为SQL注入的注入点？',
          score: 1,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['http://example.com', 'products.php', '?', 'id=1'],
          answer: [2] // ?
        },
        {
          id: 5,
          content: '为了有效防止SQL注入，开发者应该采取的主要措施是？',
          score: 2,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['使用强密码', '使用参数化查询 (或预编译语句)', '安装防火墙', '定期备份数据'],
          answer: [1] // 使用参数化查询 (或预编译语句)
        },
        {
          id: 6,
          content: '以下哪种SQL注入类型是利用 `UNION` 关键字来合并查询结果的？',
          score: 1,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['盲注 (Blind SQL Injection)', '联合查询注入 (Union-based SQL Injection)', '报错注入 (Error-based SQL Injection)', '布尔盲注 (Boolean-based Blind SQL Injection)'],
          answer: [1] // 联合查询注入 (Union-based SQL Injection)
        },
        {
          id: 7,
          content: '在SQL注入语句中，`--` 的作用是？',
          score: 1,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['执行SQL语句', '注释掉后面的SQL语句', '分隔SQL语句', '定义变量'],
          answer: [1] // 注释掉后面的SQL语句
        },
        {
          id: 8,
          content: "如果在一个登录表单的用户名输入框中输入 `' OR '1'='1 --`，最有可能发生的情况是？",
          score: 1,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['网站崩溃', '成功绕过登录验证', '账号被锁定', '输入被视为普通的用户名'],
          answer: [1] // 成功绕过登录验证
        }
      ]
    },
    {
      id: 5,
      name: 'SQL注入防御技术',
      description: '了解参数化查询、ORM和输入验证等防御SQL注入的方法',
      score: 10,
      document:
        '## SQL注入防御技术\n\n防御SQL注入攻击是web应用安全中的重要环节。以下是几种主要的防御技术：\n\n### 1. 参数化查询 (预编译语句)\n\n参数化查询是防御SQL注入的最有效方法之一。它将SQL语句与数据分开处理：\n\n```php\n// 不安全的方式\n$query = "SELECT * FROM users WHERE username = \'" + $username + "\'"; \n\n// 安全的方式（PHP PDO示例）\n$stmt = $pdo->prepare("SELECT * FROM users WHERE username = ?");\n$stmt->execute([$username]);\n```\n\n### 2. ORM框架\n\nORM(Object-Relational Mapping)框架可以自动处理SQL查询，并实现参数化：\n\n```javascript\n// Node.js Sequelize示例\nUser.findOne({ where: { username: username } });\n```\n\n### 3. 输入验证与转义\n\n对用户输入进行验证和转义：\n\n```php\n// PHP示例\n$username = mysqli_real_escape_string($conn, $username);\n```\n\n### 4. 最小权限原则\n\n数据库账户应遵循最小权限原则，仅分配必要的权限。\n\n### 5. WAF (Web应用防火墙)\n\nWAF可以识别并拦截SQL注入攻击。',
      questions: [
        {
          id: 1,
          content: '防御SQL注入的最佳方法是什么？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['使用正则表达式过滤用户输入', '使用参数化查询（预编译语句）', '禁用错误显示', '限制数据库连接数'],
          answer: [1] // 使用参数化查询（预编译语句）
        },
        {
          id: 2,
          content: '以下哪个不是有效的SQL注入防御措施？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['使用ORM框架', '对用户输入进行白名单验证', '简单地用replace()函数删除单引号', '实施最小权限原则'],
          answer: [2] // 简单地用replace()函数删除单引号
        }
      ]
    },
    {
      id: 6,
      name: '绕过WAF技术',
      description: '学习常见SQL注入过滤器绕过技术和编码绕过方法',
      score: 10,
      document:
        "## WAF绕过技术\n\nWeb应用防火墙(WAF)通常会检测和阻止SQL注入攻击，但攻击者可能使用多种技术绕过这些防护机制。\n\n### 常见绕过技术\n\n1. **大小写混合**\n许多WAF只检查特定关键词的小写形式，使用大小写混合可能绕过检测：\n```sql\nSeLeCt * FrOm users\n```\n\n2. **注释符嵌入**\n在SQL关键词中插入注释：\n```sql\nSE/**/LECT * FR/**/OM users\n```\n\n3. **编码绕过**\n使用URL编码、十六进制编码或Unicode编码：\n```sql\nSELECT CHAR(0x73, 0x65, 0x63, 0x72, 0x65, 0x74)\n```\n\n4. **空白字符替代**\n使用制表符、换行符等替代空格：\n```sql\nSELECT*FROM[users]WHERE[id]=1\n```\n\n5. **等价函数替换**\n使用同等功能的不同表达方式：\n```sql\n'1'='1' 可替换为 '1'LIKE'1'\n```\n\n了解这些技术有助于构建更强大的防御策略。",
      questions: [
        {
          id: 1,
          content: '以下哪种技术不能用于绕过WAF对SQL注入的检测？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['使用大小写混合', '在关键词中插入注释', '使用十六进制编码', '直接清除浏览器缓存'],
          answer: [3] // 直接清除浏览器缓存
        },
        {
          id: 2,
          content: '以下哪个SQL语句可能用于绕过WAF检测？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['SELECT * FROM users', 'SE/**/LECT * FROM users', 'select * from users', 'SELECT FROM users *'],
          answer: [1] // SE/**/LECT * FROM users
        }
      ]
    },
    {
      id: 7,
      name: 'SQL注入实验环境',
      description: '在靶机环境中实践SQL注入攻击和数据提取',
      score: 10,
      document: `# SQL注入实验环境

## 实验简介

本实验环境提供了一个基础的用户查询系统，你将在这个环境中学习如何识别SQL注入漏洞，并尝试构造特定的输入来获取隐藏的信息。

**注意：本实验环境仅用于教育目的。** 所有操作都在受控环境中进行，这些技术在未经授权的情况下使用是违法的。

## 实验目标

1. 理解 SQL 注入的基本原理
2. 学习如何识别潜在的注入点
3. 掌握基本的 SQL 注入技术
4. 获取隐藏的 flag 值

## 实验环境说明

实验环境包含：
- 一个用于查询用户信息的输入框
- 一个显示查询结果的区域
- 一个包含 flag 的隐藏数据表

## 实验步骤

### 第一步：理解正常查询流程

1. 观察查询界面的基本功能
2. 注意查询结果区域显示的 SQL 语句
3. 使用正常用户名进行查询
4. 分析查询结果和执行的 SQL 语句

### 第二步：发现漏洞

系统会在你多次尝试后提供帮助：

1. 基础提示帮助你理解正常操作
2. 进阶提示指出潜在的漏洞
3. 高级提示协助你完成目标

### 第三步：漏洞利用尝试

在理解了基本原理后：

1. 尝试使用特殊字符测试系统响应
2. 观察系统的反馈信息
3. 根据反馈调整你的输入

### 第四步：获取 Flag

获取 flag 需要你：

1. 理解高级 SQL 查询语句的作用
2. 发现数据库中的其他表
3. 构造正确的查询语句

## 实验小贴士

- 仔细观察每次查询的结果
- 注意系统的警告信息
- 遇到困难时先多次尝试
- 记录并分析你的尝试过程

## 实验评分标准

实验评分基于以下几个方面：
1. 对注入原理的理解（3分）
2. 成功绕过验证（3分）
3. 成功获取 flag（4分）

## 安全提醒

请记住：
- 未经授权的注入测试是违法的
- 应该使用合法的渗透测试方法
- 发现漏洞要及时报告

现在，开始你的实验吧！`,
      questions: [
        {
          id: 1,
          content: '请描述SQL注入的基本原理 (在本前端模拟实验的上下文中)',
          score: 3,
          requiresTarget: false,
          type: 'open-ended-without-answer'
        },
        {
          id: 2,
          content: "以下哪个payload可以成功绕过前端模拟的用户名验证，并至少显示 '用户存在!' 的结果？",
          score: 3,
          requiresTarget: false,
          type: 'single-choice',
          options: ["' OR '1'='1", 'testuser', "'; DROP TABLE users; --", '正常用户名'],
          answer: 1 // testuser
        },
        {
          id: 3,
          content: '请使用 `UNION SELECT` 类型的 payload，尝试获取模拟的 flag 值。请写出你使用的 payload 和最终获取的 flag 值。',
          score: 4,
          requiresTarget: false,
          type: 'open-ended-with-answer'
        }
      ]
    }
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440000'
  }
}; 