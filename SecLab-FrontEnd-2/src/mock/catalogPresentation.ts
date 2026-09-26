import type { CourseSummaryDto } from '../api'
import type { Course } from '../types/course'
import type { Experiment } from '../types/experiment'
import type { ModuleOverViewType } from '../pages/User/Modules/components/ModuleOverView'
import type { CourseOverViewType } from '../pages/User/Courses/components/CourseOverView'

/**
 * 课程模块（章节）。`labId` 指向真实存在、可进入的实验；没有 labId 的是理论模块，
 * 前端不能给它拼一个 /user/module/<随便什么 id>——那样会跳进完全不相干的实验。
 */
export type PresentationCourseModuleSeed = {
  id: number
  name: string
  introduction: string
  type: string[]
  difficulty: 1 | 2 | 3 | 4 | 5
  labId?: number
}

export type PresentationCourseSeed = {
  id: number
  name: string
  description: string
  /** 详情页「课程简介」用的长文；列表卡片仍用 description */
  longDescription: string
  difficulty: 1 | 2 | 3 | 4 | 5
  type: string
  category: string
  cover: string
  instructor: string
  costTime: number
  schedule: string
  /** public/video 下的真实文件名；没有主讲视频时留空 */
  videoFile?: string
  /** 所属视频章节，用来生成「视频选集」 */
  videoChapter?: string
  tags: string[]
  modules: PresentationCourseModuleSeed[]
}

/**
 * public/video 下真实存在的 12 个视频。title/description 按文件内容归纳，
 * chapter 用来把同一章的视频组成课程页的「视频选集」。
 * 时长不写死——详情页读 <video> 的 loadedmetadata，避免和实际文件对不上。
 */
export type PresentationVideoSeed = {
  file: string
  title: string
  description: string
  chapter: string
}

export const VIDEO_CHAPTER_WEB = '第一章 · Web 与网络攻防'
export const VIDEO_CHAPTER_CRYPTO = '第二章 · 密码学'
export const VIDEO_CHAPTER_SYSTEM = '第三章 · 系统安全'
export const VIDEO_CHAPTER_OVERVIEW = '第四章 · 网络安全总论'

export const PRESENTATION_VIDEO_SEEDS: PresentationVideoSeed[] = [
  {
    file: '1.1Sql注入攻击.mp4',
    title: 'SQL 注入攻击',
    description: '讲解 SQL 注入的成因、常见注入类型与参数化查询防护。',
    chapter: VIDEO_CHAPTER_WEB,
  },
  {
    file: '1.2Xss与csrf-.mp4',
    title: 'XSS 与 CSRF',
    description: '对比跨站脚本与跨站请求伪造的触发条件和防护手段。',
    chapter: VIDEO_CHAPTER_WEB,
  },
  {
    file: '1.3 IDS和IPS.mp4',
    title: 'IDS 和 IPS',
    description: '入侵检测与入侵防御系统的原理、部署位置与能力差异。',
    chapter: VIDEO_CHAPTER_WEB,
  },
  {
    file: '1.4Apt攻击.mp4',
    title: 'APT 攻击',
    description: '高级持续性威胁的攻击链、典型战术与防御思路。',
    chapter: VIDEO_CHAPTER_WEB,
  },
  {
    file: '1.5防火墙.mp4',
    title: '防火墙',
    description: '包过滤、状态检测到下一代防火墙的演进与规则配置。',
    chapter: VIDEO_CHAPTER_WEB,
  },
  {
    file: '2.2 古典密码.mp4',
    title: '古典密码',
    description: '代换与置换密码的设计思想，以及频率分析破译方法。',
    chapter: VIDEO_CHAPTER_CRYPTO,
  },
  {
    file: '2.4公钥密码简介.mp4',
    title: '公钥密码简介',
    description: '公钥密码要解决的问题、单向陷门函数与密钥协商。',
    chapter: VIDEO_CHAPTER_CRYPTO,
  },
  {
    file: '2.5 Rsa公钥加密方案.mp4',
    title: 'RSA 公钥加密方案',
    description: 'RSA 的密钥生成、加解密流程与安全性分析。',
    chapter: VIDEO_CHAPTER_CRYPTO,
  },
  {
    file: '2.6数字签名.mp4',
    title: '数字签名',
    description: '数字签名如何提供完整性、认证性与不可否认性。',
    chapter: VIDEO_CHAPTER_CRYPTO,
  },
  {
    file: '3.2 操作系统安全概述.mp4',
    title: '操作系统安全概述',
    description: '操作系统的权限模型、访问控制与系统加固要点。',
    chapter: VIDEO_CHAPTER_SYSTEM,
  },
  {
    file: '3.4 可信计算.mp4',
    title: '可信计算',
    description: '硬件信任根、可信启动与远程证明的基本概念。',
    chapter: VIDEO_CHAPTER_SYSTEM,
  },
  {
    file: '4.1.1 网络安全概述.mp4',
    title: '网络安全概述',
    description: '网络安全的目标、威胁全景与纵深防御体系。',
    chapter: VIDEO_CHAPTER_OVERVIEW,
  },
]

/**
 * 平台上真实可进入的 7 个实验（/user/modules 里状态为「可开始」的那些）。
 * 课程页只允许跳这 7 个 id，其余实验尚未开放环境，链过去只会进到不相干的页面。
 */
export type PresentationLabLink = {
  id: number
  name: string
  difficulty: 1 | 2 | 3 | 4 | 5
  estimatedTime: string
  type: string
}

/**
 * 每门课的学习目标与前置知识。单独放一张表而不塞进课程种子，是为了让上面的课程数组
 * 保持可读；key 用课程 id（已和 userservice.course 对齐）。
 */
export type PresentationCourseLearning = {
  objectives: string[]
  prerequisites: string[]
}

