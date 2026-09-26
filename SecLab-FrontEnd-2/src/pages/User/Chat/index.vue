<template>
  <div class="min-h-screen flex flex-col mt-16">
    <!-- 顶部装饰线 -->
    <div class="h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent"></div>
    
    <div class="w-full mx-auto flex-grow flex flex-col px-0 py-0 sm:p-4">
      <div class="card bg-base-100 shadow-xl sm:border border-base-200 flex-grow flex flex-col h-[calc(100vh-2px)]">
        <div class="card-body p-0 flex flex-col flex-grow">
          <!-- 顶部栏 -->
          <div class="flex items-center justify-between p-4 border-b border-base-200 bg-base-100/90 backdrop-blur-sm sticky top-0 z-10">
            <div class="flex items-center gap-2">
              <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-lg">
                <i class="fas fa-shield-alt text-xl text-white"></i>
              </div>
              <div>
                <div class="flex items-center gap-1">
                  <h2 class="text-xl font-bold">Sec<span class="text-primary">Lab</span> AI</h2>
                  <div class="badge badge-primary badge-sm">Beta</div>
                </div>
                <p class="text-xs text-base-content/60">安全知识智能助手</p>
              </div>
            </div>
            <div class="flex gap-2">
              <div class="dropdown dropdown-end">
                <label tabindex="0" class="btn btn-sm btn-ghost">
                  <i class="fas fa-cog"></i>
                </label>
                <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52">
                  <li>
                    <a @click="clearMessages">
                      <i class="fas fa-trash-alt mr-2"></i>清空对话
                    </a>
                  </li>
                  <li>
                    <a @click="toggleTheme">
                      <i class="fas fa-moon mr-2"></i>切换主题
                    </a>
                  </li>
                  <li>
                    <a @click="switchToFloatingMode">
                      <i class="fas fa-external-link-alt mr-2"></i>悬浮窗模式
                    </a>
                  </li>
                </ul>
              </div>
            </div>
          </div>
          
          <!-- 聊天消息区域 - 修复高度设置 -->
          <div ref="chatContainer" class="flex-grow overflow-y-auto p-2 sm:p-4 space-y-4 bg-base-200/30" style="height: calc(100vh - 13rem);">
            <div v-if="messages.length === 0" class="flex flex-col items-center justify-start h-full text-center text-base-content/50">
              <div class="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-gradient-to-br from-primary/20 to-secondary/20 
                          flex items-center justify-center mb-4 animate-pulse">
                <i class="fas fa-shield-alt text-3xl sm:text-4xl text-primary"></i>
              </div>
              <h3 class="text-xl sm:text-2xl font-bold mb-2 bg-clip-text text-transparent 
                         bg-gradient-to-r from-primary via-secondary to-accent">
                SecLab AI 智能助手
              </h3>
              <div class="max-w-sm mt-2 text-base-content/70 px-4 text-sm sm:text-base">
                您的网络安全学习伙伴，可以解答安全知识、辅助安全学习、提供实验指导
              </div>
              
              <!-- 快速问题建议 - 改进响应式布局 -->
              <div class="mt-6 sm:mt-8 grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3 w-full max-w-2xl px-4">
                <button 
                  v-for="(suggestion, index) in suggestions" 
                  :key="index"
                  class="btn btn-outline btn-sm border-base-content/20 justify-start normal-case font-normal
                         hover:bg-primary/10 hover:border-primary/30 transition-all duration-300 text-xs sm:text-sm"
                  @click="askSuggestion(suggestion)"
                >
                  <i class="fas fa-question-circle text-primary/70 mr-2"></i>
                  {{ suggestion }}
                </button>
              </div>
            </div>
            
            <template v-else>
              <div
                v-for="(message, index) in messages"
                :key="index"
                class="mb-4 sm:mb-6" 
              >
                <!-- 用户消息 -->
                <div 
                  v-if="message.role === 'user'"
                  class="chat chat-end"
                >
                  <div class="chat-image avatar">
                    <div class="w-8 sm:w-10 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
                      <img 
                        src="https://api.dicebear.com/7.x/avataaars/svg?seed=user"
                        alt="用户"
                      />
                    </div>
                  </div>
                  <div class="chat-bubble chat-bubble-primary">
                    {{ message.content }}
                  </div>
                  <div class="chat-footer opacity-50 flex gap-2 text-xs">
                    <span>{{ formatTime(message.timestamp) }}</span>
                  </div>
                </div>

                <!-- AI回复 -->
                <div 
                  v-else
                  class="chat chat-start"
                >
                  <div class="chat-image avatar">
                    <div class="w-8 sm:w-10 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-md">
                      <i class="fas fa-shield-alt text-xs sm:text-sm text-white"></i>
                    </div>
                  </div>
                  <div class="chat-bubble chat-bubble-neutral p-0">
                    <!-- 思考过程部分 - 可折叠面板 -->
                    <div v-if="message.thinking && message.showThinking" class="collapse collapse-arrow bg-base-200/30 mb-3 rounded-lg">
                      <input type="checkbox" class="min-h-0" checked /> 
                      <div class="collapse-title py-2 px-3 min-h-0 flex items-center gap-2 text-base-content/70 text-xs font-medium">
                        <i class="fas fa-brain text-secondary"></i>
                        <span>思考过程</span>
                      </div>
                      <div class="collapse-content px-3 sm:px-4 pt-0">
                        <div class="text-xs sm:text-sm text-base-content/70 thinking-content p-3 sm:p-4">
                          <div v-if="message.isStreaming">
                            <MarkdownRenderer :content="message.thinking || ''" />
                            <span v-if="message.thinking" class="inline-block ml-1">
                              <span class="loading loading-dots loading-xs"></span>
                            </span>
                          </div>
                          <div v-else>
                            <MarkdownRenderer :content="message.thinking || ''" />
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    <!-- 回复内容 -->
                    <div class="p-3 sm:p-4" v-if="message.content || message.streamContent">
                      <div v-if="message.isStreaming">
                        <MarkdownRenderer :content="message.streamContent || ''" />
                      </div>
                      <div v-else>
                        <MarkdownRenderer :content="message.content" />
                      </div>
                    </div>
                    <div v-else class="flex items-center gap-2 p-3 sm:p-4">
                      <span class="loading loading-dots loading-sm"></span>
                      <span>思考中...</span>
                    </div>
                  </div>
                  <div class="chat-footer opacity-50 flex gap-2 text-xs">
                    <span>{{ formatTime(message.timestamp) }}</span>
                    <button 
                      v-if="message.content" 
                      class="opacity-50 hover:opacity-100" 
                      @click="copyToClipboard(message.content)"
                      title="复制内容"
                    >
                      <i class="fas fa-copy"></i>
                    </button>
                  </div>
                </div>
              </div>
              <!-- 添加底部额外空间确保最后的消息可见 -->
              <div class="h-24 sm:h-32 md:h-40"></div>
            </template>
          </div>

          <!-- 输入区域 - 改进响应式设计 -->
          <div class="border-t border-base-200 p-3 pt-4 sm:p-4 bg-base-100 sticky bottom-0">
            <div class="flex flex-col gap-2">
              <div class="flex items-center gap-2 mb-2">
                <div class="flex items-center tooltip tooltip-right" data-tip="启用后，AI将展示推理思考过程">
                  <button
                    class="btn btn-sm btn-outline rounded-full gap-1 px-3 border-base-content/30"
                    :class="{'btn-primary': enableThinking, 'border-primary': enableThinking}"
                    @click="enableThinking = !enableThinking"
                  >
                    <i class="fas fa-brain text-xs"></i>
                    <span class="text-xs">深度思考</span>
                    <div class="badge badge-xs" :class="enableThinking ? 'badge-primary' : 'badge-ghost'"></div>
                  </button>
                </div>
                <div v-if="enableThinking" class="text-xs text-base-content/60">
                  已开启深度思考模式，AI将展示分析过程
                </div>
              </div>
              <div class="join w-full">
                <textarea
                  class="textarea textarea-bordered join-item flex-1 min-h-[60px] max-h-[120px] resize-none focus:outline-primary text-sm sm:text-base"
                  placeholder="输入您的问题，例如：什么是XSS攻击？如何防范SQL注入？..."
                  v-model="inputMessage"
                  @keydown.enter.ctrl="handleSendMessage"
                  ref="inputField"
                ></textarea>
              </div>
              <div class="flex justify-between items-center">
                <div class="text-xs text-base-content/60">
                  按Ctrl+Enter发送
                </div>
                <div class="flex items-center gap-2">
                  <button
                    class="btn btn-sm btn-ghost" 
                    @click="clearInput"
                    title="清空输入"
                  >
                    <i class="fas fa-eraser"></i>
                  </button>
                  <button
                    class="btn btn-sm sm:btn-md btn-primary"
                    @click="handleSendMessage"
                    :disabled="isLoading || !inputMessage.trim()"
                  >
                    <i class="fas fa-paper-plane mr-2"></i>
                    发送
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 底部装饰线 -->
    <div class="h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import DOMPurify from 'dompurify'
