<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Course } from '../../../types/course'
import { useRouter } from 'vue-router'
import type { Experiment } from '../../../types/experiment'

const router = useRouter()

// 添加动画控制状态
const isLoaded = ref(false)

onMounted(() => {
  setTimeout(() => {
    isLoaded.value = true
  }, 100)
})

// 课程列表数据
const courses = ref<Course[]>([
  {
    id: 1,
    name: 'SQL注入攻防实战',
    description: '深度解析字符型/数值型注入原理，涵盖联合查询注入、布尔盲注、时间盲注、报错注入等6大攻击类型，实验包含空格绕过、HEX编码绕过、注释符过滤突破等8种防御绕过技术',
    cover: '/cover-sql.png',
    difficulty: 3,
    category: 'Web安全',
    status: 'published',
    studentCount: 120,
    experimentCount: 0,
    createTime: '2024-03-15 10:00:00'
  },
  {
    id: 2,
    name: 'XSS漏洞深度解析',
    description: '构建反射型XSS钓鱼页面、存储型XSS持久化攻击、DOM型XSS前端漏洞利用三大实验场景，实战演示Cookie窃取、会话劫持、BeEF框架协同攻击',
    cover: '/cover-xss.png',
    difficulty: 2,
    category: 'Web安全',
    status: 'published',
    studentCount: 83,
    experimentCount: 0,
    createTime: '2024-03-14 15:30:00'
  },
  {
    id: 3,
    name: '文件上传漏洞突破',
    description: '从客户端校验绕过到服务端检测突破，涵盖图片马制作、Content-Type伪造、.htaccess攻击、二次渲染对抗、竞争条件上传等全链条攻击手法',
    cover: '/3.文件上传漏洞突破.png',
    difficulty: 3,
    category: 'Web安全',
    status: 'published',
    studentCount: 62,
    experimentCount: 0,
    createTime: '2024-03-13 09:15:00'
  },
  {
    id: 4,
    name: '中间件漏洞利用',
    description: '实战复现Weblogic反序列化漏洞(CVE-2023-21839)、Tomcat AJP协议漏洞(CVE-2020-1938)、JBoss JMXInvokerServlet反序列化三大经典漏洞',
    cover: '/4.中间件漏洞利用.png',
    difficulty: 4,
    category: '系统安全',
    status: 'published',
    studentCount: 40,
    experimentCount: 0,
    createTime: '2024-03-12 14:20:00'
  },
  {
    id: 5,
    name: '组件漏洞挖掘',
    description: '深入解析Shiro RememberMe反序列化、Fastjson JNDI注入、Log4j2远程代码执行(Log4Shell)三大组件漏洞的利用链构造与防御方案',
    cover: '/5.组件漏洞挖掘.png',
    difficulty: 4,
    category: '系统安全',
    status: 'published',
    studentCount: 42,
    experimentCount: 0,
    createTime: '2024-03-11 11:30:00'
  },
  {
    id: 6,
    name: '目录遍历',
    description: '详细介绍目录遍历漏洞的原理、利用方法和防护技术。包括路径遍历攻击、敏感文件读取、目录遍历绕过技术等核心内容，通过实战演练掌握目录遍历漏洞的发现、利用和防护方法。',
    cover: '/6.目录遍历.png',
    difficulty: 3,
    category: 'Web安全',
    status: 'published',
    studentCount: 51,
    experimentCount: 0,
    createTime: '2024-03-10 16:45:00'
  },
  {
    id: 7,
    name: '业务逻辑漏洞实战',
    description: '模拟电商平台实战环境，训练支付金额篡改、平行越权访问、短信炸弹攻击、验证码复用漏洞、空订单生成等12种典型业务场景漏洞挖掘',
    cover: '/7.业务逻辑漏洞实战.png',
    difficulty: 3,
    category: 'Web安全',
    status: 'published',
    studentCount: 55,
    experimentCount: 0,
    createTime: '2024-03-09 13:15:00'
  },
  {
    id: 8,
    name: '内网渗透技术',
    description: '构建完整内网渗透链路：从CS/MSF木马植入→横向移动(PTH/PTT)→域控提权→隧道搭建(SSH/ICMP)→权限维持(黄金票据/影子账户)',
    cover: '/8.内网渗透技术.png',
    difficulty: 5,
    category: '网络安全',
    status: 'published',
    studentCount: 35,
    experimentCount: 0,
    createTime: '2024-03-08 10:30:00'
  },
  {
    id: 9,
    name: '代码审计进阶',
    description: '基于真实CMS源码分析，训练SQL注入点定位、反序列化利用链构造、文件包含漏洞追踪、危险函数回溯等代码审计核心技能',
    cover: '/9.代码审计进阶.png',
    difficulty: 4,
    category: 'Web安全',
    status: 'published',
    studentCount: 44,
    experimentCount: 0,
    createTime: '2024-03-07 15:20:00'
  },
  {
    id: 10,
    name: 'CTF综合实战',
    description: '集成Web渗透、二进制逆向、密码破解、隐写分析等竞赛题型，包含2023年最新CTF赛题解析与自动化脚本开发技巧',
    cover: '/10.CTF攻防实战.png',
    difficulty: 5,
    category: '密码学',
    status: 'published',
    studentCount: 56,
    experimentCount: 0,
    createTime: '2024-03-06 09:45:00'
  },
  {
    id: 11,
    name: '红队武器库',
    description: '深度使用Cobalt Strike 4.9进行协同作战，涵盖木马免杀(Shellcode混淆/内存加载)、钓鱼攻击、横向移动、痕迹清理等红队战术',
    cover: '/11.红队武器库.png',
    difficulty: 5,
    category: '网络安全',
    status: 'published',
    studentCount: 38,
    experimentCount: 0,
    createTime: '2024-03-05 14:30:00'
  },
  {
    id: 12,
    name: '漏洞挖掘方法论',
    description: '从模糊测试到静态分析，完整漏洞挖掘流程实践：AFL智能模糊测试→IDA Pro逆向分析→GDB动态调试→PoC验证→CVE申请流程',
    cover: '/12.漏洞挖掘方法论.png',
    difficulty: 5,
    category: '系统安全',
    status: 'published',
    studentCount: 24,
    experimentCount: 0,
    createTime: '2024-03-04 11:20:00'
  }
])