export const PRESENTATION_COURSE_LEARNING: Record<number, PresentationCourseLearning> = {
  1: {
    objectives: [
      '理解参数拼接如何让用户输入变成 SQL 语法的一部分',
      '掌握联合查询、报错、布尔盲注与时间盲注四类利用手法',
      '能独立完成从注入点探测到数据获取的完整流程',
      '会用参数化查询与最小权限账号完成加固',
    ],
    prerequisites: ['SQL 基础语法（SELECT / UNION / WHERE）', 'HTTP 请求与参数传递方式'],
  },
  2: {
    objectives: [
      '区分反射型、存储型与 DOM 型 XSS 的触发路径',
      '理解浏览器自动携带 Cookie 为什么让 CSRF 成立',
      '能构造可用的 XSS payload 与 CSRF 自动提交表单',
      '会用输出编码、CSP 与 SameSite 完成防护',
    ],
    prerequisites: ['HTML 与 JavaScript 基础', '同源策略与 Cookie 工作方式'],
  },
  // 3 是空号：「文件上传漏洞」课程已按目录基线删除（靶场仍保留）
  4: {
    objectives: [
      '说清 IDS 旁路监听与 IPS 串行阻断的能力边界',
      '理解特征检测、异常检测与行为分析各自的适用场景',
      '能读懂并编写 Snort / Suricata 检测规则',
      '掌握镜像口取流与误报调优的基本方法',
    ],
    prerequisites: ['TCP/IP 协议与常见端口', 'Wireshark / tcpdump 基本使用'],
  },
  5: {
    objectives: [
      '用 ATT&CK 框架拆解一次完整的 APT 事件',
      '识别侦察、初始入侵、驻留、横向移动、数据外带各阶段特征',
      '能从日志中还原攻击链并定位失陷点',
      '理解威胁情报与检测工程在防御侧的作用',
    ],
    prerequisites: ['常见 Web 与系统漏洞的利用方式', '操作系统日志与进程基础'],
  },
  6: {
    objectives: [
      '区分包过滤、状态检测、应用层网关与下一代防火墙',
      '掌握 ACL 规则顺序与最小放行原则的设计方法',
      '能完成 SNAT / DNAT 与 DMZ 区域划分配置',
      '理解防火墙与 IPS、VPN 的联动方式',
    ],
    prerequisites: ['IP 地址、子网与路由基础', 'TCP/UDP 端口与会话概念'],
  },
  7: {
    objectives: [
      '掌握凯撒、仿射、维吉尼亚与置换密码的加解密过程',
      '会用频率分析与重合指数破译单表 / 多表代换',
      '能估算密钥空间并解释穷举成本',
      '建立"统计特征泄露"这一密码分析的基本直觉',
    ],
    prerequisites: ['模运算与排列组合基础', '基本的字母频率概念'],
  },
  8: {
    objectives: [
      '说清对称密钥分发难题与公钥体制的解决思路',
      '理解单向陷门函数、大整数分解与离散对数难题',
      '掌握 Diffie-Hellman 密钥交换的完整流程',
      '理解证书、CA 与 PKI 信任链如何抵御中间人攻击',
    ],
    prerequisites: ['模幂运算与素数基础', '对称加密的基本概念'],
  },
  9: {
    objectives: [
      '独立推导 RSA 密钥生成与加解密的数学过程',
      '用小参数手工完成一次完整的加解密验证',
      '说清 PKCS#1 v1.5 与 OAEP 填充为什么不可省略',
      '复盘小指数、共模与低私钥指数三类经典攻击',
    ],
    prerequisites: ['欧拉定理与扩展欧几里得算法', '建议先学《公钥密码简介》'],
  },
  10: {
    objectives: [
      '说清签名与加密在密钥使用方向上的本质区别',
      '理解哈希摘要在签名流程中承担的作用',
      '比较 RSA-PSS、DSA 与 ECDSA 的适用场景',
      '能完成一次证书链校验并解释失败原因',
    ],
    prerequisites: ['哈希函数与公钥密码基础', '证书与 PKI 的基本概念'],
  },
  11: {
    objectives: [
      '梳理用户 / 组 / 权限位、setuid 与能力机制',
      '区分自主访问控制与强制访问控制的适用边界',
      '能定位路径拼接缺陷导致的越界文件读取',
      '会用路径规范化与白名单完成加固',
    ],
    prerequisites: ['Linux 常用命令与文件权限', '进程与文件系统基本概念'],
  },
  12: {
    objectives: [
      '说清可信根为什么必须落在硬件上',
      '掌握 TPM 的密钥层次、PCR 度量与密封存储用途',
      '区分 Secure Boot 的"阻断"与 Measured Boot 的"记录"',
      '理解远程证明如何向第三方证明自身状态',
    ],
    prerequisites: ['操作系统启动流程', '哈希函数与数字签名基础'],
  },
  13: {
    objectives: [
      '用 CIA 三要素建立安全评价框架',
      '分类梳理网络层、系统层、应用层与人员层面的主要威胁',
      '说清一次典型攻击链的推进方式',
      '理解纵深防御体系中各类设备与流程的分工',
    ],
    prerequisites: ['计算机网络基础', '本课程为入门总论，无需安全前置知识'],
  },
  14: {
    objectives: [
      '说清参数入栈、返回地址保存与栈帧布局',
      '能用调试器定位缓冲区到返回地址的偏移',
      '独立编写 exp 劫持返回地址拿到 shell',
      '理解 Canary / NX / ASLR / PIE 的防护原理与绕过前提',
    ],
    prerequisites: ['C 语言与指针基础', '汇编基础与 GDB 调试经验'],
  },
  15: {
    objectives: [
      '理解 chunk 头部结构与前后向合并规则',
      '掌握 fastbin、tcache、unsorted bin 的取用顺序',
      '说清 UAF、Double Free 与堆块重叠的成因',
      '理解 tcache poisoning 与 unlink 的利用前提',
    ],
    prerequisites: ['建议先学《栈溢出》', '动态内存管理与指针操作'],
  },
  16: {
    objectives: [
      '理解可变参数函数如何按格式串取栈上数据',
      '用 %x / %s 泄露栈内容并定位参数偏移',
      '用 %n 实现任意地址写入并改写 GOT 表',
      '掌握 FORTIFY_SOURCE 与格式串常量化的防护效果',
    ],
    prerequisites: ['C 语言 printf 系列函数用法', '栈布局与 GOT / PLT 基础'],
  },
  17: {
    objectives: [
      '看懂 Wireshark 里一条 TCP 连接从握手到挥手的完整过程',
      '能用过滤表达式从海量流量中定位目标会话',
      '逐字段解析 HTTP 报文，理解明文传输为什么能被直接嗅探',
      '从混杂流量中识别扫描、爆破与异常外连的特征并还原攻击时间线',
    ],
    prerequisites: ['TCP/IP 分层模型与常见端口', 'HTTP 请求响应结构'],
  },
}

export const getCourseLearning = (courseId: number | null | undefined): PresentationCourseLearning | undefined =>
  courseId == null ? undefined : PRESENTATION_COURSE_LEARNING[courseId]

export const PRESENTATION_LAB_LINKS: PresentationLabLink[] = [
  { id: 1, name: 'SQL注入基础实验', difficulty: 3, estimatedTime: '2-3小时', type: 'Web安全' },
  { id: 2, name: 'XSS跨站脚本攻击实验', difficulty: 2, estimatedTime: '2-3小时', type: 'Web安全' },
  { id: 3, name: 'CSRF跨站请求伪造实验', difficulty: 3, estimatedTime: '3-4小时', type: 'Web安全' },
  { id: 4, name: '命令注入漏洞实验', difficulty: 2, estimatedTime: '2小时', type: 'Web安全' },
  { id: 5, name: '文件上传漏洞实验', difficulty: 3, estimatedTime: '2小时', type: 'Web安全' },
  { id: 6, name: '目录遍历漏洞实验', difficulty: 3, estimatedTime: '2小时', type: 'Web安全' },
  { id: 15, name: '栈溢出实验', difficulty: 3, estimatedTime: '2-3小时', type: '二进制安全' },
  // 靶场三关（TCP/IP 分析 / HTTP 分析 / 安全事件分析）对应「协议分析实战」课程的三个模块，
  // 所以那三个模块都挂 labId: 16，进的是同一个实验环境的不同关卡。
  { id: 16, name: '协议分析实战', difficulty: 3, estimatedTime: '2-3小时', type: '网络攻击与防御' },
]

