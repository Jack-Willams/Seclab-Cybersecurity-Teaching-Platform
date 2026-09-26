<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { ModuleOverViewType } from './components/ModuleOverView.ts'
import ModuleOverView from './components/ModuleOverView.vue'
import PageHero from '../../../components/PageHero.vue'

// 修改模块数据，添加分数计算
const calculateScore = (difficulty: number, time: string): number => {
  // 解析预计用时，提取小时数
  const hours = parseFloat(time.split('-')[1]?.split('小时')[0] || time.split('小时')[0])
  // 计算总分：难度基础分 + 时间加成，上限100分
  const score = Math.min(difficulty * 15 + hours * 5, 100)
  return Math.round(score)
}

// 模拟模块数据
const modules = ref<ModuleOverViewType[]>([
  {
    id: 1,
    name: 'SQL注入基础实验',
    description: '学习Web安全的基本概念和常见漏洞类型，包括SQL注入、XSS等。适合安全学习的入门者。',
    difficulty: 3,
    type: 'Web安全',
    status: 'available',
    estimatedTime: '2-3小时',
    score: calculateScore(3, '2-3小时'), // 65分：难度3×15 + 3小时×5
    image: '/cover-sql.png'
  },
  {
    id: 2,
    name: 'XSS跨站脚本攻击实验',
    description: '学习XSS跨站脚本攻击的原理、分类和防御方法，包括反射型、存储型和DOM型XSS。',
    difficulty: 2,
    type: 'Web安全',
    status: 'available',
    estimatedTime: '2-3小时',
    score: calculateScore(2, '2-3小时'), // 45分：难度2×15 + 3小时×5
    image: '/cover-xss.png'
  },
  {
    id: 3,
    name: 'CSRF跨站请求伪造实验',
    description: '学习CSRF攻击的原理和防御方法，包括Token验证、同源检查等安全措施。',
    difficulty: 3,
    type: 'Web安全',
    status: 'available',
    estimatedTime: '3-4小时',
    score: calculateScore(3, '3-4小时'), // 65分：难度3×15 + 4小时×5
    image: '/cover-csrf.png'
  },
  {
    id: 4,
    name: '命令注入漏洞实验',
    description: '学习命令注入漏洞的原理、危害和防御方法，实践各种命令注入攻击技术。',
    difficulty: 2,
    type: 'Web安全',
    status: 'available',
    estimatedTime: '2小时',
    score: calculateScore(2, '2小时'), // 40分：难度2×15 + 2小时×5
    image: '/cover-command-injection.png'
  },
  {
    id: 5,
    name: '文件上传漏洞实验',
    description: '学习文件上传漏洞的原理和利用方法，包括绕过客户端验证、服务器端验证等技术。',
    difficulty: 3,
    type: 'Web安全',
    status: 'available',
    estimatedTime: '2小时',
    score: calculateScore(3, '2小时'), // 55分：难度3×15 + 2小时×5
    image: '/3.文件上传漏洞突破 .png'
  },
  {
    id: 6,
    name: '目录遍历',
    description: '学习目录遍历漏洞的原理和利用方法，包括路径遍历、敏感文件读取、目录遍历绕过等技术。通过实战演练掌握目录遍历漏洞的发现、利用和防护方法。',
    difficulty: 3,
    type: 'Web安全',
    status: 'available',
    estimatedTime: '2小时',
    score: calculateScore(3, '2小时'), // 55分：难度3×15 + 2小时×5
    image: '/cover-directory-traversal.png'
  },
  {
    id: 15,
    name: '栈溢出实验',
    description: '在操作环境中自己编写栈溢出程序，用 pwndbg 定位溢出点、pwntools 编写 exp 劫持返回地址拿到本地 shell，再连接真实远程靶机完成 getshell 拿 flag。',
    difficulty: 3,
    type: '二进制安全',
    status: 'available',
    estimatedTime: '2-3小时',
    score: calculateScore(3, '2-3小时'), // 65分：难度3×15 + 3小时×5
    image: '/cover-stack-overflow.png'
  },
  {
    id: 16,
    name: '协议分析实战',
    description: '在抓包数据、HTTP 请求日志与安全事件日志三类数据中做协议分析：读懂 TCP/IP 分层与三次握手、定位 HTTP 会话中明文传输的敏感信息、从告警日志里还原攻击链并找出隐藏的 Flag。',
    difficulty: 3,
    type: '网络攻击与防御',
    status: 'available',
    estimatedTime: '2-3小时',
    score: calculateScore(3, '2-3小时'), // 65分：难度3×15 + 3小时×5
    image: '/协议分析实战.png'
  },
  {
    id: 7,
    name: '组件漏洞挖掘',
    description: '通过静态代码分析和动态测试发现第三方组件安全隐患，深入解析Shiro RememberMe反序列化、Fastjson JNDI注入、Log4j2远程代码执行等高危组件漏洞',
    difficulty: 4,
    type: 'Web安全',
    status: 'locked',
    estimatedTime: '3小时',
    score: calculateScore(4, '3小时'), // 70分：难度4×15 + 3小时×5
    image: '/5.组件漏洞挖掘.png'
  },
  {
    id: 8,
    name: '业务逻辑漏洞实战',
    description: '基于真实电商平台业务流程，系统训练水平越权、垂直越权、支付金额篡改、订单重放攻击等典型业务逻辑漏洞的发现与利用方法',
    difficulty: 3,
    type: 'Web安全',
    status: 'locked',
    prerequisites: [1, 2, 3],
    estimatedTime: '3-4小时',
    score: calculateScore(3, '3-4小时'), // 65分：难度3×15 + 4小时×5
    image: '/7.业务逻辑漏洞实战.png'
  },
  {
    id: 9,
    name: '内网渗透技术',
    description: '从外网突破到内网控制的完整渗透链路实践，包括边界突破、域环境信息收集、横向移动、域控提权等高级内网渗透技术',
    difficulty: 5,
    type: '网络攻防',
    status: 'locked',
    prerequisites: [4, 6, 7],
    estimatedTime: '4-5小时',
    score: calculateScore(5, '4-5小时'), // 85分：难度5×15 + 5小时×5
    image: '/8.内网渗透技术.png'
  },
  {
    id: 10,
    name: '代码审计进阶',
    description: '使用静态分析与动态调试相结合的方法，基于真实开源CMS项目源码，系统训练漏洞点定位、参数流追踪、调用链分析等代码审计核心技能',
    difficulty: 4,
    type: '系统安全',
    status: 'locked',
    prerequisites: [6, 7],
    estimatedTime: '3-4小时',
    score: calculateScore(4, '3-4小时'), // 75分：难度4×15 + 4小时×5
    image: '/9.代码审计进阶.png'
  },
  {
    id: 11,
    name: 'CTF综合实战',
    description: '通过实战演练最新CTF赛题，全面提升Web渗透、二进制逆向、密码学、隐写分析等多领域安全技能，掌握高效解题思路与自动化工具开发方法',
    difficulty: 5,
    type: 'CTF',
    status: 'locked',
    prerequisites: [1, 2, 3, 4, 5],
    estimatedTime: '5小时',
    score: calculateScore(5, '5小时'), // 100分：难度5×15 + 5小时×5
    image: '/10.CTF攻防实战.png'
  },
  {
    id: 12,
    name: '红队武器库',
    description: '系统学习红队实战武器装备的使用与定制，包括Cobalt Strike高级功能应用、木马免杀技术、社会工程学钓鱼攻击、网络侦查等红队核心战术与技术',
    difficulty: 5,
    type: '网络攻防',
    status: 'locked',
    prerequisites: [9],
    estimatedTime: '4-5小时',
    score: calculateScore(5, '4-5小时'), // 100分：难度5×15 + 5小时×5
    image: '/11.红队武器库.png'
  },
  {
    id: 13,
    name: '漏洞挖掘方法论',
    description: '系统讲解从发现到利用的完整漏洞挖掘流程，包括模糊测试技术应用、静态代码分析方法、动态调试技巧、漏洞验证与利用开发以及CVE申请全过程',
    difficulty: 5,
    type: '系统安全',
    status: 'locked',
    prerequisites: [10],
    estimatedTime: '5小时',
    score: calculateScore(5, '5小时'), // 100分：难度5×15 + 5小时×5
    image: '/12.漏洞挖掘方法论.png'
  },
  {
    id: 14,
    name: '第三方框架漏洞',
    description: '整漏洞挖掘流程，包包括Thinkphp多种典型漏洞利用、Struts2多种典型漏洞利用、Spring框架典型漏洞利用、若依框架典型漏洞利用等实验内容',
    difficulty: 5,
    type: '系统安全',
    status: 'locked',
    prerequisites: [10],
    estimatedTime: '5小时',
    score: calculateScore(5, '5小时'), // 100分：难度5×15 + 5小时×5
    image: '/6.框架漏洞利用.png'
  }

])



