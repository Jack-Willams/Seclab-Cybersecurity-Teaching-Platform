// 导出所有漏洞实验模拟数据
import { SQLInjectionExperiment } from './SQLInjectionExperiment';
import { XSSExperiment } from './XSSExperiment';
import { CSRFExperiment } from './CSRFExperiment';
import { CommandInjectionExperiment } from './CommandInjectionExperiment';
import { FileUploadExperiment } from './FileUploadExperiment';
import { MiddlewareVulnerabilityExperiment } from './MiddlewareVulnerabilityExperiment';
import { ComponentVulnerabilityExperiment } from './ComponentVulnerabilityExperiment';
import { StackOverflowExperiment } from './StackOverflowExperiment';
import { ProtocolAnalysisExperiment } from './ProtocolAnalysisExperiment';

// 创建基础实验数据，确保ID从1开始连续
const SQLInjection = JSON.parse(JSON.stringify(SQLInjectionExperiment));
SQLInjection.id = 1;
SQLInjection.name = 'SQL注入基础实验';

const XSS = JSON.parse(JSON.stringify(XSSExperiment));
XSS.id = 2;
XSS.name = 'XSS跨站脚本攻击实验';

const CSRF = JSON.parse(JSON.stringify(CSRFExperiment));
CSRF.id = 3;
CSRF.name = 'CSRF跨站请求伪造实验';

const CommandInjection = JSON.parse(JSON.stringify(CommandInjectionExperiment));
CommandInjection.id = 4;
CommandInjection.name = '命令注入漏洞实验';

const FileUpload = JSON.parse(JSON.stringify(FileUploadExperiment));
FileUpload.id = 5;
FileUpload.name = '文件上传漏洞实验';

const MiddlewareVulnerability = JSON.parse(JSON.stringify(MiddlewareVulnerabilityExperiment));
MiddlewareVulnerability.id = 6;
MiddlewareVulnerability.name = '目录遍历漏洞实验';
MiddlewareVulnerability.introduction = '学习目录遍历漏洞的原理和利用方法，包括路径遍历、敏感文件读取、目录遍历绕过等技术。通过实战演练掌握目录遍历漏洞的发现、利用和防护方法。';

const ComponentVulnerability = JSON.parse(JSON.stringify(ComponentVulnerabilityExperiment));
ComponentVulnerability.id = 7;
ComponentVulnerability.name = '组件漏洞挖掘';

// 创建自定义实验内容，填充ID 8-12
const BusinessLogicVulnerability = {
  id: 8,
  name: '业务逻辑漏洞实战',
  introduction: '基于真实电商平台业务流程，系统训练水平越权、垂直越权、支付金额篡改、订单重放攻击、验证码复用、短信炸弹等12种典型业务逻辑漏洞的发现与利用方法，掌握业务安全测试思路',
  difficulty: 3,
  taskPoints: [
    {
      id: 1,
      name: '越权漏洞分析',
      description: '水平越权与垂直越权原理与实战',
      score: 12,
      document: '## 越权漏洞分析\n\n越权漏洞是业务逻辑漏洞中最常见的一种，分为水平越权与垂直越权。\n\n水平越权指同级别用户间的越权访问，垂直越权指低权限用户获取高权限功能。本节将通过真实案例讲解这两类越权漏洞的发现与利用技巧。',
      questions: [
        {
          id: 1,
          content: '以下哪种行为属于水平越权？',
          score: 5,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['普通用户访问管理员功能', '用户A查看用户B的订单信息', '游客访问需要登录的页面', '绕过验证码登录']
        },
        {
          id: 2,
          content: '检测越权漏洞最有效的方法是什么？',
          score: 7,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['比较不同角色的Cookie值', '使用不同权限账号测试相同接口', '检查HTTP响应头', '分析JavaScript代码']
        }
      ]
    },
    {
      id: 2,
      name: '支付漏洞利用',
      description: '分析电商平台支付流程中的安全隐患',
      score: 15,
      document: '## 支付漏洞利用\n\n电商平台的支付流程是业务逻辑漏洞的重灾区，包括订单金额篡改、支付绕过、订单重放等多种攻击方式。\n\n本节将模拟一个真实电商平台，系统分析支付流程中的安全隐患及其防护方法。',
      questions: [
        {
          id: 1,
          content: '支付金额篡改漏洞通常出现在哪个环节？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['生成订单时', '支付过程中', '前端显示时', '支付完成后']
        },
        {
          id: 2,
          content: '以下哪种方式无法有效防止订单重放攻击？',
          score: 7,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['使用订单唯一标识', '设置订单有效期', '记录IP地址', '使用HTTPS传输']
        }
      ]
    }
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440008'
  }
};