type PresentationModuleSeed = {
  id: number
  name: string
  description: string
  difficulty: 1 | 2 | 3 | 4 | 5
  type: string
  estimatedTime: string
  score: number
  courseId: number
  courseName: string
}

export const PRESENTATION_TOTAL_USERS = 128
export const PRESENTATION_CLASS_SCORE = 76

/**
 * 课程目录基线（2026-08-08 按线上部署核对）：16 门课，**没有**「文件上传漏洞」，
 * 末尾多一门「协议分析实战」。id 3 因此是空号，不要拿去补别的课。
 *
 * 真正要命的是 name，不是 id ——
 * `mergeCourseSummariesWithPresentation` 用 `item.name === seed.name` 匹配远端课程，
 * `resolvePresentationCourse` 也是名字优先、id 兜底。所以 name 必须和
 * `userservice.course.course_name` 一字不差；对不上的话，那门课会退化成纯本地种子，
 * 描述/封面/标签都拿不到远端数据。id 只在后端不在线时当路由兜底用。
 *
 * 历史坑（别再踩）：前端课程数与数据库对不上时，卡片带的 id 和详情页认的 id 会各算各的，
 * 结果就是标题变占位符、视频放成隔壁课的。加课删课后务必和
 * `SELECT id, course_name FROM userservice.course ORDER BY id` 对一遍。
 */