// 搜索和筛选条件
const filters = ref({
  search: '',
  category: '',
  difficulty: '',
  status: ''
})

// 课程分类
const categories = ['Web安全', '系统安全', '密码学', '网络攻防', '移动安全']

// 过滤后的课程列表
const filteredCourses = computed(() => {
  return courses.value.filter((course) => {
    if (filters.value.search && !course.name.toLowerCase().includes(filters.value.search.toLowerCase())) {
      return false
    }
    if (filters.value.category && course.category !== filters.value.category) {
      return false
    }
    if (filters.value.difficulty && course.difficulty !== parseInt(filters.value.difficulty)) {
      return false
    }
    if (filters.value.status && course.status !== filters.value.status) {
      return false
    }
    return true
  })
})

// 获取难度星级显示
const getDifficultyStars = (difficulty: number) => '★'.repeat(difficulty) + '☆'.repeat(5 - difficulty)

// 获取状态标签样式
const getStatusBadgeClass = (status: Course['status']) => ({
  'badge-success': status === 'published',
  'badge-warning': status === 'draft',
  'badge-error': status === 'archived'
})

// 获取状态文本
const getStatusText = (status: Course['status']) =>
  ({
    published: '已发布',
    draft: '草稿',
    archived: '已归档'
  }[status])

// 处理课程操作
const handleCreateCourse = () => {
  router.push('/admin/course/create')
}

const handleEdit = (course: Course) => {
  console.log('编辑课程:', course)
}

const handleDelete = (course: Course) => {
  console.log('删除课程:', course)
}

const handleStudents = (course: Course) => {
  console.log('管理学生:', course)
}

// 实验管理相关状态
const experimentList = ref<Experiment[]>([])
const currentCourse = ref<Course | null>(null)
const showExperimentModal = ref(false)
const loading = ref(false)

// 课程关联的实验列表（模拟数据）
const courseExperiments = ref<Map<number, number[]>>(new Map())