import OpenAI from 'openai'
import MarkdownRenderer from '../../../components/MarkdownRenderer.vue'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  thinking?: string
  streamContent?: string
  isStreaming?: boolean
  showThinking?: boolean  // 添加标记，指示这条消息是否要显示思考过程
}

const AGENT_BASE_URL = import.meta.env.VITE_AGENT_BASE_URL || (import.meta.env.DEV ? 'http://localhost:8010' : '')

// 走 ai-agent-service 的 OpenAI 兼容代理：真实密钥留在服务端 .env，不进前端产物
const openai = new OpenAI({
  apiKey: 'seclab-proxy', // 占位值，代理端点不校验；真实 key 在 ai-agent-service
  dangerouslyAllowBrowser: true,
  baseURL: `${AGENT_BASE_URL}/api/llm`
})

const messages = ref<Message[]>([])
const inputMessage = ref('')
const isLoading = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
const inputField = ref<HTMLTextAreaElement | null>(null)
const enableThinking = ref(false)
const showThinking = ref(false)

// 添加平台相关的背景信息
const platformInfo = {
  name: "SecLab安全实验平台",
  description: "一个专注于网络安全教育的在线学习平台，提供理论学习和实践实验相结合的课程体系，支持多种类型的实验环境和互动学习方式。",
  features: [
    "提供网络安全、密码学、渗透测试等多领域课程",
    "支持在线实验环境，可进行实际操作练习",
    "课程分为模块化学习，每个模块包含理论知识和实验任务",
    "提供CTF竞赛训练和模拟环境",
    "支持团队协作和项目实践",
    "实时排行榜系统，记录学习成果和积分",
    "深度思考功能，展示AI分析过程",
    "学习进度跟踪，自适应学习路径推荐"
  ],
  courses: [
    {name: "网络安全基础", topics: ["安全基本概念", "网络协议安全", "Web安全入门", "密码学基础"]},
    {name: "密码学原理", topics: ["对称加密", "非对称加密", "哈希算法", "数字签名", "密钥交换协议"]},
    {name: "Web安全进阶", topics: ["XSS攻击", "CSRF攻击", "SQL注入", "文件上传漏洞", "命令注入"]}
  ],
  experimentModules: [
    {id: 1, name: "SQL注入基础", type: "Web安全", difficulty: 2},
    {id: 2, name: "数据库类型识别", type: "Web安全", difficulty: 2},
    {id: 3, name: "注入点检测方法", type: "Web安全", difficulty: 3},
    {id: 4, name: "理解SQL注入原理", type: "Web安全", difficulty: 3},
    {id: 5, name: "SQL注入防御技术", type: "Web安全", difficulty: 4},
    {id: 6, name: "绕过WAF技术", type: "Web安全", difficulty: 5},
    {id: 7, name: "XSS跨站脚本攻击", type: "Web安全", difficulty: 3},
    {id: 8, name: "CSRF跨站请求伪造", type: "Web安全", difficulty: 3},
    {id: 9, name: "文件上传漏洞", type: "Web安全", difficulty: 4},
    {id: 10, name: "密码学基础", type: "密码学", difficulty: 2},
    {id: 11, name: "对称加密算法", type: "密码学", difficulty: 3},
    {id: 12, name: "漏洞挖掘方法论", type: "系统安全", difficulty: 5},
    {id: 13, name: "哈希函数与数字签名", type: "密码学", difficulty: 3},
    {id: 14, name: "网络嗅探", type: "网络安全", difficulty: 3},
    {id: 15, name: "ARP欺骗", type: "网络安全", difficulty: 3},
    {id: 16, name: "DNS劫持", type: "网络安全", difficulty: 4},
    {id: 17, name: "DDoS攻击原理", type: "网络安全", difficulty: 4},
    {id: 18, name: "防火墙配置", type: "网络安全", difficulty: 3},
    {id: 19, name: "Linux系统加固", type: "系统安全", difficulty: 3},
    {id: 20, name: "Windows系统加固", type: "系统安全", difficulty: 3},
    {id: 21, name: "权限提升", type: "系统安全", difficulty: 4},
    {id: 22, name: "缓冲区溢出", type: "系统安全", difficulty: 5},
    {id: 23, name: "渗透测试方法论", type: "渗透测试", difficulty: 3},
    {id: 24, name: "信息收集", type: "渗透测试", difficulty: 2},
    {id: 25, name: "漏洞扫描", type: "渗透测试", difficulty: 3},
    {id: 26, name: "漏洞利用", type: "渗透测试", difficulty: 4},
    {id: 27, name: "后渗透与权限维持", type: "渗透测试", difficulty: 4},
    {id: 28, name: "渗透测试报告", type: "渗透测试", difficulty: 2}
  ],
  scoreboard: {
    description: "平台排行榜根据用户完成的实验任务和获得的总分进行排名",
    rankingFactors: [
      "总分：完成实验任务获得的分数总和",
      "完成任务数：成功完成的实验任务数量",
      "难度系数：难度更高的实验获得更多分数",
      "时间系数：实验完成时间影响分数获取",
      "创新性：解题方法的创新性会获得额外加分"
    ],
    timeRanges: ["周排行", "月排行", "总排行"],
    filters: ["实验类型", "班级", "时间范围"]
  },
  learningEnv: {
    description: "平台提供两种实验环境：操作环境和靶机环境",
    operationEnv: "操作环境是学生进行实验操作的工作区，提供各种安全工具和软件",
    targetEnv: "靶机环境是实验目标系统，包含特定的漏洞或安全问题供学生发现和利用"
  },
  questionTypes: [
    "选择题：测试基础概念理解",
    "开放题：需要学生提供详细解答",
    "实操题：需要在环境中完成特定操作并获取结果"
  ],
  learningPath: "学习路径通常从基础安全概念开始，然后进入专项技术学习，建议按照由易到难的顺序完成实验。通常先完成基础实验模块，再尝试综合性实验，最后进行实战演练，形成完整的安全技能体系。"
}