export const PRESENTATION_COURSE_SEEDS: PresentationCourseSeed[] = [
  {
    id: 1,
    name: 'SQL注入攻击',
    description: '系统讲解 SQL 注入原理、利用方式与常见防护策略。',
    longDescription:
      '从数据库查询语句是如何被拼接出来讲起，系统梳理 SQL 注入的成因、探测方法与利用手法：联合查询注入、报错注入、布尔盲注、时间盲注，以及针对关键字过滤的常见绕过技巧。防护部分覆盖参数化查询（预编译）、最小权限账号、输入校验与 WAF 规则，帮助你同时从开发与测试两个视角处理注入风险。',
    difficulty: 3,
    type: 'web',
    category: 'Web安全',
    cover: '/cover-sql.png',
    instructor: '李伟',
    costTime: 8,
    schedule: '每周一 14:00-16:00',
    videoFile: '1.1Sql注入攻击.mp4',
    videoChapter: VIDEO_CHAPTER_WEB,
    tags: ['SQL注入', 'Web安全', '数据库安全'],
    modules: [
      {
        id: 101,
        name: 'SQL 注入原理与探测',
        introduction:
          '理解参数拼接如何让用户输入变成 SQL 语法的一部分，掌握单引号闭合、注释符截断、字段数探测与回显位判断等基础探测流程。',
        type: ['Web安全', 'SQL注入'],
        difficulty: 3,
      },
      {
        id: 102,
        name: 'SQL 注入实战演练',
        introduction:
          '进入 SQL 注入靶机环境，实践联合查询注入与盲注取数，完成从探测注入点到拖库的完整链路，并验证参数化查询的防护效果。',
        type: ['Web安全', 'SQL注入'],
        difficulty: 3,
        labId: 1,
      },
    ],
  },
  {
    id: 2,
    name: 'XSS与CSRF攻击',
    description: '围绕 XSS 与 CSRF 攻击链路，训练前端安全分析与防护能力。',
    longDescription:
      '聚焦浏览器端两类经典漏洞。XSS 部分区分反射型、存储型与 DOM 型三条触发路径，讲解输出上下文编码、CSP 策略与富文本白名单过滤；CSRF 部分从浏览器自动携带 Cookie 的机制出发讲清攻击成立的前提，并给出 Token 校验、SameSite 属性与敏感操作二次确认等防御方案。',
    difficulty: 2,
    type: 'web',
    category: 'Web安全',
    cover: '/cover-xss.png',
    instructor: '李伟',
    costTime: 6,
    schedule: '每周二 10:00-12:00',
    videoFile: '1.2Xss与csrf-.mp4',
    videoChapter: VIDEO_CHAPTER_WEB,
    tags: ['XSS', 'CSRF', '前端安全'],
    modules: [
      {
        id: 201,
        name: '浏览器安全模型',
        introduction:
          '梳理同源策略、Cookie 携带规则与浏览器信任边界，理解为什么 XSS 能拿到会话、而 CSRF 不需要拿到会话也能替用户发请求。',
        type: ['Web安全', '前端安全'],
        difficulty: 2,
      },
      {
        id: 202,
        name: 'XSS 跨站脚本实战',
        introduction:
          '进入 XSS 靶机环境，分别构造反射型、存储型与 DOM 型payload，实践窃取会话与页面劫持，并验证输出编码与 CSP 的拦截效果。',
        type: ['Web安全', 'XSS'],
        difficulty: 2,
        labId: 2,
      },
      {
        id: 203,
        name: 'CSRF 跨站请求伪造实战',
        introduction:
          '进入 CSRF 靶机环境，构造自动提交表单完成越权操作，再通过 Token 校验与 SameSite 配置复现防护前后的差异。',
        type: ['Web安全', 'CSRF'],
        difficulty: 3,
        labId: 3,
      },
    ],
  },
  {
    id: 4,
    name: 'IDS和IPS系统',
    description: '介绍 IDS 与 IPS 的工作机制、部署方法与流量分析思路。',
    longDescription:
      '讲解入侵检测（IDS）与入侵防御（IPS）的工作机制与部署位置差异：基于特征、基于异常与基于行为的三类检测方法各自适用的场景；结合 Snort / Suricata 规则语法讲解规则编写、误报调优与流量镜像采集方式，帮助你把检测能力真正落到网络边界与关键链路上。',
    difficulty: 3,
    type: 'network',
    category: '网络安全',
    cover: '/cover-ids-ips.png',
    instructor: '李伟',
    costTime: 7,
    schedule: '每周三 14:00-16:00',
    videoFile: '1.3 IDS和IPS.mp4',
    videoChapter: VIDEO_CHAPTER_WEB,
    tags: ['IDS', 'IPS', '网络安全'],
    modules: [
      {
        id: 401,
        name: '入侵检测原理与部署位置',
        introduction:
          '对比 IDS 的旁路监听与 IPS 的串行阻断，理解特征检测与异常检测的取舍，掌握镜像口、分光器等常见流量采集方式。',
        type: ['网络安全', 'IDS'],
        difficulty: 3,
      },
      {
        id: 402,
        name: '检测规则编写与误报调优',
        introduction:
          '以 Snort / Suricata 规则语法为例，从一条真实攻击流量出发编写检测规则，并通过阈值、白名单与关联分析降低误报率。',
        type: ['网络安全', 'IPS'],
        difficulty: 4,
      },
    ],
  },
  {
    id: 5,
    name: 'APT攻击分析',
    description: '通过案例分析理解 APT 攻击链路、战术特征与应对方式。',
    longDescription:
      '以真实 APT 案例为线索，拆解侦察、初始入侵、驻留、提权、横向移动到数据外带的完整攻击链，结合 ATT&CK 框架理解攻击者的战术与技术（TTP）；防御侧介绍威胁情报运用、日志留存策略与检测工程的组织方式，说明为什么单点防护挡不住有组织的持续攻击。',
    difficulty: 4,
    type: 'advanced',
    category: '高级威胁',
    cover: '/cover-apt.png',
    instructor: '李伟',
    costTime: 10,
    schedule: '每周四 10:00-12:00',
    videoFile: '1.4Apt攻击.mp4',
    videoChapter: VIDEO_CHAPTER_WEB,
    tags: ['APT', '威胁分析', '安全运营'],
    modules: [
      {
        id: 501,
        name: 'APT 攻击链与 ATT&CK 框架',
        introduction:
          '用 ATT&CK 矩阵拆解一起完整的 APT 事件，识别各阶段的战术目标与常用技术，建立"攻击者视角"的分析习惯。',
        type: ['高级威胁', 'APT'],
        difficulty: 4,
      },
      {
        id: 502,
        name: '初始入侵：远程命令执行',
        introduction:
          'APT 最常见的初始入侵方式之一是通过暴露在外的 Web 应用执行系统命令。本模块进入命令注入实验环境，实践命令拼接、分隔符绕过与反弹连接。',
        type: ['高级威胁', '命令注入'],
        difficulty: 2,
        labId: 4,
      },
    ],
  },
  {
    id: 6,
    name: '防火墙技术',
    description: '学习防火墙原理、规则配置和网络边界防护方法。',
    longDescription:
      '从包过滤、状态检测到应用层网关与下一代防火墙，梳理各代防火墙的能力边界与性能取舍；讲解访问控制列表（ACL）的设计顺序、NAT 与端口映射、DMZ 区域划分，以及防火墙与 VPN、IPS 的联动配置，帮助你形成一套可落地的边界防护策略。',
    difficulty: 3,
    type: 'network',
    category: '网络安全',
    cover: '/cover-firewall.png',
    instructor: '李伟',
    costTime: 8,
    schedule: '每周五 14:00-16:00',
    videoFile: '1.5防火墙.mp4',
    videoChapter: VIDEO_CHAPTER_WEB,
    tags: ['防火墙', '边界防护', '网络安全'],
    modules: [
      {
        id: 601,
        name: '防火墙类型与工作原理',
        introduction:
          '对比包过滤、状态检测、应用层代理与下一代防火墙的检查粒度，理解会话表、五元组匹配与深度包检测的实现代价。',
        type: ['网络安全', '防火墙'],
        difficulty: 3,
      },
      {
        id: 602,
        name: '访问控制策略与 NAT 配置',
        introduction:
          '从一份真实网络拓扑出发设计 ACL 与区域策略，实践 SNAT/DNAT 端口映射，并讨论规则顺序、最小放行与策略审计。',
        type: ['网络安全', '防火墙'],
        difficulty: 4,
      },
    ],
  },
  {
    id: 7,
    name: '古典密码学',
    description: '掌握古典密码体制、手工破译思路与密码学基础概念。',
    longDescription:
      '从凯撒密码、单表与多表代换（维吉尼亚）、置换密码到转轮机，梳理古典密码的设计思想；并通过频率分析、重合指数与卡西斯基测试等手工破译方法，建立"密钥空间"与"统计特征"这两个贯穿现代密码学的核心直觉，为后续公钥密码课程打底。',
    difficulty: 2,
    type: 'crypto',
    category: '密码学',
    cover: '/cover-classic-crypto.png',
    instructor: '李伟',
    costTime: 6,
    schedule: '每周一 10:00-12:00',
    videoFile: '2.2 古典密码.mp4',
    videoChapter: VIDEO_CHAPTER_CRYPTO,
    tags: ['密码学', '古典密码', '安全基础'],
    modules: [
      {
        id: 701,
        name: '代换密码与置换密码',
        introduction:
          '梳理凯撒、仿射、单表代换、维吉尼亚多表代换与列置换的加解密过程，比较各自的密钥空间大小与抗分析能力。',
        type: ['密码学', '古典密码'],
        difficulty: 2,
      },
      {
        id: 702,
        name: '频率分析与手工破译',
        introduction:
          '用字母频率分布、重合指数与卡西斯基测试还原密钥长度并破译密文，理解统计特征泄露为何是古典密码的致命弱点。',
        type: ['密码学', '密码分析'],
        difficulty: 3,
      },
    ],
  },
  {
    id: 8,
    name: '公钥密码简介',
    description: '介绍公钥密码体系、密钥管理、证书与 PKI 基础。',
    longDescription:
      '讲解公钥密码要解决的核心问题——在不安全信道上完成密钥协商与身份绑定。内容涵盖单向陷门函数的思想、Diffie-Hellman 密钥交换、公私钥的职责划分，以及数字证书、CA 与 PKI 信任链的组织方式，说明为什么"把公钥公开"反而是安全的。',
    difficulty: 3,
    type: 'crypto',
    category: '密码学',
    cover: '/cover-pubkey.png',
    instructor: '李伟',
    costTime: 7,
    schedule: '每周二 14:00-16:00',
    videoFile: '2.4公钥密码简介.mp4',
    videoChapter: VIDEO_CHAPTER_CRYPTO,
    tags: ['公钥密码', 'PKI', '证书体系'],
    modules: [
      {
        id: 801,
        name: '公钥密码体制与数学基础',
        introduction:
          '从对称密钥分发难题引出公钥思想，理解单向陷门函数、大整数分解与离散对数难题，并掌握 Diffie-Hellman 密钥交换流程。',
        type: ['密码学', '公钥密码'],
        difficulty: 3,
      },
      {
        id: 802,
        name: '密钥分发、证书与 PKI',
        introduction:
          '讲解中间人攻击如何击穿裸公钥交换，进而理解数字证书、CA 签发、信任链校验与证书吊销在真实系统中的作用。',
        type: ['密码学', 'PKI'],
        difficulty: 3,
      },
    ],
  },
  {
    id: 9,
    name: 'RSA公钥加密方案',
    description: '深入理解 RSA 的数学原理、密钥生成与典型应用。',
    longDescription:
      '深入 RSA：从欧拉定理与模幂运算推导密钥生成与加解密流程，讲解填充方案（PKCS#1 v1.5 与 OAEP）为什么不可省略，并分析小指数攻击、共模攻击、低私钥指数攻击等经典安全问题，最后落到工程实践中的参数选择与性能取舍。',
    difficulty: 4,
    type: 'crypto',
    category: '密码学',
    cover: '/cover-rsa.png',
    instructor: '李伟',
    costTime: 8,
    schedule: '每周三 08:00-10:00',
    videoFile: '2.5 Rsa公钥加密方案.mp4',
    videoChapter: VIDEO_CHAPTER_CRYPTO,
    tags: ['RSA', '非对称加密', '密码学'],
    modules: [
      {
        id: 901,
        name: 'RSA 密钥生成与加解密',
        introduction:
          '手工走一遍素数选取、模数与欧拉函数计算、公私钥指数求解的全过程，并用小参数完成一次完整的加解密验证。',
        type: ['密码学', 'RSA'],
        difficulty: 4,
      },
      {
        id: 902,
        name: '填充方案与经典攻击',
        introduction:
          '分析教科书式 RSA 的确定性缺陷，理解 PKCS#1 v1.5 与 OAEP 填充的必要性，并复盘小指数、共模与低私钥指数三类经典攻击。',
        type: ['密码学', '密码分析'],
        difficulty: 4,
      },
    ],
  },
  {
    id: 10,
    name: '数字签名技术',
    description: '学习数字签名、身份认证和证书验证相关核心技术。',
    longDescription:
      '讲解数字签名如何同时提供完整性、认证性与不可否认性：哈希函数与签名算法（RSA-PSS、DSA、ECDSA）的组合方式、签名与加密的本质区别，以及证书链校验、时间戳服务与吊销机制（CRL / OCSP）在实际系统中的落地方式。',
    difficulty: 4,
    type: 'crypto',
    category: '密码学',
    cover: '/cover-signature.png',
    instructor: '李伟',
    costTime: 7,
    schedule: '每周四 14:00-16:00',
    videoFile: '2.6数字签名.mp4',
    videoChapter: VIDEO_CHAPTER_CRYPTO,
    tags: ['数字签名', '身份认证', '密码学'],
    modules: [
      {
        id: 1001,
        name: '数字签名原理与算法',
        introduction:
          '理解"私钥签名、公钥验签"的方向为何与加密相反，掌握哈希摘要在签名中的作用，并比较 RSA-PSS、DSA 与 ECDSA 的适用场景。',
        type: ['密码学', '数字签名'],
        difficulty: 4,
      },
      {
        id: 1002,
        name: '证书链校验与签名实务',
        introduction:
          '从一张真实证书出发逐级校验签发链，理解时间戳、吊销状态查询与签名验证失败的常见原因。',
        type: ['密码学', 'PKI'],
        difficulty: 4,
      },
    ],
  },
  {
    id: 11,
    name: '操作系统安全概述',
    description: '建立操作系统安全机制、访问控制与系统加固的整体认知。',
    longDescription:
      '建立操作系统安全的整体框架：用户与权限模型、自主访问控制与强制访问控制（SELinux / AppArmor）、文件系统权限与路径解析规则、进程隔离与最小权限原则；并结合路径穿越这类真实漏洞，理解访问控制一旦在路径拼接处失效会造成什么后果。',
    difficulty: 3,
    type: 'system',
    category: '系统安全',
    cover: '/cover-os-security.png',
    instructor: '李伟',
    costTime: 8,
    schedule: '每周五 10:00-12:00',
    videoFile: '3.2 操作系统安全概述.mp4',
    videoChapter: VIDEO_CHAPTER_SYSTEM,
    tags: ['操作系统安全', '访问控制', '系统加固'],
    modules: [
      {
        id: 1101,
        name: '权限模型与访问控制',
        introduction:
          '梳理用户/组/权限位、setuid 与能力机制，比较自主访问控制与强制访问控制的差异，掌握最小权限原则的落地方式。',
        type: ['系统安全', '访问控制'],
        difficulty: 3,
      },
      {
        id: 1102,
        name: '文件系统访问控制实战',
        introduction:
          '进入目录遍历实验环境，实践路径拼接缺陷如何突破目录边界读取系统敏感文件，并用规范化路径与白名单完成加固。',
        type: ['系统安全', '路径穿越'],
        difficulty: 3,
        labId: 6,
      },
    ],
  },
  {
    id: 12,
    name: '可信计算技术',
    description: '学习可信计算、TPM、可信启动与远程证明等关键概念。',
    longDescription:
      '介绍可信计算的核心思路——用硬件信任根为整个软件栈提供度量与证明能力。内容涵盖 TPM / TCM 的功能划分、信任链与可信启动（Secure Boot 与 Measured Boot 的区别）、PCR 度量值与远程证明（Remote Attestation）流程，以及可信执行环境（TEE）的典型应用场景。',
    difficulty: 4,
    type: 'system',
    category: '系统安全',
    cover: '/cover-trusted-computing.png',
    instructor: '李伟',
    costTime: 8,
    schedule: '每周六 10:00-12:00',
    videoFile: '3.4 可信计算.mp4',
    videoChapter: VIDEO_CHAPTER_SYSTEM,
    tags: ['可信计算', 'TPM', '系统安全'],
    modules: [
      {
        id: 1201,
        name: '可信根与 TPM 基础',
        introduction:
          '理解可信根为什么必须落在硬件上，掌握 TPM 的密钥层次、PCR 寄存器与密封存储（Sealing）的基本用法。',
        type: ['系统安全', '可信计算'],
        difficulty: 4,
      },
      {
        id: 1202,
        name: '可信启动与远程证明',
        introduction:
          '按启动顺序走一遍度量扩展链，区分 Secure Boot 的"阻断"与 Measured Boot 的"记录"，并理解远程证明如何向第三方证明自身状态。',
        type: ['系统安全', '可信计算'],
        difficulty: 5,
      },
    ],
  },
  {
    id: 13,
    name: '网络安全概述',
    description: '梳理网络安全基础概念、威胁类型与整体防护框架。',
    longDescription:
      '网络安全的入门总论：梳理机密性、完整性、可用性三大安全目标，常见威胁类型（嗅探、欺骗、拒绝服务、恶意代码、社会工程），典型攻击链的推进方式，以及纵深防御体系中各类安全设备与安全流程的分工，为后续所有专项课程建立统一的术语与全局视角。',
    difficulty: 3,
    type: 'network',
    category: '网络安全',
    cover: '/cover-network-security.png',
    instructor: '李伟',
    costTime: 6,
    schedule: '每周一 08:00-10:00',
    videoFile: '4.1.1 网络安全概述.mp4',
    videoChapter: VIDEO_CHAPTER_OVERVIEW,
    tags: ['网络安全', '安全架构', '防护体系'],
    modules: [
      {
        id: 1301,
        name: '安全目标与威胁全景',
        introduction:
          '从 CIA 三要素出发建立评价体系，分类梳理网络层、系统层、应用层与人员层面的主要威胁及其真实案例。',
        type: ['网络安全', '安全基础'],
        difficulty: 3,
      },
      {
        id: 1302,
        name: '纵深防御与安全运营',
        introduction:
          '理解边界防护、终端防护、检测响应与安全管理如何分层协作，认识资产梳理、日志采集与应急响应在日常运营中的位置。',
        type: ['网络安全', '安全运营'],
        difficulty: 3,
      },
    ],
  },
  {
    id: 14,
    name: '栈溢出',
    description: '讲解栈缓冲区溢出的原理、内存布局与利用思路，带你入门二进制安全（PWN）。',
    longDescription:
      '从函数调用栈、栈帧结构与返回地址讲起，逐步介绍如何通过构造超长输入覆盖返回地址、劫持控制流，并结合 shellcode、ret2text、ret2libc 等经典手法理解二进制安全（PWN）的核心思想；最后介绍 Canary、NX、ASLR、PIE 等栈保护机制及其绕过前提。',
    difficulty: 4,
    type: 'binary',
    category: '二进制安全',
    cover: '/cover-stack-overflow.png',
    instructor: '李伟',
    costTime: 8,
    schedule: '每周六 14:00-16:00',
    tags: ['栈溢出', '二进制安全', 'PWN'],
    modules: [
      {
        id: 1401,
        name: '函数调用栈与栈帧结构',
        introduction:
          '理解参数入栈、返回地址保存与栈帧布局，用调试器观察一次函数调用的内存变化，定位缓冲区与返回地址的相对偏移。',
        type: ['二进制安全', 'PWN'],
        difficulty: 3,
      },
      {
        id: 1402,
        name: '栈溢出利用实战',
        introduction:
          '进入栈溢出实验环境，用 pwndbg 定位溢出点、pwntools 编写 exp 劫持返回地址拿到本地 shell，再连接远程靶机完成 getshell 取 flag。',
        type: ['二进制安全', 'PWN'],
        difficulty: 3,
        labId: 15,
      },
    ],
  },
  {
    // id 17：本地 userservice.course 里还没有这门课，17 是种子内部的占位号。
    // 后端在线时列表卡片带的是数据库 id，详情页按「课程名」回查种子（resolvePresentationCourse
    // 是名字优先、id 兜底），所以这个号对不上数据库也不影响；但 name 必须和库里的课程名一字不差。
    id: 17,
    name: '协议分析实战',
    description: '使用 Wireshark 深度分析 HTTP/TCP/UDP 协议，理解明文嗅探与 HTTPS 防护。',
    longDescription:
      '以 Wireshark 抓包为主线，把网络协议从字节层面拆开看：先从 TCP/IP 分层与三次握手、四次挥手读懂一条连接的完整生命周期，再逐字段解析 HTTP 请求与响应，观察明文传输下账号口令是如何被直接嗅探出来的，最后进入安全事件分析——从一段混杂流量里筛出扫描、爆破与异常外连的特征，还原攻击者的动作序列。课程同时说明 HTTPS 如何通过 TLS 消除明文嗅探，以及加密之后流量分析还能看到什么。',
    difficulty: 3,
    type: 'network',
    category: '网络安全',
    cover: '/协议分析实战.png',
    instructor: '李伟',
    costTime: 8,
    schedule: '每周五 10:00-12:00',
    tags: ['协议分析', 'Wireshark', '网络安全'],
    modules: [
      {
        id: 1701,
        name: 'TCP/IP 分层与连接分析',
        introduction:
          '对照 Wireshark 抓到的真实报文理解 TCP/IP 分层：逐层剥开以太网帧、IP 头与 TCP 头，跟踪三次握手、数据传输与四次挥手，学会用过滤表达式把一条连接从海量流量里单独拎出来。',
        type: ['网络安全', '协议分析'],
        difficulty: 2,
        labId: 16,
      },
      {
        id: 1702,
        name: 'HTTP 协议解析与明文嗅探',
        introduction:
          '解析 HTTP 请求行、首部与实体，用 Follow HTTP Stream 还原一次完整会话，直观看到明文传输下账号口令与 Cookie 如何被截获，并对比 HTTPS 握手后同一份流量还能暴露哪些信息。',
        type: ['网络安全', '协议分析'],
        difficulty: 3,
        labId: 16,
      },
      {
        id: 1703,
        name: '安全事件流量分析',
        introduction:
          '从混杂流量里识别端口扫描、口令爆破与异常外连的报文特征，结合时间线还原攻击者的动作序列，输出一份可复核的事件分析结论。',
        type: ['网络安全', '协议分析'],
        difficulty: 3,
        labId: 16,
      },
    ],
  },
  {
    id: 15,
    name: '堆溢出',
    description: '讲解堆内存管理与堆溢出漏洞原理，介绍 chunk 结构、malloc/free 机制与常见堆利用手法。',
    longDescription:
      '从 glibc 堆内存管理机制（chunk 结构、bins、fastbin 与 tcache）讲起，剖析 malloc / free 的内部流程，介绍 Use-After-Free、Double Free、堆块重叠等经典问题，并结合 unlink、tcache poisoning、fastbin attack 等利用手法，帮助你理解堆利用的核心思想与对应的加固措施。',
    difficulty: 5,
    type: 'binary',
    category: '二进制安全',
    cover: '/cover-heap-overflow.png',
    instructor: '李伟',
    costTime: 10,
    schedule: '每周日 14:00-16:00',
    tags: ['堆溢出', '二进制安全', 'PWN'],
    modules: [
      {
        id: 1501,
        name: 'glibc 堆管理机制',
        introduction:
          '理解 chunk 的头部结构与前后向合并规则，掌握 fastbin、tcache、unsorted bin 的取用顺序，看清 malloc / free 的关键分支。',
        type: ['二进制安全', 'PWN'],
        difficulty: 4,
      },
      {
        id: 1502,
        name: '堆利用手法与防护',
        introduction:
          '梳理 UAF、Double Free、堆块重叠的成因，理解 tcache poisoning 与 unlink 的利用前提，并对照新版 glibc 的校验加固。',
        type: ['二进制安全', 'PWN'],
        difficulty: 5,
      },
    ],
  },
  {
    id: 16,
    name: '格式化字符串',
    description: '讲解格式化字符串漏洞的成因与利用，掌握任意地址读写与信息泄露技巧。',
    longDescription:
      '从 printf 系列函数的可变参数机制与格式化说明符（%x、%s、%n 等）讲起，剖析漏洞如何导致栈内存泄露、任意地址读取与任意地址写入；结合 %n 改写 GOT 表、劫持控制流等经典利用手法，最后给出编译选项与编码规范两个层面的防护措施。',
    difficulty: 4,
    type: 'binary',
    category: '二进制安全',
    cover: '/cover-format-string.png',
    instructor: '李伟',
    costTime: 8,
    schedule: '每周日 10:00-12:00',
    tags: ['格式化字符串', '二进制安全', 'PWN'],
    modules: [
      {
        id: 1601,
        name: '格式化字符串漏洞成因',
        introduction:
          '理解可变参数函数如何按格式串取栈上数据，掌握用 %x / %s 泄露栈内容与定位参数偏移的基本方法。',
        type: ['二进制安全', 'PWN'],
        difficulty: 3,
      },
      {
        id: 1602,
        name: '任意地址读写与 GOT 改写',
        introduction:
          '利用 %n 系列说明符实现任意地址写入，改写 GOT 表项劫持控制流，并理解 FORTIFY_SOURCE 与格式串常量化的防护效果。',
        type: ['二进制安全', 'PWN'],
        difficulty: 4,
      },
    ],
  },
]