const IntranetPenetration = {
  id: 9,
  name: '内网渗透技术',
  introduction: '从外网突破到内网控制的完整渗透链路实践，包括边界突破、域环境信息收集、横向移动(Hash传递/票据传递)、域控提权、隐蔽通信隧道搭建及权限持久化(黄金票据/影子账户)等高级内网渗透技术',
  difficulty: 5,
  taskPoints: [
    {
      id: 1,
      name: '内网信息收集',
      description: '掌握域环境下的信息收集技术',
      score: 15,
      document: '## 内网信息收集\n\n成功突破外网边界后，内网信息收集是关键的第一步。本节将介绍在域环境中的有效信息收集方法，包括：\n\n1. 存活主机探测\n2. 域控制器识别\n3. 用户组结构分析\n4. 敏感信息查找\n5. 可信关系发现',
      questions: [
        {
          id: 1,
          content: '在Windows域环境中，以下哪个命令可以查询域控制器信息？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['net user', 'nltest /dclist', 'ipconfig /all', 'tasklist']
        },
        {
          id: 2,
          content: '在内网信息收集阶段，以下哪个工具不适合进行大规模端口扫描？',
          score: 7,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['Nmap', 'Masscan', 'Responder', 'Zmap']
        }
      ]
    },
    {
      id: 2,
      name: '横向移动技术',
      description: '学习域环境中的横向移动方法',
      score: 18,
      document: '## 横向移动技术\n\n横向移动是内网渗透中的关键环节，本节将详细介绍多种横向移动技术：\n\n1. 哈希传递攻击(PTH)\n2. 票据传递攻击(PTT)\n3. 远程服务利用\n4. WMI和PSExec技术\n5. DCOM横向移动',
      questions: [
        {
          id: 1,
          content: '哈希传递攻击(Pass-The-Hash)主要利用了Windows身份验证中的哪个协议的特性？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['Kerberos', 'NTLM', 'Digest', 'Basic']
        },
        {
          id: 2,
          content: '以下哪个工具不能用于横向移动？',
          score: 10,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['Mimikatz', 'PsExec', 'WMI', 'Wireshark']
        }
      ]
    }
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440009'
  }
};

const CodeAudit = {
  id: 10,
  name: '代码审计进阶',
  introduction: '使用静态分析与动态调试相结合的方法，基于真实开源CMS项目源码，系统训练漏洞点定位、参数流追踪、调用链分析、危险函数识别等代码审计核心技能，提升白盒安全测试能力',
  difficulty: 4,
  taskPoints: [
    {
      id: 1,
      name: '静态代码分析',
      description: '学习高效的源码静态分析方法',
      score: 15,
      document: '## 静态代码分析\n\n静态代码分析是白盒安全测试的基础，本节将介绍：\n\n1. 危险函数识别技术\n2. 污点传播分析方法\n3. 代码自动化扫描工具的使用\n4. 各类漏洞的特征识别',
      questions: [
        {
          id: 1,
          content: '在PHP语言中，以下哪个函数最容易导致命令注入漏洞？',
          score: 6,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['echo', 'system', 'strlen', 'array_push']
        },
        {
          id: 2,
          content: '污点分析的主要目的是什么？',
          score: 9,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['优化代码性能', '检测死代码', '跟踪用户输入到危险函数的传播路径', '统计代码行数']
        }
      ]
    },
    {
      id: 2,
      name: 'PHP CMS审计实战',
      description: '分析真实CMS系统中的安全漏洞',
      score: 18,
      document: '## PHP CMS审计实战\n\n本节将使用真实的开源CMS系统作为审计对象，系统演示漏洞发现全流程：\n\n1. 项目结构分析\n2. 入口点识别\n3. 危险函数回溯\n4. 参数传递链路分析\n5. 漏洞利用验证',
      questions: [
        {
          id: 1,
          content: '对CMS系统进行代码审计时，首先应当分析哪个部分？',
          score: 9,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['数据库配置文件', '页面模板', '请求处理入口', 'JavaScript文件']
        },
        {
          id: 2,
          content: '在代码审计过程中发现SQL注入漏洞后，应如何负责任地处理？',
          score: 9,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['立即公开漏洞细节', '私下出售漏洞', '向开发者报告并给予修复时间', '在社交媒体发布但不给出细节']
        }
      ]
    }
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440010'
  }
};