// 监听enableThinking变化，同步更新showThinking
watch(enableThinking, (newValue) => {
  showThinking.value = newValue
})

// 快速问题建议
const suggestions = [
  "什么是XSS攻击？",
  "如何防范SQL注入？",
  "请介绍常见的网络安全威胁",
  "什么是CSRF攻击？",
  "密码学基础知识有哪些？",
  "如何进行安全的代码审计？"
]

// 使用建议问题
const askSuggestion = (question: string) => {
  inputMessage.value = question
  handleSendMessage()
}

// 格式化时间
const formatTime = (date: Date) => {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// 格式化消息内容，支持markdown - 这个方法可以保留但不再使用
const formatMessageContent = (content: string) => {
  return content
}

// 复制到剪贴板
const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text)
    .then(() => {
      // 可以添加toast通知用户复制成功
      console.log('复制成功')
    })
    .catch(err => {
      console.error('复制失败:', err)
    })
}

// 清空消息
const clearMessages = () => {
  if (messages.value.length > 0 && confirm('确定要清空所有对话记录吗？')) {
    messages.value = []
  }
}

// 清空输入
const clearInput = () => {
  inputMessage.value = ''
  inputField.value?.focus()
}

// 切换主题
const toggleTheme = () => {
  const html = document.querySelector('html')
  if (html) {
    const currentTheme = html.getAttribute('data-theme')
    html.setAttribute('data-theme', currentTheme === 'night' ? 'light' : 'night')
  }
}