export const PRESENTATION_MODULE_SEEDS: PresentationModuleSeed[] = [
  { id: 1, name: 'SQL注入基础实验', description: '掌握 SQL 注入漏洞的基础识别与利用方式。', difficulty: 3, type: 'Web安全', estimatedTime: '2-3小时', score: 60, courseId: 1, courseName: 'SQL注入攻击' },
  { id: 2, name: 'XSS跨站脚本攻击实验', description: '训练反射型、存储型和 DOM 型 XSS 的分析能力。', difficulty: 2, type: 'Web安全', estimatedTime: '2-3小时', score: 45, courseId: 2, courseName: 'XSS与CSRF攻击' },
  { id: 3, name: 'CSRF跨站请求伪造实验', description: '理解 CSRF 利用流程与令牌防护机制。', difficulty: 3, type: 'Web安全', estimatedTime: '3-4小时', score: 65, courseId: 2, courseName: 'XSS与CSRF攻击' },
  { id: 4, name: '命令注入漏洞实验', description: '学习命令注入漏洞的利用链与输入过滤绕过方式。', difficulty: 2, type: 'Web安全', estimatedTime: '2小时', score: 40, courseId: 5, courseName: 'APT攻击分析' },
  // 原来挂在「文件上传漏洞」课程（id 3）下，该课程已按目录基线删除；
  // 靶场本身还在（7 个可进入实验之一），这里改挂同属 Web 安全的 XSS与CSRF攻击，避免指向不存在的课程。
  { id: 5, name: '文件上传漏洞实验', description: '掌握文件上传绕过、校验缺陷利用与风险分析。', difficulty: 3, type: 'Web安全', estimatedTime: '2小时', score: 55, courseId: 2, courseName: 'XSS与CSRF攻击' },
  { id: 6, name: '目录遍历漏洞实验', description: '训练路径遍历、敏感文件读取和绕过技巧。', difficulty: 3, type: 'Web安全', estimatedTime: '2小时', score: 55, courseId: 11, courseName: '操作系统安全概述' },
  { id: 7, name: '组件漏洞挖掘', description: '围绕第三方组件高危漏洞开展分析与复现。', difficulty: 4, type: '系统安全', estimatedTime: '3小时', score: 75, courseId: 12, courseName: '可信计算技术' },
  { id: 8, name: '业务逻辑漏洞实战', description: '围绕业务流程缺陷训练越权、重放与篡改攻击。', difficulty: 3, type: 'Web安全', estimatedTime: '3-4小时', score: 65, courseId: 5, courseName: 'APT攻击分析' },
  { id: 9, name: '内网渗透技术', description: '从边界突破到横向移动，训练完整内网渗透链路。', difficulty: 5, type: '网络攻防', estimatedTime: '4-5小时', score: 85, courseId: 13, courseName: '网络安全概述' },
  { id: 10, name: '代码审计进阶', description: '基于开源项目训练漏洞点追踪与代码审计能力。', difficulty: 4, type: '系统安全', estimatedTime: '3-4小时', score: 75, courseId: 11, courseName: '操作系统安全概述' },
  { id: 11, name: 'CTF综合实战', description: '综合训练 Web、逆向、密码学与取证等能力。', difficulty: 5, type: 'CTF', estimatedTime: '5小时', score: 100, courseId: 13, courseName: '网络安全概述' },
  { id: 12, name: '红队武器库', description: '学习红队武器使用、免杀、钓鱼与渗透技巧。', difficulty: 5, type: '网络攻防', estimatedTime: '4-5小时', score: 100, courseId: 4, courseName: 'IDS和IPS系统' },
  { id: 13, name: '漏洞挖掘方法论', description: '掌握漏洞发现、验证、利用和复现的方法论。', difficulty: 5, type: '系统安全', estimatedTime: '5小时', score: 100, courseId: 11, courseName: '操作系统安全概述' },
  { id: 14, name: '第三方框架漏洞', description: '聚焦 ThinkPHP、Struts2、Spring 等框架漏洞实战。', difficulty: 5, type: '系统安全', estimatedTime: '5小时', score: 100, courseId: 12, courseName: '可信计算技术' },
  { id: 15, name: '栈溢出实验', description: '定位栈溢出点、编写 exp 劫持返回地址并远程 getshell。', difficulty: 3, type: '二进制安全', estimatedTime: '2-3小时', score: 65, courseId: 14, courseName: '栈溢出' },
]