onMounted(()=>{
  // 注意：后端 /stu/module/modules 目前只有 3 条数据（且含已下线的文件上传），
  // 放开这段会把页面从 16 个实验砍到 3 个。等库里补齐再切。
  // getModuleList().then((res)=>{
  //   modules.value = res.data;
  // })
  setTimeout(() => {
    isLoaded.value = true
  }, 100)
})

// 筛选条件（类型已经交给下面的分类芯片，这里只留难度和状态）
const filters = ref({
  difficulty: '',
  status: ''
})

// 添加搜索关键词
const searchQuery = ref('')

/**
 * 分类芯片。和课程页 (pages/User/Courses/index.vue) 用同一套 id/名称/图标，
 * 两个页面切换时分类词汇是一致的，不会出现「课程叫网络安全、实验叫网络攻防」。
 */
const categories = [
  { id: 'web', name: 'Web安全', icon: 'fa-globe' },
  { id: 'system', name: '系统安全', icon: 'fa-desktop' },
  { id: 'network', name: '网络安全', icon: 'fa-network-wired' },
  { id: 'crypto', name: '密码学', icon: 'fa-key' },
  { id: 'advanced', name: '高级威胁', icon: 'fa-shield-alt' },
  { id: 'binary', name: '二进制安全', icon: 'fa-microchip' },
]