// 切换到悬浮窗模式
const switchToFloatingMode = () => {
  // 将当前消息存储到本地存储，以便悬浮窗可以加载
  localStorage.setItem('chatMessages', JSON.stringify(messages.value))
  // 导航到悬浮窗演示页面
  window.location.href = '#/user/floating-chat-demo'
}

// 滚动到底部
const scrollToBottom = () => {
  if (chatContainer.value) {
    // 使用更长的延时确保DOM完全更新
    setTimeout(() => {
      if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight + 200
      }
    }, 100)
  }
}

// 检测用户问题是否与平台相关
const isPlatformRelatedQuestion = (question: string): boolean => {
  const platformKeywords = [
    "平台", "SecLab", "安全实验", "课程", "模块", "学习路径", "实验", "CTF", 
    "怎么使用", "如何开始", "功能", "特点", "课程内容", "学习计划", "SecLab平台",
    "安全学习", "实验环境", "账号", "注册", "登录", "学习进度", "证书", "成绩",
    "积分", "排名", "排行榜", "实验任务", "操作环境", "靶机", "SQL注入", "XSS",
    "Web安全", "网络安全", "密码学", "渗透测试", "系统安全", "学时", "难度",
    "题解", "思考模式", "教师", "分数", "技能树", "实验报告", "练习"
  ]
  
  // 转换为小写进行匹配
  const lowercaseQuestion = question.toLowerCase()
  return platformKeywords.some(keyword => 
    lowercaseQuestion.includes(keyword.toLowerCase())
  )
}