const CTFPractice = {
  id: 11,
  name: 'CTF综合实战',
  introduction: '通过实战演练最新CTF赛题，全面提升Web渗透、二进制逆向、密码学、隐写分析等多领域安全技能，掌握高效解题思路与自动化工具开发方法，从入门到进阶竞赛水平',
  difficulty: 5,
  taskPoints: [
    {
      id: 1,
      name: 'Web题型分析',
      description: 'CTF比赛中常见Web题型解题思路',
      score: 15,
      document: '## Web题型分析\n\nCTF比赛中的Web题型通常包括但不限于：\n\n1. SQL注入变种\n2. XSS高级利用\n3. 文件包含与上传\n4. SSRF服务端请求伪造\n5. 反序列化攻击\n\n本节将通过实际题目讲解解题思路与技巧。',
      questions: [
        {
          id: 1,
          content: 'CTF比赛中的Web题目通常更侧重于测试哪方面能力？',
          score: 7,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['UI设计能力', '代码优化能力', '漏洞利用技巧', '数据库设计能力']
        },
        {
          id: 2,
          content: '面对一个未知的Web应用，CTF选手通常会首先进行哪项操作？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['查看源代码', '测试默认凭据', '进行SQL注入', '分析网站架构']
        }
      ]
    },
    {
      id: 2,
      name: 'CTF解题框架开发',
      description: '学习开发自动化CTF解题工具',
      score: 18,
      document: '## CTF解题框架开发\n\nCTF比赛中，自动化工具可以大幅提升解题效率。本节将指导学员开发一套CTF解题辅助框架，包含：\n\n1. 自动化SQL注入模块\n2. 加解密工具集\n3. Web漏洞利用模板\n4. 快速Exploit生成器',
      questions: [
        {
          id: 1,
          content: '开发CTF工具框架时，以下哪种编程语言因其丰富的安全工具库而被广泛使用？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['C#', 'Python', 'Pascal', 'Swift']
        },
        {
          id: 2,
          content: '在CTF自动化工具中，以下哪个功能对Web题目最不重要？',
          score: 10,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['HTTP请求构造', 'Cookie管理', '3D图形渲染', '响应解析']
        }
      ]
    }
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440011'
  }
};

const RedTeamArsenal = {
  id: 12,
  name: '红队武器库',
  introduction: '系统学习红队实战武器装备的使用与定制，包括Cobalt Strike高级功能应用、木马免杀技术(反病毒绕过)、社会工程学钓鱼攻击、网络侦查、横向移动与后渗透维权等红队核心战术与技术',
  difficulty: 5,
  taskPoints: [
    {
      id: 1,
      name: 'Cobalt Strike高级应用',
      description: '学习CS的高级功能与定制开发',
      score: 15,
      document: '## Cobalt Strike高级应用\n\nCobalt Strike是当前红队行动中最常用的C2框架之一，本节将深入讲解：\n\n1. Beacon高级控制\n2. 自定义Profile配置\n3. 云上C2基础设施搭建\n4. Sleep脚本开发\n5. 自定义模块扩展',
      questions: [
        {
          id: 1,
          content: 'Cobalt Strike中，哪个组件负责在受感染主机上执行命令？',
          score: 7,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['Team Server', 'Beacon', 'Listener', 'Stager']
        },
        {
          id: 2,
          content: '为避免被安全设备检测，Cobalt Strike的Malleable C2配置主要修改什么内容？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['杀毒软件规则', '网络流量特征', '操作系统设置', '用户权限']
        }
      ]
    },
    {
      id: 2,
      name: '木马免杀技术',
      description: '学习绕过主流杀毒软件的技术',
      score: 18,
      document: '## 木马免杀技术\n\n免杀是红队武器库中的核心技术，本节将系统介绍：\n\n1. 静态特征识别与规避\n2. 行为特征分析与对抗\n3. 基于硬编码的免杀技术\n4. 分离加载技术\n5. 环境检测技术',
      questions: [
        {
          id: 1,
          content: '杀毒软件主要通过哪种方式检测已知木马？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['特征码匹配', 'IP地址追踪', '操作系统版本检测', '硬件信息比对']
        },
        {
          id: 2,
          content: '以下哪种技术不属于木马免杀方法？',
          score: 10,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['代码混淆', '分离加载', '数据加密', '硬件虚拟化']
        }
      ]
    }
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440012'
  }
};