/**
 * 卡片上的 type 是给人看的中文名，芯片要的是 id，中间得有张对照表。
 * 「网络攻防」和「网络攻击与防御」是同一件事的两种写法，都并到 network ——
 * 之前的写死列表里这两个名字一个都没有，内网渗透/红队武器库/CTF 三个实验
 * 任何类型选项都筛不出来。
 */
const TYPE_TO_CATEGORY: Record<string, string> = {
  'Web安全': 'web',
  '系统安全': 'system',
  '网络安全': 'network',
  '网络攻防': 'network',
  '网络攻击与防御': 'network',
  '密码学': 'crypto',
  'CTF': 'advanced',
  '二进制安全': 'binary',
}

const selectedCategory = ref('')

/**
 * 只渲染数据里真实存在的分类。
 * 把 6 个分类写死的话，「密码学」会是一个点了永远出空白页的死按钮 —— 现在没有密码学实验。
 */
const availableCategories = computed(() => {
  const present = new Set(
    modules.value.map((m) => TYPE_TO_CATEGORY[m.type]).filter(Boolean)
  )
  return categories.filter((c) => present.has(c.id))
})

const isLoaded = ref(false)

// 更新筛选逻辑
// 更新筛选逻辑
const filteredModules = computed(() => {
  // 首先进行筛选
  const filtered = modules.value.filter(module => {
    // 搜索过滤
    if (searchQuery.value && !module.name.toLowerCase().includes(searchQuery.value.toLowerCase()) &&
        !module.description.toLowerCase().includes(searchQuery.value.toLowerCase())) {
      return false
    }
    // 分类芯片
    if (selectedCategory.value && TYPE_TO_CATEGORY[module.type] !== selectedCategory.value) return false
    // 现有的筛选条件
    if (filters.value.status && module.status !== filters.value.status) return false
    if (filters.value.difficulty && module.difficulty !== parseInt(filters.value.difficulty)) return false
    return true
  })

  // 然后按照状态排序
  return filtered.sort((a, b) => {
    const statusOrder = {
      'available': 0,  // 可开始 排第一
      'locked': 1,     // 未解锁 排第二
      'completed': 2   // 已完成 排第三
    }
    return statusOrder[a.status] - statusOrder[b.status]
  })
})