// 增强用户问题，添加平台相关上下文
const enhanceUserQuestion = (question: string): string => {
  if (!isPlatformRelatedQuestion(question)) {
    // 如果不是平台相关问题，保持原样
    return question
  }
  
  // 为平台相关问题添加上下文
  let enhancedPrompt = `关于SecLab安全实验平台的问题：${question}\n\n请根据以下SecLab平台详细信息回答：\n`;
  
  // 检查是否包含特定关键词，有针对性地添加相关上下文
  const lowerQuestion = question.toLowerCase();
  
  // 添加课程相关信息
  if (lowerQuestion.includes("课程") || lowerQuestion.includes("学习")) {
    enhancedPrompt += "【课程信息】\n";
    platformInfo.courses.forEach(course => {
      enhancedPrompt += `- ${course.name}：${course.topics.join("、")}\n`;
    });
    enhancedPrompt += "\n";
  }
  
  // 添加实验模块相关信息
  if (lowerQuestion.includes("实验") || lowerQuestion.includes("模块") || 
      lowerQuestion.includes("练习") || lowerQuestion.includes("sql") || 
      lowerQuestion.includes("xss") || lowerQuestion.includes("安全")) {
    enhancedPrompt += "【实验模块】\n平台提供28个实验模块，包括：\n";
    const modules = platformInfo.experimentModules.map(m => `${m.name}(难度:${m.difficulty}星)`);
    // 根据类型分组
    const moduleTypes = [...new Set(platformInfo.experimentModules.map(m => m.type))];
    moduleTypes.forEach(type => {
      enhancedPrompt += `- ${type}领域：${platformInfo.experimentModules
        .filter(m => m.type === type)
        .map(m => m.name)
        .join("、")}\n`;
    });
    enhancedPrompt += "\n";
  }
  
  // 添加排行榜相关信息
  if (lowerQuestion.includes("排行") || lowerQuestion.includes("排名") || 
      lowerQuestion.includes("积分") || lowerQuestion.includes("分数") || 
      lowerQuestion.includes("成绩") || lowerQuestion.includes("总分")) {
    enhancedPrompt += "【排名系统】\n";
    enhancedPrompt += `${platformInfo.scoreboard.description}\n`;
    enhancedPrompt += "排名依据：\n";
    enhancedPrompt += "- 排行榜主要根据用户的总分进行排名，总分越高排名越靠前\n";
    enhancedPrompt += "- 总分来源于完成的实验任务，难度越高的实验获得的分数越多\n";
    enhancedPrompt += "- 可按实验类型、班级和时间范围筛选排行榜\n";
    enhancedPrompt += "\n";
  }
  
  // 添加学习环境相关信息
  if (lowerQuestion.includes("环境") || lowerQuestion.includes("靶机") || 
      lowerQuestion.includes("操作") || lowerQuestion.includes("实验工具")) {
    enhancedPrompt += "【学习环境】\n";
    enhancedPrompt += `${platformInfo.learningEnv.description}\n`;
    enhancedPrompt += `- 操作环境：${platformInfo.learningEnv.operationEnv}\n`;
    enhancedPrompt += `- 靶机环境：${platformInfo.learningEnv.targetEnv}\n\n`;
  }
  
  // 如果没有匹配到特定类别，添加平台概览
  if (!enhancedPrompt.includes("【")) {
    enhancedPrompt += "【平台概览】\n";
    enhancedPrompt += `${platformInfo.description}\n\n`;
    enhancedPrompt += "主要功能：\n";
    platformInfo.features.slice(0, 5).forEach(feature => {
      enhancedPrompt += `- ${feature}\n`;
    });
    enhancedPrompt += "\n";
  }
  
  return enhancedPrompt;
}