// 获取实验列表
const fetchExperiments = async () => {
  loading.value = true
  try {
    // 这里应该从API获取实验列表
    // const response = await api请求
    // experimentList.value = response.data
    
    // 模拟数据
    experimentList.value = [
      // SQL注入相关实验
      {
        id: 1,
        name: 'SQL注入基础实验',
        description: '通过实践了解SQL注入的原理和基本利用方法',
        difficulty: 3,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-01'
      },
      {
        id: 2,
        name: 'SQL盲注技术',
        description: '掌握布尔盲注和时间盲注的高级技术',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-02'
      },
      {
        id: 3,
        name: '联合查询注入',
        description: '掌握使用order by和union select获取数据库信息的技巧',
        difficulty: 3,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-03'
      },
      {
        id: 4,
        name: '报错注入利用',
        description: '利用数据库报错机制获取敏感信息',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-04'
      },
      {
        id: 5,
        name: 'WAF绕过技术',
        description: '学习使用编码、大小写混淆等手段绕过防火墙防护',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-05'
      },
      
      // XSS相关实验
      {
        id: 6,
        name: '反射型XSS攻击',
        description: '构建钓鱼页面，实现反射型XSS攻击',
        difficulty: 2,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-06'
      },
      {
        id: 7,
        name: '存储型XSS利用',
        description: '在留言板等场景实现持久化XSS攻击',
        difficulty: 3,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-07'
      },
      {
        id: 8,
        name: 'DOM型XSS实战',
        description: '利用前端JS漏洞实现XSS攻击',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-08'
      },
      {
        id: 9,
        name: 'BeEF框架使用',
        description: '使用BeEF框架实现浏览器控制',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-09'
      },
      
      // 文件上传漏洞相关实验
      {
        id: 10,
        name: '客户端校验绕过',
        description: '绕过前端JS校验上传恶意文件',
        difficulty: 2,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-10'
      },
      {
        id: 11,
        name: '图片马制作与利用',
        description: '制作图片木马并绕过检测机制',
        difficulty: 3,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-11'
      },
      {
        id: 12,
        name: 'Content-Type绕过',
        description: '使用Burp修改请求头绕过MIME类型检测',
        difficulty: 3,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-12'
      },
      {
        id: 13,
        name: '竞争条件上传',
        description: '利用竞争条件漏洞上传恶意文件',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-13'
      },
      
      // 中间件漏洞相关实验
      {
        id: 14,
        name: 'Weblogic反序列化漏洞',
        description: '复现CVE-2023-21839漏洞利用过程',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-14'
      },
      {
        id: 15,
        name: 'Tomcat AJP协议漏洞',
        description: '复现CVE-2020-1938幽灵猫漏洞',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-15'
      },
      {
        id: 16,
        name: 'JBoss反序列化漏洞',
        description: '利用JMXInvokerServlet实现远程代码执行',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-16'
      },
      
      // 组件漏洞相关实验
      {
        id: 17,
        name: 'Shiro反序列化漏洞',
        description: '利用Shiro RememberMe漏洞获取系统权限',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-17'
      },
      {
        id: 18,
        name: 'Fastjson反序列化',
        description: '利用Fastjson实现JNDI注入',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-18'
      },
      {
        id: 19,
        name: 'Log4j2漏洞利用',
        description: '复现Log4Shell远程代码执行漏洞',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-19'
      },
      
      // 框架漏洞相关实验
      {
        id: 20,
        name: 'ThinkPHP RCE漏洞',
        description: '利用ThinkPHP多版本远程代码执行漏洞',
        difficulty: 3,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-20'
      },
      {
        id: 21,
        name: 'Struts2表达式注入',
        description: '利用OGNL表达式实现代码执行',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-21'
      },
      {
        id: 22,
        name: 'Spring Cloud漏洞',
        description: '复现Spring Cloud Gateway远程代码执行漏洞',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-22'
      },
      
      // 业务逻辑漏洞相关实验
      {
        id: 23,
        name: '支付金额篡改',
        description: '在电商平台中实现支付金额修改',
        difficulty: 2,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-23'
      },
      {
        id: 24,
        name: '水平越权漏洞',
        description: '利用ID参数实现越权访问他人信息',
        difficulty: 3,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-24'
      },
      {
        id: 25,
        name: '短信验证码攻击',
        description: '实现短信轰炸与验证码复用攻击',
        difficulty: 3,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-25'
      },
      
      // 内网渗透相关实验
      {
        id: 26,
        name: 'CS木马植入',
        description: '使用Cobalt Strike植入后门',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-26'
      },
      {
        id: 27,
        name: '横向移动技术',
        description: '利用PTH/PTT技术在内网横向移动',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-27'
      },
      {
        id: 28,
        name: '域控提权',
        description: '利用DCSync实现域控提权',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-28'
      },
      
      // 代码审计相关实验
      {
        id: 29,
        name: 'CMS代码审计',
        description: '审计开源CMS系统中的SQL注入漏洞',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-29'
      },
      {
        id: 30,
        name: '反序列化链构造',
        description: '构造反序列化利用链实现代码执行',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-30'
      },
      
      // CTF相关实验
      {
        id: 31,
        name: 'Web渗透题解析',
        description: '解析2023年CTF中的Web渗透题型',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-03-31'
      },
      {
        id: 32,
        name: '二进制逆向分析',
        description: '分析CTF中的逆向工程题目',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-04-01'
      },
      {
        id: 33,
        name: '密码破解技术',
        description: '掌握常见密码学题型的解题思路',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-04-02'
      },
      
      // 红队武器库相关实验
      {
        id: 34,
        name: 'Cobalt Strike进阶',
        description: '深度使用CS 4.9进行红队协同作战',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-04-03'
      },
      {
        id: 35,
        name: '木马免杀技术',
        description: '使用Shellcode混淆和内存加载绕过杀软',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-04-04'
      },
      
      // 漏洞挖掘相关实验
      {
        id: 36,
        name: 'AFL模糊测试',
        description: '使用AFL进行智能模糊测试发现漏洞',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-04-05'
      },
      {
        id: 37,
        name: 'IDA Pro静态分析',
        description: '使用IDA Pro进行二进制程序分析',
        difficulty: 5,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-04-06'
      },
      {
        id: 38,
        name: 'GDB动态调试',
        description: '使用GDB追踪程序执行流程发现漏洞',
        difficulty: 4,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-04-07'
      },
      {
        id: 39,
        name: 'CVE申请流程',
        description: '学习漏洞披露和CVE申请全流程',
        difficulty: 3,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-04-08'
      },
      
      // CSRF相关实验
      {
        id: 40,
        name: 'CSRF漏洞利用',
        description: '学习跨站请求伪造攻击原理与防御',
        difficulty: 2,
        courseId: undefined,
        status: 'published',
        taskPoints: [],
        environment: {},
        studentCount: 0,
        completionRate: 0,
        averageScore: 0,
        createTime: '2024-04-09'
      }
    ]
  } catch (error) {
    console.error('获取实验列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 打开实验管理弹窗
const openExperimentModal = (course: Course) => {
  currentCourse.value = course
  fetchExperiments()
  showExperimentModal.value = true
}

// 获取该课程关联的实验列表
const getCourseExperiments = computed(() => {
  if (!currentCourse.value) return []
  const courseId = currentCourse.value.id
  return experimentList.value.filter(exp => {
    const experimentIds = courseExperiments.value.get(courseId) || []
    return experimentIds.includes(exp.id)
  })
})

// 获取可添加的实验列表（未关联当前课程的实验）
const getAvailableExperiments = computed(() => {
  if (!currentCourse.value) return []
  const courseId = currentCourse.value.id
  return experimentList.value.filter(exp => {
    const experimentIds = courseExperiments.value.get(courseId) || []
    return !experimentIds.includes(exp.id)
  })
})

// 添加实验到课程
const addExperimentToCourse = (experimentId: number) => {
  if (!currentCourse.value) return
  
  const courseId = currentCourse.value.id
  const experiments = courseExperiments.value.get(courseId) || []
  
  if (!experiments.includes(experimentId)) {
    experiments.push(experimentId)
    courseExperiments.value.set(courseId, experiments)
    
    // 更新课程的实验计数
    const course = courses.value.find(c => c.id === courseId)
    if (course) {
      course.experimentCount = experiments.length
    }
  }
}

// 从课程中移除实验
const removeExperimentFromCourse = (experimentId: number) => {
  if (!currentCourse.value) return
  
  const courseId = currentCourse.value.id
  let experiments = courseExperiments.value.get(courseId) || []
  
  experiments = experiments.filter(id => id !== experimentId)
  courseExperiments.value.set(courseId, experiments)
  
  // 更新课程的实验计数
  const course = courses.value.find(c => c.id === courseId)
  if (course) {
    course.experimentCount = experiments.length
  }
}
</script>

<template>
  <div class="container mx-auto p-4 min-h-screen">
    <!-- 页面标题 -->
    <div class="flex justify-between items-center mb-6" :class="{ 'animate-fade-in': isLoaded }">
      <h1 class="text-2xl font-bold">课程管理</h1>
      <button class="btn btn-primary" @click="handleCreateCourse">
        <i class="fas fa-plus mr-2"></i>
        创建课程
      </button>
    </div>

    <!-- 搜索和筛选 -->
    <div class="card bg-base-100 shadow-xl mb-6" :class="{ 'animate-slide-up': isLoaded }" style="animation-delay: 0.2s">
      <div class="card-body">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">搜索</span>
            </label>
            <input type="text" class="input input-bordered" placeholder="搜索课程名称" v-model="filters.search" />
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">分类</span>
            </label>
            <select class="select select-bordered" v-model="filters.category">
              <option value="">全部</option>
              <option v-for="category in categories" :key="category" :value="category">
                {{ category }}
              </option>
            </select>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">难度</span>
            </label>
            <select class="select select-bordered" v-model="filters.difficulty">
              <option value="">全部</option>
              <option v-for="n in 5" :key="n" :value="n">{{ n }} 星</option>
            </select>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">状态</span>
            </label>
            <select class="select select-bordered" v-model="filters.status">
              <option value="">全部</option>
              <option value="published">已发布</option>
              <option value="draft">草稿</option>
              <option value="archived">已归档</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- 课程列表 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-8" :class="{ 'animate-fade-in': isLoaded }" style="animation-delay: 0.3s">
      <div v-for="(course, index) in filteredCourses" :key="course.id" class="card bg-base-100 shadow-xl hover:shadow-2xl transition-all duration-500 group backdrop-blur-sm" :style="{ animationDelay: `${index * 0.1}s` }" :class="{ 'animate-slide-up': isLoaded }">
        <!-- 课程封面 -->
        <figure class="relative overflow-hidden aspect-video">
          <img :src="course.cover" :alt="course.name" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" />
          <div class="absolute inset-0 bg-gradient-to-t from-base-100 to-transparent opacity-60"></div>
          <div class="absolute top-2 right-2">
            <div class="badge" :class="getStatusBadgeClass(course.status)">
              {{ getStatusText(course.status) }}
            </div>
          </div>
        </figure>

        <div class="card-body">
          <!-- 课程信息 -->
          <h2 class="card-title group-hover:text-primary transition-colors">
            {{ course.name }}
            <div class="text-sm font-normal text-yellow-500">
              {{ getDifficultyStars(course.difficulty) }}
            </div>
          </h2>
          <p class="text-base-content/70">{{ course.description }}</p>

          <!-- 课程统计 -->
          <div class="flex gap-4 my-2 text-sm text-base-content/60">
            <div class="flex items-center gap-1">
              <i class="fas fa-users text-primary/70"></i>
              <span>{{ course.studentCount }} 名学生</span>
            </div>
            <div class="flex items-center gap-1">
              <i class="fas fa-flask text-primary/70"></i>
              <span>{{ course.experimentCount }} 个实验</span>
              <button 
                class="btn btn-xs btn-circle btn-ghost hover:bg-primary/20"
                @click.stop="openExperimentModal(course)"
                title="添加实验">
                <i class="fas fa-plus text-primary"></i>
              </button>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions justify-end mt-4">
            <div class="flex gap-2">
              <button class="btn btn-sm btn-ghost gap-1 group-hover:scale-105 transition-transform"
                      @click.stop="handleStudents(course)">
                <i class="fas fa-users"></i>
                学生
              </button>
              <button class="btn btn-sm btn-ghost gap-1 group-hover:scale-105 transition-transform"
                      @click.stop="openExperimentModal(course)">
                <i class="fas fa-flask"></i>
                实验
              </button>
              <button class="btn btn-sm btn-ghost gap-1 group-hover:scale-105 transition-transform"
                      @click.stop="handleEdit(course)">
                <i class="fas fa-edit"></i>
                编辑
              </button>
              <button class="btn btn-sm btn-ghost gap-1 group-hover:scale-105 transition-transform text-error"
                      @click.stop="handleDelete(course)">
                <i class="fas fa-trash"></i>
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 实验管理弹窗 -->
    <dialog :open="showExperimentModal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box">
        <div class="flex justify-between items-center mb-4">
          <h3 class="font-bold text-lg">
            {{ currentCourse?.name }} - 实验管理
          </h3>
          <button class="btn btn-sm btn-circle btn-ghost" @click="showExperimentModal = false">
            <i class="fas fa-times"></i>
          </button>
        </div>

        <div v-if="loading" class="flex justify-center py-8">
          <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
        <div v-else>
          <!-- 当前课程关联的实验列表 -->
          <div v-if="getCourseExperiments.length > 0" class="mb-6">
            <h4 class="font-semibold text-base mb-2 flex items-center gap-2">
              <i class="fas fa-link text-primary"></i>
              已关联实验
            </h4>
            <div class="space-y-3">
              <div v-for="experiment in getCourseExperiments" :key="experiment.id" 
                   class="bg-base-200 rounded-lg p-3 flex justify-between items-center">
                <div>
                  <div class="font-medium">{{ experiment.name }}</div>
                  <div class="text-sm text-base-content/60">{{ experiment.description }}</div>
                  <div class="flex gap-2 items-center mt-1">
                    <span class="text-yellow-500 text-xs">{{ getDifficultyStars(experiment.difficulty) }}</span>
                    <span class="badge badge-sm" :class="getStatusBadgeClass(experiment.status)">
                      {{ getStatusText(experiment.status) }}
                    </span>
                  </div>
                </div>
                <button class="btn btn-sm btn-ghost hover:bg-error/20" 
                        @click="removeExperimentFromCourse(experiment.id)"
                        title="移除实验">
                  <i class="fas fa-unlink text-error"></i>
                </button>
              </div>
            </div>
          </div>
          <div v-else class="alert alert-info mb-6">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <span>该课程暂未关联任何实验</span>
          </div>

          <!-- 可添加的实验列表 -->
          <div>
            <h4 class="font-semibold text-base mb-2 flex items-center gap-2">
              <i class="fas fa-plus-circle text-primary"></i>
              添加实验
            </h4>
            <div v-if="getAvailableExperiments.length > 0" class="space-y-3">
              <div v-for="experiment in getAvailableExperiments" :key="experiment.id" 
                   class="bg-base-200 rounded-lg p-3 flex justify-between items-center">
                <div>
                  <div class="font-medium">{{ experiment.name }}</div>
                  <div class="text-sm text-base-content/60">{{ experiment.description }}</div>
                  <div class="flex gap-2 items-center mt-1">
                    <span class="text-yellow-500 text-xs">{{ getDifficultyStars(experiment.difficulty) }}</span>
                    <span class="badge badge-sm" :class="getStatusBadgeClass(experiment.status)">
                      {{ getStatusText(experiment.status) }}
                    </span>
                  </div>
                </div>
                <button class="btn btn-sm btn-primary" 
                        @click="addExperimentToCourse(experiment.id)">
                  <i class="fas fa-plus"></i>
                  添加
                </button>
              </div>
            </div>
            <div v-else class="alert">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              <span>已添加全部可用实验</span>
            </div>
          </div>
        </div>

        <div class="modal-action">
          <button class="btn" @click="showExperimentModal = false">关闭</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showExperimentModal = false">关闭</button>
      </form>
    </dialog>
  </div>
</template>

<style scoped>
.container {
  max-width: 1400px;
  height: 100%;
  overflow-y: auto;
}

.animate-fade-in {
  animation: fadeIn 0.8s ease-out forwards;
}

.animate-slide-up {
  opacity: 0;
  animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 卡片悬停效果 */
.card {
  cursor: pointer;
  transform-style: preserve-3d;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: center;
  will-change: transform;
  border: 1px solid rgba(0, 0, 0, 0.1);
  position: relative;
}

.card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border-color: rgba(0, 242, 254, 0.3);
  background: linear-gradient(45deg, rgba(0, 242, 254, 0.05), rgba(79, 172, 254, 0.05));
}

/* 图标动画 */
.fas {
  transition: transform 0.3s ease;
}

.card:hover .fas {
  transform: scale(1.1);
}

/* 标签动画 */
.badge {
  transition: all 0.3s ease;
}

.badge:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