// 有没有任何筛选生效 —— 决定要不要把「重置」按钮显示出来
const hasActiveFilter = computed(() =>
  Boolean(searchQuery.value || selectedCategory.value || filters.value.status || filters.value.difficulty)
)

// 重置筛选器
const resetFilters = () => {
  filters.value = {
    difficulty: '',
    status: ''
  }
  searchQuery.value = ''
  selectedCategory.value = ''
}

// 获取统计信息
const stats = computed(() => ({
  total: modules.value.length,
  completed: modules.value.filter(m => m.status === 'completed').length,
  available: modules.value.filter(m => m.status === 'available').length,
  locked: modules.value.filter(m => m.status === 'locked').length
}))
</script>

<template>
  <div class="container-fluid px-4 py-4 overflow-x-hidden min-h-screen">
    <!-- 页头和课程页共用 PageHero，两页切换时是连续的 -->
    <PageHero
      kicker="SEC LAB · 实验靶场"
      title="探索实验"
      subtitle="在真实靶机环境里动手，把课程里学到的攻防链路走一遍"
      :class="{ 'animate-fade-in': isLoaded }"
    />

    <!-- 统计信息：改用课程页那套紧凑规格（py-2 / text-xs / text-xl），
         原来的默认尺寸在 1280 投影上要吃掉快一半首屏 -->
    <div class="stats shadow w-full mb-6 bg-base-100 backdrop-blur-sm" :class="{ 'animate-slide-up': isLoaded }">
      <div class="stat py-2">
        <div class="stat-figure text-primary">
          <i class="fas fa-cube text-xl"></i>
        </div>
        <div class="stat-title text-xs">总实验数</div>
        <div class="stat-value text-primary text-xl">{{ stats.total }}</div>
      </div>

      <div class="stat py-2">
        <div class="stat-figure text-success">
          <i class="fas fa-check-circle text-xl"></i>
        </div>
        <div class="stat-title text-xs">已完成</div>
        <div class="stat-value text-success text-xl">{{ stats.completed }}</div>
      </div>

      <div class="stat py-2">
        <div class="stat-figure text-warning">
          <i class="fas fa-unlock text-xl"></i>
        </div>
        <div class="stat-title text-xs">可开始</div>
        <div class="stat-value text-warning text-xl">{{ stats.available }}</div>
      </div>

      <div class="stat py-2">
        <div class="stat-figure text-error">
          <i class="fas fa-lock text-xl"></i>
        </div>
        <div class="stat-title text-xs">未解锁</div>
        <div class="stat-value text-error text-xl">{{ stats.locked }}</div>
      </div>
    </div>

    <!-- 筛选栏：原来是一张 133px 高的卡片装四个大 select，
         换成课程页那条单行（搜索框 + 分类芯片），难度/状态保留成 select-sm 塞进同一行。
         允许换行，1280 投影下自然折成两行而不是压扁。 -->
    <div
      class="flex flex-col md:flex-row md:flex-wrap md:items-center gap-3 mb-6"
      :class="{ 'animate-slide-up': isLoaded }"
      style="animation-delay: 0.2s"
    >
      <div class="flex-1 min-w-[200px] relative">
        <input
          type="text"
          placeholder="搜索实验名称或描述..."
          class="input input-sm input-bordered w-full pl-8 pr-3 bg-base-100/70 focus:bg-base-100 transition-all duration-300 shadow-sm hover:shadow focus:shadow-md"
          v-model="searchQuery"
        />
        <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-xs text-base-content/50"></i>
      </div>

      <select class="select select-sm select-bordered bg-base-100/70" v-model="filters.difficulty">
        <option value="">全部难度</option>
        <option v-for="n in 5" :key="n" :value="n">{{ '★'.repeat(n) }}{{ '☆'.repeat(5 - n) }}</option>
      </select>

      <select class="select select-sm select-bordered bg-base-100/70" v-model="filters.status">
        <option value="">全部状态</option>
        <option value="available">可开始</option>
        <option value="locked">未解锁</option>
        <option value="completed">已完成</option>
      </select>

      <div class="flex flex-wrap gap-1">
        <button
          v-for="category in availableCategories"
          :key="category.id"
          class="btn btn-ghost btn-sm gap-1 text-xs"
          :class="{ 'btn-active': selectedCategory === category.id }"
          @click="selectedCategory = selectedCategory === category.id ? '' : category.id"
        >
          <i :class="['fas', category.icon]"></i>
          <span>{{ category.name }}</span>
        </button>
      </div>

      <!-- 有筛选生效时才出现：原来只有空结果页里才有重置入口，
           筛出东西但想清空的时候没地方点 -->
      <button v-if="hasActiveFilter" class="btn btn-ghost btn-sm gap-1 text-xs" @click="resetFilters">
        <i class="fas fa-rotate-left"></i>
        <span>重置</span>
      </button>
    </div>

    <!-- 实验列表：和课程页同一套断点，lg 起 4 列。
         封面是 aspect-[16/9]，列宽一降下来封面自然就不那么占地方了 -->
    <div
      class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
      :class="{ 'animate-fade-in': isLoaded }"
      style="animation-delay: 0.3s"
    >
      <template v-if="filteredModules.length">
        <div
          v-for="(module, index) in filteredModules"
          :key="module.id"
          :style="{ animationDelay: `${index * 0.05}s` }"
          class="animate-slide-up h-full"
        >
          <ModuleOverView :module="module" />
        </div>
      </template>

      <!-- 无结果提示 -->
      <div v-else class="col-span-full text-center py-6">
        <div class="text-4xl mb-2 text-base-content/30">
          <i class="fas fa-search"></i>
        </div>
        <h3 class="text-lg font-semibold mb-1">未找到匹配的实验</h3>
        <p class="text-sm text-base-content/70">试试调整筛选条件</p>
        <button class="btn btn-primary btn-sm mt-3" @click="resetFilters">重置筛选器</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container-fluid {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
}