// 构建更详细的系统提示词
const getSystemPrompt = (): string => {
  return `你是SecLab安全实验平台（${platformInfo.name}）的AI助手，专注于网络安全领域知识和平台使用指导。

平台信息：
${platformInfo.description}

平台主要功能：
${platformInfo.features.map(f => "- " + f).join("\n")}

平台课程内容：
${platformInfo.courses.map(c => `- ${c.name}：${c.topics.join("、")}`).join("\n")}

平台实验模块：
平台提供28个实验模块，涵盖Web安全、网络安全、密码学、系统安全和渗透测试五大领域。
难度从1星(入门)到5星(专家级)不等，实验类型包括理论学习和实践操作。
每个实验模块包含多个知识点和评分题目，完成后可获得相应积分。

排行榜系统：
${platformInfo.scoreboard.description}
排名主要根据用户的总分进行排名，总分高的用户排名靠前。总分通过完成实验任务获得，难度高的实验可获得更多分数。
支持按${platformInfo.scoreboard.timeRanges.join("、")}查看排名，可按${platformInfo.scoreboard.filters.join("、")}进行筛选。

学习环境：
${platformInfo.learningEnv.description}
- 操作环境：${platformInfo.learningEnv.operationEnv}
- 靶机环境：${platformInfo.learningEnv.targetEnv}

题目类型：
${platformInfo.questionTypes.join("\n")}

学习路径：
${platformInfo.learningPath}

你的角色：
1. 回答网络安全领域的专业问题，提供准确、专业的知识
2. 指导用户如何使用SecLab平台及其功能
3. 推荐合适的学习路径和课程内容
4. 解答实验过程中遇到的问题
5. 帮助用户理解网络安全概念和实验原理
6. 解释平台积分和排名规则

回答规则：
- 当用户询问平台相关问题时，基于上述平台信息提供具体、准确的回答
- 当用户询问网络安全知识时，提供专业、清晰的解释
- 如不确定，请诚实地表明不知道，避免提供错误信息
- 回答应使用专业且友好的语气，尽量简洁明了
- 优先推荐平台上的学习资源和课程
- 根据问题自然地引用相关实验模块，鼓励用户尝试相关实验`
}

// 调用OpenAI API
const callOpenAI = async (userQuestion: string, messageIndex: number) => {
  messages.value[messageIndex].isStreaming = true
  messages.value[messageIndex].streamContent = ''
  
  // 初始化思考过程流内容并记录消息的思考显示状态
  messages.value[messageIndex].showThinking = enableThinking.value
  if (enableThinking.value) {
    messages.value[messageIndex].thinking = ''
  }
  
  try {
    // 构建消息历史
    const messageHistory = messages.value
      .slice(0, messageIndex)
      .map(msg => {
        if (msg.role === 'user') {
          // 向用户消息添加平台相关上下文
          return {
            role: msg.role,
            content: isPlatformRelatedQuestion(msg.content) ? enhanceUserQuestion(msg.content) : msg.content
          }
        }
        return {
          role: msg.role,
          content: msg.content
        }
      })
    
    // 添加增强的系统消息
    messageHistory.unshift({
      role: 'system',
      content: getSystemPrompt()
    } as any)

    // 构建请求参数
    const requestParams: any = {
      model: enableThinking.value ? 'deepseek-reasoner' : 'deepseek-chat',
      messages: messageHistory,
      temperature: 0.7,
      stream: true,
    }
    
    // 使用OpenAI SDK的流式API
    const stream = await openai.chat.completions.create(requestParams)

    let completeResponse = ''
    let completeThinking = ''
    
    // 处理流式响应
    for await (const chunk of stream) {
      // 处理普通内容
      const content = chunk.choices[0]?.delta?.content || ''
      if (content) {
        completeResponse += content
        messages.value[messageIndex].streamContent = completeResponse
        // 在每次更新内容后都滚动到底部
        nextTick(() => {
          scrollToBottom()
        })
      }
      
      // 处理思考过程
      if (enableThinking.value) {
        const reasoningContent = chunk.choices[0]?.delta?.reasoning_content || ''
        if (reasoningContent) {
          completeThinking += reasoningContent
          messages.value[messageIndex].thinking = completeThinking
        }
      }
    }
    
    // 更新最终完整回答
    messages.value[messageIndex].content = completeResponse
    messages.value[messageIndex].isStreaming = false
    
    
  } catch (error: any) {
    messages.value[messageIndex].streamContent = ''
    messages.value[messageIndex].content = `调用API时出错: ${error.message || '未知错误'}`
    messages.value[messageIndex].isStreaming = false
  }
}

