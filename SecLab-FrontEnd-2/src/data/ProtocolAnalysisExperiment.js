// 协议分析实验模拟数据
export const ProtocolAnalysisExperiment = {
  id: 16,
  name: '协议分析实战',
  introduction: '本实验将帮助你理解网络协议的工作原理，掌握TCP/IP协议分析、HTTP协议分析和网络安全事件分析的基本技能',
  difficulty: 3,
  taskPoints: [
    {
      id: 1,
      name: 'TCP/IP协议基础', 
      description: '学习TCP/IP协议栈的基本结构和各层协议特征',
      score: 5,
      document:
        '## TCP/IP协议基础\n\nTCP/IP协议栈是互联网通信的基础，它将网络通信划分为多个层次，每层负责不同的功能。\n\n### OSI七层模型与TCP/IP四层模型\n\n**OSI七层模型：**\n1. 物理层 - 传输比特流\n2. 数据链路层 - 帧的传输\n3. 网络层 - 数据包路由\n4. 传输层 - 端到端传输\n5. 会话层 - 建立和管理会话\n6. 表示层 - 数据格式转换\n7. 应用层 - 应用程序通信\n\n**TCP/IP四层模型：**\n1. 网络接口层 - 对应OSI物理层和数据链路层\n2. 网络层 - IP协议\n3. 传输层 - TCP/UDP协议\n4. 应用层 - HTTP、FTP、DNS等协议\n\n### 常见协议类型\n\n1. **TCP (Transmission Control Protocol)**\n   - 面向连接的可靠传输协议\n   - 提供数据完整性和顺序保证\n   - 使用三次握手建立连接\n\n2. **UDP (User Datagram Protocol)**\n   - 无连接的不可靠传输协议\n   - 传输速度快，但不保证数据到达\n   - 适用于实时应用如视频通话\n\n3. **IP (Internet Protocol)**\n   - 负责数据包的路由和转发\n   - IP地址标识网络中的主机\n   - IPv4使用32位地址，IPv6使用128位地址\n\n4. **HTTP (Hypertext Transfer Protocol)**\n   - 用于Web浏览器和服务器之间的通信\n   - 基于TCP协议，默认端口80\n\n5. **ARP (Address Resolution Protocol)**\n   - 将IP地址转换为MAC地址\n   - 在局域网内广播查询\n\n理解这些协议的工作原理对于网络协议分析至关重要。',
      questions: [
        {
          id: 1,
          content: 'TCP协议是面向连接的还是无连接的？',
          score: 2,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['面向连接', '无连接', '半连接', '以上都不是'],
          answer: [0] // 面向连接
        },
        {
          id: 2,
          content: 'TCP三次握手的顺序是？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['SYN → SYN-ACK → ACK', 'ACK → SYN → SYN-ACK', 'SYN → ACK → SYN-ACK', 'SYN-ACK → SYN → ACK'],
          answer: [0] // SYN → SYN-ACK → ACK
        }
      ]
    },
    {
      id: 2,
      name: '数据包分析基础',
      description: '学习使用Wireshark等工具捕获和分析网络数据包',
      score: 7,
      document:
        '## 数据包分析基础\n\n网络数据包分析是网络安全的核心技能之一，通过捕获和分析数据包，可以了解网络中的通信模式和潜在的安全威胁。\n\n### Wireshark基本操作\n\n1. **捕获数据包**\n   - 选择网络接口\n   - 开始捕获\n   - 使用过滤器筛选特定协议\n\n2. **过滤器语法**\n   - `tcp` - 显示所有TCP数据包\n   - `udp` - 显示所有UDP数据包\n   - `http` - 显示所有HTTP流量\n   - `ip.addr == 192.168.1.100` - 显示特定IP地址的流量\n   - `tcp.port == 80` - 显示特定端口的流量\n\n3. **分析数据包内容**\n   - 查看帧信息\n   - 分析IP头部\n   - 分析TCP/UDP头部\n   - 查看应用层数据\n\n### 常见数据包字段\n\n**IP头部字段：**\n- Version: IP协议版本\n- TTL: 生存时间\n- Protocol: 上层协议类型\n- Source Address: 源IP地址\n- Destination Address: 目的IP地址\n\n**TCP头部字段：**\n- Source Port: 源端口\n- Destination Port: 目的端口\n- Sequence Number: 序列号\n- Acknowledgment Number: 确认号\n- Flags: 标志位(SYN, ACK, FIN, RST等)\n- Window Size: 窗口大小\n\n**UDP头部字段：**\n- Source Port: 源端口\n- Destination Port: 目的端口\n- Length: 数据包长度\n- Checksum: 校验和\n\n通过分析这些字段，可以深入理解网络通信的细节。',
      questions: [
        {
          id: 1,
          content: '在Wireshark中，哪个过滤器可以只显示TCP数据包？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['ip', 'tcp', 'udp', 'http'],
          answer: [1] // tcp
        },
        {
          id: 2,
          content: 'TCP头部中的SYN标志位表示什么？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['确认数据已收到', '请求建立连接', '请求断开连接', '重置连接'],
          answer: [1] // 请求建立连接
        }
      ]
    },
    {
      id: 3,
      name: 'HTTP协议分析',
      description: '学习分析HTTP请求和响应，提取敏感信息',
      score: 8,
      document:
        '## HTTP协议分析\n\nHTTP协议是Web通信的基础，分析HTTP流量可以帮助我们理解Web应用的工作原理，发现潜在的安全问题。\n\n### HTTP请求结构\n\n一个完整的HTTP请求包括：\n\n```\nGET /api/users HTTP/1.1\nHost: localhost\nUser-Agent: Mozilla/5.0\nAccept: application/json\nCookie: session=abc123\n\n```\n\n**请求方法：**\n- GET - 获取资源\n- POST - 提交数据\n- PUT - 更新资源\n- DELETE - 删除资源\n- HEAD - 获取响应头部\n\n### HTTP响应结构\n\n```\nHTTP/1.1 200 OK\nContent-Type: application/json\nContent-Length: 50\n\n{"status": "success", "data": [...]}    \n```\n\n**状态码：**\n- 2xx - 成功\n- 3xx - 重定向\n- 4xx - 客户端错误\n- 5xx - 服务器错误\n\n### 常见安全问题\n\n1. **敏感信息泄露**\n   - Cookie中的会话信息\n   - 请求体中的表单数据\n   - 响应中的敏感数据\n\n2. **不安全的HTTP方法**\n   - 未授权的DELETE请求\n   - 未验证的PUT请求\n\n3. **缺少安全头部**\n   - 缺少HTTPS\n   - 缺少CORS限制\n   - 缺少安全相关的HTTP头部\n\n分析HTTP流量时，应特别关注这些安全问题。',
      questions: [
        {
          id: 1,
          content: 'HTTP请求中哪个头部字段用于标识客户端浏览器？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['Host', 'User-Agent', 'Accept', 'Cookie'],
          answer: [1] // User-Agent
        },
        {
          id: 2,
          content: 'HTTP状态码404表示什么？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['服务器错误', '请求成功', '资源未找到', '重定向'],
          answer: [2] // 资源未找到
        }
      ]
    },
    {
      id: 4,
      name: '网络安全事件分析',
      description: '学习识别和分析常见的网络安全事件，包括端口扫描、SQL注入、XSS攻击等',
      score: 10,
      document:
        '## 网络安全事件分析\n\n网络安全事件分析是安全运维的核心技能，通过分析安全事件日志，可以及时发现和响应安全威胁。\n\n### 常见安全事件类型\n\n1. **端口扫描 (Port Scan)**\n   - 攻击者扫描目标主机开放的端口\n   - 识别服务类型和版本\n   - 为后续攻击做准备\n\n2. **SQL注入 (SQL Injection)**\n   - 攻击者通过注入恶意SQL语句\n   - 获取或修改数据库数据\n   - 可能导致数据泄露或系统崩溃\n\n3. **XSS攻击 (Cross-Site Scripting)**\n   - 攻击者注入恶意JavaScript代码\n   - 窃取用户Cookie和会话信息\n   - 进行钓鱼攻击\n\n4. **暴力破解 (Brute Force)**\n   - 攻击者尝试大量用户名和密码组合\n   - 尝试登录系统\n   - 需要账户锁定机制防御\n\n5. **数据泄露 (Data Exfiltration)**\n   - 攻击者将敏感数据传输到外部\n   - 通过网络流量分析可以发现异常\n   - 需要监控出站连接\n\n### 安全事件分析流程\n\n1. **收集事件日志**\n   - 网络流量日志\n   - 系统日志\n   - 应用日志\n\n2. **分析事件特征**\n   - 识别攻击类型\n   - 确定攻击来源\n   - 评估影响范围\n\n3. **响应和处置**\n   - 阻断攻击源\n   - 修复漏洞\n   - 加强监控\n\n4. **记录和报告**\n   - 记录事件详情\n   - 生成安全报告\n   - 总结经验教训\n\n通过系统化的分析流程，可以有效应对网络安全事件。',
      questions: [
        {
          id: 1,
          content: '以下哪种攻击最可能导致数据泄露？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['端口扫描', 'SQL注入', 'XSS攻击', '暴力破解'],
          answer: [1] // SQL注入
        },
        {
          id: 2,
          content: '安全事件分析的第一步是什么？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['分析事件特征', '收集事件日志', '响应和处置', '记录和报告'],
          answer: [1] // 收集事件日志
        },
        {
          id: 3,
          content: '以下哪种事件的严重级别通常最高？',
          score: 4,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['端口扫描', '数据泄露', 'XSS尝试', '暴力破解'],
          answer: [1] // 数据泄露
        }
      ]
    },
    {
      id: 5,
      name: '协议分析实验环境',
      description: '在靶机环境中实践协议分析，分析数据包、HTTP日志和安全事件，获取隐藏的Flag',
      score: 10,
      document: `# 协议分析实验环境

## 实验简介

本实验环境提供了一个完整的网络协议分析平台，你将在这个环境中学习如何分析网络数据包、HTTP请求日志和安全事件，找出隐藏的敏感信息和Flag值。

**注意：本实验环境仅用于教育目的。** 所有操作都在受控环境中进行，这些技术在未经授权的情况下使用是违法的。

## 实验目标

1. 理解网络协议的基本原理
2. 学习使用数据包分析工具
3. 掌握HTTP协议分析方法
4. 识别常见网络安全事件
5. 获取隐藏的Flag值

## 实验环境说明

实验环境包含三个级别：

### Level 1 - TCP/IP协议分析
- 数据包捕获和分析
- TCP三次握手过程分析
- 协议类型识别

### Level 2 - HTTP协议分析
- HTTP请求日志分析
- 敏感信息提取
- Cookie和会话分析

### Level 3 - 网络安全分析
- 安全事件日志分析
- 攻击类型识别
- 数据泄露检测

## 实验步骤

### Level 1：TCP/IP协议分析

1. 观察数据包预览信息
2. 输入协议类型进行筛选（如 TCP、UDP、HTTP、ARP）
3. 分析三次握手过程
4. 识别不同协议的特征

### Level 2：HTTP协议分析

1. 分析HTTP请求日志
2. 输入路径或方法进行筛选
3. 提取Cookie和会话信息
4. 查找隐藏在响应中的敏感数据

### Level 3：网络安全分析

1. 分析安全事件日志
2. 按严重级别筛选事件
3. 识别攻击类型和模式
4. 在数据泄露事件中查找隐藏的Flag

## 实验小贴士

- 仔细观察每条记录的详细信息
- 注意Flag的格式通常为 flag{...}
- 分析事件描述中的线索
- 结合多个数据源进行交叉验证

## 实验评分标准

实验评分基于以下几个方面：
1. TCP/IP协议分析（3分）
2. HTTP协议分析（3分）
3. 安全事件分析与Flag获取（4分）

## 安全提醒

请记住：
- 未经授权的网络分析是违法的
- 应该使用合法的渗透测试方法
- 发现漏洞要及时报告

现在，开始你的实验吧！`,
      questions: [
        {
          id: 1,
          content: '请描述TCP三次握手的过程',
          score: 3,
          requiresTarget: false,
          type: 'open-ended-without-answer'
        },
        {
          id: 2,
          content: 'HTTP请求中哪个字段通常包含会话信息？',
          score: 3,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['Host', 'User-Agent', 'Cookie', 'Referer'],
          answer: [2] // Cookie
        },
        {
          id: 3,
          content: '请分析安全事件日志，找到数据泄露事件中隐藏的Flag值。',
          score: 4,
          requiresTarget: false,
          type: 'open-ended-with-answer'
        }
      ]
    }
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440016'
  }
};