html, body {
  overflow-x: hidden;
  margin: 0;
  padding: 0;
  width: 100%;
}

.input-group > span {
  padding: 0 1rem;
  display: flex;
  align-items: center;
  /* 原写法 var(--color-base-content/50) 把 Tailwind 的透明度语法塞进了变量名，整条声明失效 */
  color: oklch(var(--bc) / 0.7);
}

/* 入场动画和课程页保持一致：整块淡入，卡片逐张上浮（延迟由模板按 index 给） */
.animate-fade-in {
  animation: fadeIn 0.8s ease-out forwards;
}

.animate-slide-up {
  opacity: 0;
  animation: slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
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
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 统计卡片动画 */
.stat {
  transition: all 0.3s ease;
}

.stat:hover {
  transform: translateY(-2px);
}

.stat-figure {
  transition: transform 0.3s ease;
}

.stat:hover .stat-figure {
  transform: scale(1.1);
}

/* 搜索框样式 */
.input {
  transition: all 0.3s ease;
}

.input:focus {
  outline: none;
  border-color: oklch(var(--p));
}

/* 下拉框样式 */
.select {
  transition: all 0.3s ease;
}

.select:focus {
  outline: none;
  border-color: oklch(var(--p));
}

/* 选项悬停效果 */
.select option {
  padding: 0.5rem;
}

.select option:hover {
  background-color: oklch(var(--p));
  color: white;
}

/* 卡片内部边框 */
.border-b {
  border-bottom-width: 1px;
  border-color: oklch(var(--bc) / 0.1);
}

/* 磨砂玻璃效果 */
.backdrop-blur-sm {
  backdrop-filter: blur(8px);
}
</style>