// 发送消息
const handleSendMessage = () => {
  if (!inputMessage.value.trim() || isLoading.value) return

  // 在消息界面显示原始用户输入
  const newMessage: Message = {
    role: 'user',
    content: inputMessage.value,
    timestamp: new Date()
  }

  messages.value.push(newMessage)
  const userQuestion = inputMessage.value
  inputMessage.value = ''
  
  // 自动滚动到底部
  scrollToBottom()
  
  // 添加加载状态的消息
  isLoading.value = true
  const responseIndex = messages.value.length
  messages.value.push({
    role: 'assistant',
    content: '',
    timestamp: new Date()
  })
  
  // 确保滚动到底部
  scrollToBottom()
  // 再次确保滚动到底部（解决某些浏览器渲染延迟问题）
  setTimeout(scrollToBottom, 100)
  setTimeout(scrollToBottom, 300)
  
  // 调用OpenAI API - 传入原始问题，增强会在API调用中进行
  callOpenAI(userQuestion, responseIndex)
    .finally(() => {
      isLoading.value = false
      // 回答完成后再次滚动到底部
      scrollToBottom()
      setTimeout(scrollToBottom, 100)
    })
}

// 优化监听消息变化的滚动处理
watch(messages, () => {
  // 使用nextTick确保DOM更新后再滚动
  nextTick(() => {
    scrollToBottom()
    // 再次滚动，确保内容完全可见
    setTimeout(() => {
      scrollToBottom()
    }, 200)
  })
}, { deep: true })

// 组件挂载后，聚焦输入框
onMounted(() => {
  inputField.value?.focus()
  // 确保聊天记录显示在底部
  nextTick(() => {
    scrollToBottom()
  })
})
</script>

<style scoped>
:deep(.chat-bubble) {
  max-width: 80%; /* 修改气泡最大宽度 */
  word-break: break-word;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1); /* 添加轻微阴影 */
}

:deep(.chat-bubble a) {
  color: var(--p);
  text-decoration: underline;
}

:deep(.chat-bubble pre) {
  background-color: hsl(var(--n) / 0.1);
  padding: 0.75rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  margin: 0.5rem 0;
}

:deep(.chat-bubble code) {
  background-color: hsl(var(--n) / 0.1);
  padding: 0.2rem 0.4rem;
  border-radius: 0.25rem;
  font-size: 0.9em;

}


:deep(.chat-bubble ul, .chat-bubble ol) {
  padding-left: 1.5rem;
  margin: 0.5rem 0;
}

:deep(.chat-bubble ul) {
  list-style-type: disc;
}

:deep(.chat-bubble ol) {
  list-style-type: decimal;
}

/* 机器人图标居中样式 */
.avatar .rounded-full {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.avatar .fas.fa-shield-alt, .avatar .fas.fa-brain {
  display: block;
  line-height: 1;
  margin: 0;
  padding: 0;
}

/* 思考过程样式 */
.collapse-arrow .collapse-title:after {
  top: 1.2rem;
  right: 1rem;
}

.thinking-content :deep(p) {
  margin-bottom: 0.5rem;
}

.thinking-content :deep(ol), .thinking-content :deep(ul) {
  margin-top: 0.25rem;
  margin-bottom: 0.5rem;
}

/* 确保折叠面板内部内容缩进和样式正确 */
.collapse-content {
  padding-bottom: 0.5rem;
}

.collapse .collapse-title {
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
}

/* 确保聊天区域和输入区域没有重叠 */
.chat-start:last-child,
.chat-end:last-child {
  margin-bottom: 1rem;
}

/* 确保气泡底部内容可见 */
.chat-bubble {
  margin-bottom: 0.25rem;
}

/* 添加响应式布局样式 */
@media (max-width: 640px) {
  :deep(.chat-bubble) {
    max-width: 88%;
  }
  
  .card {
    margin: 0;
    border-radius: 0;
    box-shadow: none;
  }
  
  :deep(.markdown-body) {
    font-size: 0.9rem;
  }
  
  /* 修复移动端底部内边距 */
  .chat-start:last-child,
  .chat-end:last-child {
    margin-bottom: 0.75rem;
  }
}
</style> 