const buildPresentationAdminCourse = (course: PresentationCourseSeed, index: number): Course => ({
  id: course.id,
  name: course.name,
  description: course.description,
  cover: course.cover,
  difficulty: course.difficulty,
  category: course.category,
  status: 'published',
  studentCount: 48 + index * 3,
  experimentCount: PRESENTATION_MODULE_SEEDS.filter((module) => module.courseId === course.id).length,
  createTime: `2024-03-${String(index + 1).padStart(2, '0')} 10:00:00`,
})

const buildPresentationCourseSummary = (course: PresentationCourseSeed): CourseSummaryDto => ({
  id: course.id,
  name: course.name,
  description: course.description,
  difficulty: course.difficulty,
  imageUrl: course.cover.replace(/^\//, ''),
  type: course.type,
  tags: course.tags,
  status: 'published',
})

const buildPresentationModuleOverview = (module: PresentationModuleSeed): ModuleOverViewType => ({
  id: module.id,
  name: module.name,
  description: module.description,
  difficulty: module.difficulty,
  type: module.type,
  status: 'available',
  estimatedTime: module.estimatedTime,
  score: module.score,
})

const buildPresentationAdminLab = (module: PresentationModuleSeed, index: number): Experiment => ({
  id: module.id,
  name: module.name,
  description: module.description,
  difficulty: module.difficulty,
  courseId: module.courseId,
  courseName: module.courseName,
  status: 'published',
  taskPoints: [
    {
      id: module.id * 10 + 1,
      name: `${module.name}任务点`,
      score: 50,
      description: `围绕 ${module.name} 的核心知识点展开训练`,
    },
  ],
  environment: {
    targetMachine: {
      image: `module-${module.id}:latest`,
      port: 80,
      memory: module.difficulty >= 4 ? '1GB' : '512MB',
    },
    operationMachine: {
      image: 'kali-tools:latest',
      port: 6080,
      memory: '1GB',
    },
  },
  studentCount: 32 + (index % 6) * 8,
  completionRate: 58 + (index % 5) * 6,
  averageScore: 70 + (index % 4) * 5,
  createTime: `2024-03-${String(index + 1).padStart(2, '0')} 09:00:00`,
})

export const buildPresentationCourseSummaries = (): CourseSummaryDto[] =>
  PRESENTATION_COURSE_SEEDS.map(buildPresentationCourseSummary)

export const buildPresentationAdminCourses = (): Course[] =>
  PRESENTATION_COURSE_SEEDS.map(buildPresentationAdminCourse)

export const buildPresentationUserCourses = (): CourseOverViewType[] =>
  PRESENTATION_COURSE_SEEDS.map((course, index) => ({
    id: course.id,
    name: course.name,
    image: course.cover,
    description: course.description,
    status: 'available',
    category: course.type,
    difficulty: course.difficulty,
    estimatedHours: course.costTime,
    tags: course.tags,
    totalStudents: 800 + index * 35,
    videoUrl: courseVideoUrl(course),
  }))

/** public 下的视频地址；文件名里有空格和中文，交给浏览器编码 */
export const videoUrlOf = (file: string) => `/video/${file}`

const courseVideoUrl = (course: PresentationCourseSeed) =>
  course.videoFile ? videoUrlOf(course.videoFile) : undefined

const courseSeedByName = new Map(PRESENTATION_COURSE_SEEDS.map((seed) => [seed.name, seed]))
const courseSeedById = new Map(PRESENTATION_COURSE_SEEDS.map((seed) => [seed.id, seed]))
const labLinkById = new Map(PRESENTATION_LAB_LINKS.map((lab) => [lab.id, lab]))

export const findPresentationLab = (labId: number | null | undefined) =>
  labId == null ? undefined : labLinkById.get(labId)

/** 课程的「视频选集」：同一章节下的全部视频，当前课程那一集会被标记为正在播放 */
export const getPresentationCourseVideos = (seed: PresentationCourseSeed | undefined) =>
  seed?.videoChapter ? PRESENTATION_VIDEO_SEEDS.filter((video) => video.chapter === seed.videoChapter) : []

/**
 * 解析路由上的课程 id。
 * 后端（experiment-module 8084）在线时，列表页卡片带的是数据库 id，
 * 这里先用远端列表把 id 换成课程名再查种子数据；后端不在线时列表页用的就是种子 id，
 * 直接按 id 查即可 —— 两条路径都能落到同一门课上。
 */
export const resolvePresentationCourse = (
  courseId: number,
  remoteCourses: CourseSummaryDto[] = [],
): PresentationCourseSeed | undefined => {
  const remote = remoteCourses.find((item) => Number(item.id) === courseId)
  if (remote?.name) {
    const byName = courseSeedByName.get(remote.name)
    if (byName) return byName
  }
  return courseSeedById.get(courseId)
}

export const buildPresentationModuleOverviews = (): ModuleOverViewType[] =>
  PRESENTATION_MODULE_SEEDS.map(buildPresentationModuleOverview)

export const buildPresentationAdminLabs = (): Experiment[] =>
  PRESENTATION_MODULE_SEEDS.map(buildPresentationAdminLab)

const courseSummaryMap = new Map(buildPresentationCourseSummaries().map((item) => [item.name, item]))
const adminCourseMap = new Map(buildPresentationAdminCourses().map((item) => [item.name, item]))
const moduleOverviewMap = new Map(buildPresentationModuleOverviews().map((item) => [item.name, item]))
const adminLabMap = new Map(buildPresentationAdminLabs().map((item) => [item.name, item]))

export const mergeCourseSummariesWithPresentation = (remoteCourses: CourseSummaryDto[] = []) =>
  PRESENTATION_COURSE_SEEDS.map((seed) => {
    const base = courseSummaryMap.get(seed.name)!
    const remote = remoteCourses.find((item) => item.name === seed.name)
    return remote
      ? {
          ...base,
          ...remote,
          description: remote.description || base.description,
          imageUrl: remote.imageUrl || base.imageUrl,
          // 后端把「课程分类」这个字段也叫 type，但存的是中文标签（如「Web安全」），
          // 和前端筛选按钮用的英文 slug（'web'/'network'/...）不是一回事——
          // 这里的 type 就得认本地种子的 slug，不能被远端覆盖，否则分类筛选永远匹配不上。
          type: base.type,
          tags: remote.tags?.length ? remote.tags : base.tags,
        }
      : base
  })

export const mergeAdminCoursesWithPresentation = (remoteCourses: Course[] = []) =>
  PRESENTATION_COURSE_SEEDS.map((seed) => {
    const base = adminCourseMap.get(seed.name)!
    const remote = remoteCourses.find((item) => item.name === seed.name)
    return remote
      ? {
          ...base,
          ...remote,
          description: remote.description || base.description,
          cover: remote.cover || base.cover,
          category: remote.category || base.category,
          studentCount: remote.studentCount || base.studentCount,
          experimentCount: base.experimentCount,
          createTime: remote.createTime || base.createTime,
        }
      : base
  })

export const mergeModuleOverviewsWithPresentation = (remoteModules: ModuleOverViewType[] = []) =>
  PRESENTATION_MODULE_SEEDS.map((seed) => {
    const base = moduleOverviewMap.get(seed.name)!
    const remote = remoteModules.find((item) => item.name === seed.name)
    return remote
      ? {
          ...base,
          ...remote,
          description: remote.description || base.description,
          type: remote.type || base.type,
          estimatedTime: remote.estimatedTime || base.estimatedTime,
          score: remote.score || base.score,
        }
      : base
  })

export const mergeAdminLabsWithPresentation = (remoteLabs: Experiment[] = []) =>
  PRESENTATION_MODULE_SEEDS.map((seed) => {
    const base = adminLabMap.get(seed.name)!
    const remote = remoteLabs.find((item) => item.name === seed.name)
    return remote
      ? {
          ...base,
          ...remote,
          description: remote.description || base.description,
          courseId: remote.courseId ?? base.courseId,
          courseName: remote.courseName || base.courseName,
          taskPoints: remote.taskPoints?.length ? remote.taskPoints : base.taskPoints,
          environment: Object.keys(remote.environment || {}).length ? remote.environment : base.environment,
          studentCount: remote.studentCount || base.studentCount,
          completionRate: remote.completionRate || base.completionRate,
          averageScore: remote.averageScore || base.averageScore,
          createTime: remote.createTime || base.createTime,
        }
      : base
  })