const VulnerabilityMethodology = {
  id: 13,
  name: '漏洞挖掘方法论',
  introduction: '系统讲解从发现到利用的完整漏洞挖掘流程，包括模糊测试(Fuzzing)技术应用、静态代码分析方法、动态调试技巧、漏洞验证与利用(PoC/Exploit)开发以及规范的漏洞报告与CVE申请全过程',
  difficulty: 5,
  taskPoints: [
    {
      id: 1,
      name: 'Fuzzing技术实践',
      description: '学习现代模糊测试方法与工具',
      score: 15,
      document: '## Fuzzing技术实践\n\nFuzzing是现代漏洞挖掘的核心技术之一，本节将深入讲解：\n\n1. 基于覆盖率的Fuzzing\n2. AFL/libFuzzer等工具使用\n3. 自定义变异策略\n4. 有效种子选择\n5. 崩溃分析与漏洞确认',
      questions: [
        {
          id: 1,
          content: '以下哪个不是有效的Fuzzing策略？',
          score: 6,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['随机变异', '基于覆盖率的反馈', '基于语法的生成', '逐字节递增']
        },
        {
          id: 2,
          content: 'AFL(American Fuzzy Lop)的核心优势是什么？',
          score: 9,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['GUI界面易用', '基于代码覆盖率的反馈机制', '兼容所有操作系统', '内置漏洞利用生成器']
        }
      ]
    },
    {
      id: 2,
      name: 'PoC与Exploit开发',
      description: '学习漏洞验证与利用代码开发',
      score: 18,
      document: '## PoC与Exploit开发\n\n发现漏洞后，编写有效的验证和利用代码是关键技能，本节将系统介绍：\n\n1. 概念验证(PoC)编写规范\n2. 稳定利用代码开发方法\n3. 通用漏洞利用技术\n4. 绕过保护机制的技巧\n5. CVE申请流程与报告撰写',
      questions: [
        {
          id: 1,
          content: 'PoC(概念验证)与Exploit的主要区别是什么？',
          score: 8,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['编程语言不同', '前者验证漏洞存在性，后者完成漏洞利用', '使用场景不同', '开发难度不同']
        },
        {
          id: 2,
          content: '申请CVE编号时需要提供的关键信息不包括：',
          score: 10,
          requiresTarget: false,
          type: 'multiple-choice',
          options: ['漏洞影响的软件版本', '漏洞的技术细节', '漏洞发现者信息', '漏洞利用后可获得的经济收益']
        }
      ]
    }
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440013'
  }
};

// 导出所有实验数据集合
export const AllExperiments = [
  SQLInjection,       // ID: 1 - SQL注入基础实验
  XSS,                // ID: 2 - XSS跨站脚本攻击实验
  CSRF,               // ID: 3 - CSRF跨站请求伪造实验
  CommandInjection,   // ID: 4 - 命令注入漏洞实验
  FileUpload,         // ID: 5 - 文件上传漏洞实验
  MiddlewareVulnerability, // ID: 6 - 目录遍历漏洞实验
  ComponentVulnerability,  // ID: 7 - 组件漏洞挖掘
  BusinessLogicVulnerability, // ID: 8 - 业务逻辑漏洞实战
  IntranetPenetration,     // ID: 9 - 内网渗透技术
  CodeAudit,              // ID: 10 - 代码审计进阶
  CTFPractice,           // ID: 11 - CTF综合实战
  RedTeamArsenal,        // ID: 12 - 红队武器库
  VulnerabilityMethodology, // ID: 13 - 漏洞挖掘方法论
  ProtocolAnalysisExperiment, // ID: 16 - 协议分析实战
  StackOverflowExperiment  // ID: 15 - 栈溢出
];

// 按ID查找实验的辅助函数
export const findExperimentById = (id) => {
  // 直接查找匹配的ID
  const experiment = AllExperiments.find(exp => exp.id === id);
  if (experiment) {
    console.log(`找到ID为${id}的实验:`, experiment.name);
    return experiment;
  }
  
  // 如果没有找到，返回默认的SQL注入实验（ID为1）
  console.log(`未找到ID为${id}的实验，返回默认SQL注入实验`);
  return SQLInjection;
};

// 导出实验类型常量，方便前端代码使用
export const ExperimentTypes = {
  SQL_INJECTION: 1,
  XSS: 2,
  CSRF: 3,
  COMMAND_INJECTION: 4,
  FILE_UPLOAD: 5,
  MIDDLEWARE_VULNERABILITY: 6,
  COMPONENT_VULNERABILITY: 7,
  BUSINESS_LOGIC_VULNERABILITY: 8,
  INTRANET_PENETRATION: 9,
  CODE_AUDIT: 10,
  CTF_PRACTICE: 11,
  RED_TEAM_ARSENAL: 12,
  VULNERABILITY_METHODOLOGY: 13,
  PROTOCOL_ANALYSIS: 16,
  STACK_OVERFLOW: 15
};

// 按难度获取实验
export const getExperimentsByDifficulty = (difficulty) => {
  return AllExperiments.filter(exp => exp.difficulty === difficulty);
};

// 获取初学者推荐的实验
export const getBeginnerExperiments = () => {
  return AllExperiments.filter(exp => exp.difficulty <= 2);
};

// 获取高级实验
export const getAdvancedExperiments = () => {
  return AllExperiments.filter(exp => exp.difficulty >= 4);
}; 