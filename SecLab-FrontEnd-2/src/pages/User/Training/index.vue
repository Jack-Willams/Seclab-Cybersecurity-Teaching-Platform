<template>
  <div
    class="min-h-screen p-4 md:p-8 text-base-content relative overflow-hidden"
    :class="isNight ? 'bg-transparent' : 'bg-base-100'"
  >
    <!-- 背景装饰：暗色下 AmbientBackdrop 已有柔光，这两团再叠上去只会把星点洗淡 -->
    <template v-if="!isNight">
      <div class="absolute top-[-10%] right-[-5%] w-[40%] h-[40%] bg-primary/5 rounded-full blur-[100px] z-0"></div>
      <div class="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] bg-secondary/5 rounded-full blur-[120px] z-0"></div>
    </template>

    <div class="max-w-4xl mx-auto relative z-10 w-full">
      <!-- 头部栏 -->
      <div class="flex items-center justify-between mb-8 pb-4 border-b border-base-200">
        <div class="flex items-center gap-3">
          <button @click="exitTraining" class="btn btn-sm btn-ghost btn-circle">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          </button>
          <!-- ③ 二级页面标题回到实色 -->
          <h1 class="text-xl font-bold text-base-content">
            AI针对性强化训练 <span class="text-base font-normal text-base-content/60 ml-2">第 {{ currentRound }} 轮</span>
          </h1>
        </div>
        <div class="badge badge-primary badge-outline">无字母数字与空格的命令执行绕过</div>
      </div>

      <!-- 加载屏 -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-20 min-h-[50vh]">
        <span class="loading loading-spinner loading-lg text-primary mb-8"></span>
        <div class="text-lg font-medium text-base-content/80 text-center space-y-4">
          <p class="animate-pulse" v-show="loadingStep === 0">🔍 正在读取学生本课程的错题情况...</p>
          <p class="animate-pulse text-secondary" v-show="loadingStep === 1">🤖 正在分析薄弱点，自动生成精细化针对性习题...</p>
          <p class="animate-pulse text-success" v-show="loadingStep === 2">✅ 题目生成完毕，即将开始训练！</p>
        </div>
      </div>

      <!-- 做题屏 -->
      <div v-else-if="!submitted" class="space-y-6">
        <div class="alert alert-info shadow-sm bg-info/10 border-info/20 text-base-content mb-6">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-info shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <div>
            <h3 class="font-bold">智能陪练提示</h3>
            <div class="text-sm">系统已根据你前期的命令执行错题特征，为你推荐以下靶向题目。</div>
          </div>
        </div>

        <div v-for="(q, index) in currentQuestions" :key="q.id" class="card bg-base-200/50 border border-base-300 shadow-sm hover:border-primary/30 transition-colors">
          <div class="card-body p-6">
            <h3 class="text-lg font-bold mb-4 flex gap-2">
              <span class="text-primary">{{ index + 1 }}.</span> 
              <span>
                <span class="badge badge-sm badge-neutral mr-2 align-middle">{{ q.type === 'single' ? '单选' : q.type === 'multiple' ? '多选' : '判断' }}</span> 
                {{ q.question }}
              </span>
            </h3>

            <div class="space-y-3 pl-6">
              <!-- 单选题 / 判断题 -->
              <template v-if="q.type === 'single' || q.type === 'judge'">
                <label v-for="(opt, optIdx) in q.options" :key="optIdx" class="flex items-start gap-3 cursor-pointer p-3 rounded-lg hover:bg-base-100 transition-colors group border border-transparent hover:border-base-300">
                  <input type="radio" :name="'q-' + q.id" :value="getTypeValue(q.type, optIdx)" class="radio radio-primary radio-sm mt-0.5" v-model="answers[q.id]" />
                  <span class="text-base-content/80 group-hover:text-base-content">{{ opt }}</span>
                </label>
              </template>
              
              <!-- 多选题 -->
              <template v-if="q.type === 'multiple'">
                <label v-for="(opt, optIdx) in q.options" :key="optIdx" class="flex items-start gap-3 cursor-pointer p-3 rounded-lg hover:bg-base-100 transition-colors group border border-transparent hover:border-base-300">
                  <input type="checkbox" :value="getTypeValue(q.type, optIdx)" class="checkbox checkbox-primary checkbox-sm mt-0.5" v-model="answers[q.id]" />
                  <span class="text-base-content/80 group-hover:text-base-content">{{ opt }}</span>
                </label>
              </template>
            </div>
          </div>
        </div>

        <div class="flex justify-center pt-6 pb-12">
          <button @click="submitAnswers" class="btn btn-primary btn-wide shadow-lg shadow-primary/30" :disabled="!allAnswered">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
            提交答案并测词
          </button>
        </div>
      </div>

      <!-- 解析屏 -->
      <div v-else class="space-y-6 pb-12">
        
        <div class="text-center py-6 mb-4">
          <div class="inline-flex items-center justify-center w-20 h-20 rounded-full mb-4 shadow-xl" :class="score === 100 ? 'bg-success/20 text-success' : 'bg-warning/20 text-warning'">
            <span class="text-3xl font-bold">{{ score }}</span>
          </div>
          <h2 class="text-2xl font-bold">训练得分</h2>
          <p class="text-base-content/60 mt-2">AI 将根据本次作答情况调整下一轮训练难度</p>
        </div>

        <div v-for="(q, index) in currentQuestions" :key="'res-'+q.id" class="card bg-base-200/50 border shadow-sm" :class="isCorrect(q.id) ? 'border-success/30' : 'border-error/30'">
          <div class="card-body p-6">
            <div class="flex justify-between items-start gap-4">
              <h3 class="text-lg font-bold mb-4 flex gap-2">
                <span :class="isCorrect(q.id) ? 'text-success' : 'text-error'">{{ index + 1 }}.</span> 
                <span>
                   <span class="badge badge-sm badge-neutral mr-2 align-middle">{{ q.type === 'single' ? '单选' : q.type === 'multiple' ? '多选' : '判断' }}</span> 
                   {{ q.question }}
                </span>
              </h3>
              <div :class="isCorrect(q.id) ? 'text-success' : 'text-error'">
                <svg v-if="isCorrect(q.id)" xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              </div>
            </div>

            <div class="space-y-2 mb-6 pl-6">
               <div v-for="(opt, optIdx) in q.options" :key="optIdx" class="p-2 rounded flex items-start gap-2" :class="getOptionClass(q, optIdx)">
                  <div class="min-w-4 mt-0.5">
                    <div v-if="getOptionClass(q,optIdx).includes('text-success')" class="h-2 w-2 rounded-full bg-success translate-y-1"></div>
                    <div v-else-if="getOptionClass(q,optIdx).includes('text-error')" class="h-2 w-2 rounded-full bg-error translate-y-1"></div>
                    <div v-else class="h-2 w-2 rounded-full bg-base-300 translate-y-1"></div>
                  </div>
                  <span class="text-sm font-medium">{{ opt }}</span>
               </div>
            </div>

            <div class="rounded-xl overflow-hidden border border-base-300 bg-base-100 relative">
              <div class="absolute left-0 top-0 bottom-0 w-1" :class="isCorrect(q.id) ? 'bg-success' : 'bg-primary'"></div>
              <div class="p-4 pl-5">
                <div class="flex items-center gap-2 mb-2">
                   <span class="font-bold text-sm uppercase tracking-wider" :class="isCorrect(q.id) ? 'text-success' : 'text-primary'">🎯 AI 针对性解析</span>
                </div>
                <p class="text-sm leading-relaxed text-base-content/80 whitespace-pre-wrap">{{ q.explanation }}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="flex flex-col sm:flex-row justify-center items-center gap-4 pt-8 border-t border-base-200">
          <button @click="exitTraining" class="btn btn-ghost hover:bg-error/10 w-full sm:w-auto">
            退出训练
          </button>
          <button @click="nextRound" class="btn btn-primary shadow-lg shadow-primary/30 w-full sm:w-auto">
            继续针对化强化训练
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          </button>
        </div>

      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from '../../../composables/useTheme'

// 同 WelCome：暗色下让位给 layout 的 AmbientBackdrop，否则不透明的 base-100 会盖掉星空层
const { currentTheme } = useTheme()
const isNight = computed(() => currentTheme.value === 'night')

const router = useRouter()

// 假装的多轮题目数据结构
const allRounds = [
  // 第一轮
  [
    {
      id: 1, type: 'single', 
      question: '在命令执行场景中，若系统基础的读取文件命令被正则表达式黑名单过滤，以下哪种方式能最有效地绕过该限制？',
      options: ['A. 使用该命令的系统绝对路径', 'B. 使用花括号扩展特性，将读取命令和目标文件包含在内', 'C. 使用Base64编码绕过，例如将读取命令编码后通过系统的解码指令执行', 'D. 在原命令的字母中间强行插入反斜杠转义字符'],
      correctAnswer: 'C', explanation: 'C （当基础读取命令被正则黑名单完全拦截时，直接使用绝对路径或转义字符仍有可能触发更严格的正则匹配。使用Base64编码配合系统解码指令，可以从根本上隐藏原始的命令单词，是通用且高效的绕过方式。）'
    },
    {
      id: 2, type: 'single',
      question: '当目标环境过滤了空格，但保留了<时，读取系统密码文件的最佳构造方式是？',
      options: ['A. 正常键入读取命令，加空格和系统密码文件路径', 'B. 读取命令紧接输入<，再紧跟系统密码文件路径', 'C. 读取命令紧接内部字段分隔符系统变量，再紧跟系统密码文件路径', 'D. 读取命令紧接URL编码的空格，再紧跟系统密码文件路径'],
      correctAnswer: 'B', explanation: 'B （在被过滤了常规空格的情况下，如果系统保留了<，可以直接将其放在读取命令和目标文件路径之间。系统会将右侧文件的内容作为左侧命令的输入，全程不需要任何空格或额外的变量调用。）'
    },
    {
      id: 3, type: 'single',
      question: '在Linux系统命令行中，IFS是一个重要的内置属性。关于它的描述，下列哪项是正确的？',
      options: ['A. 该变量的默认值仅包含空格', 'B. 该变量无法用于分隔命令参数', 'C. 该变量默认包含空格、制表符和换行符，在漏洞利用中常用于绕过对空格的拦截', 'D. 该变量是特定后端编程语言（如PHP）专属的超全局变量'],
      correctAnswer: 'C', explanation: 'C （IFS是系统环境自带的内置变量，其默认值就包含了空格、制表符和换行符。在漏洞挖掘中，它经常被用来完美替代被安全策略拦截的常规空格。）'
    },
    {
      id: 4, type: 'single',
      question: '面对“无字母数字”的极端限制（例如安全策略完全过滤了所有英文字母和阿拉伯数字输入），利用后端语言特性构造执行语句时，以下哪种思路是可行的？',
      options: ['A. 直接调用系统级别的命令执行函数，并传入查看目录的指令', 'B. 利用空数组配合变量自增操作，或使用特殊符号进行异或运算来凭空构造所需字符', 'C. 使用打印命令配合星号通配符来列出目录文件', 'D. 使用读取命令配合问号和星号通配符来匹配文件路径'],
      correctAnswer: 'B', explanation: 'B （面对完全禁止字母和数字的极端情况，常规的系统命令或通配符都会失效。唯一的突破口是利用后端语言（如PHP）自身的特性，通过对无意义的特殊符号进行自增或异或等运算，在内存中动态生成我们需要的字母字符。）'
    },
    {
      id: 5, type: 'single',
      question: '关于通配符问号和星号在命令执行绕过中的应用，下列说法错误的是？',
      options: ['A. 问号可以代替并匹配任意单个字符', 'B. 星号可以匹配任意长度的任意字符（包括空字符）', 'C. 在系统命令路径中，将代表命令的最后一个字母替换为问号，其执行效果等同于原命令', 'D. 通配符属于Linux系统的专属特性，无法在Windows系统环境下使用'],
      correctAnswer: 'D', explanation: 'D （通配符并非Linux系统的专属。在Windows系统的命令行环境下，同样可以使用问号来代替单个字符，或者使用星号来代替多个字符进行模糊匹配。）'
    },
    {
      id: 6, type: 'multiple',
      question: '在命令执行漏洞利用中，为了绕过安全策略对“常规空格”的过滤，以下哪些系统特性或变量可以被用来作为替代？',
      options: ['A. 内部字段分隔符系统变量', 'B. 输入<', 'C. 系统的花括号扩展特性', 'D. 制表符的URL编码格式'],
      correctAnswer: ['A', 'B', 'C', 'D'], explanation: 'ABCD （这四项都是实战中替换常规空格的经典手段。包括利用内部字段分隔符系统变量、利用输入重定向符号、利用系统的花括号扩展特性将命令和参数包裹，以及直接使用制表符的URL编码格式。）'
    },
    {
      id: 7, type: 'multiple',
      question: '当目标环境的安全策略严格过滤了分号和管道符，但系统仍允许执行多条连续命令时，可以尝试使用以下哪些逻辑连接符或编码手段来拼接指令？',
      options: ['A. \'\'', 'B. ""', 'C. ||', 'D. 换行动作的URL编码格式（百分号零A）'],
      correctAnswer: ['A', 'B', 'C', 'D'], explanation: 'ABCD （当分号和常规管道符被禁用时，可以使用表示后台执行的逻辑连接符（单个和号）、表示条件执行的逻辑与（双个和号）、表示条件执行的逻辑或（双竖线），或者直接传入换行动作的URL编码来实现多条指令的串联运行。）'
    },
    {
      id: 8, type: 'multiple',
      question: '针对“无字母数字”的严苛代码执行限制环境，以下哪些编码或字符转换方式可能被用于辅助构造并绕过防御拦截？',
      options: ['A. 利用Base64编码及系统的对应解码指令组合', 'B. 利用十六进制编码及系统的对应数据还原指令组合', 'C. 通过字符转换函数将ASCII码拼接成所需命令', 'D. 使用经典的ROT13替换密码技术'],
      correctAnswer: ['A', 'B', 'C'], explanation: 'ABC （在极端的“无字母数字”环境下，技术人员主要依赖对特殊符号进行底层运算（如Base64解码、十六进制还原、ASCII码拼接等）来生成可用字符。而ROT13替换密码通常需要依赖现成的英文字母表进行移位操作，在连字母都无法输入的环境下，极难作为首选的绕过载荷。）'
    }
  ],
  // 第二轮
  [
    {
      id: 9, type: 'judge',
      question: '在Linux系统中，当我们把小于号放置在读取命令和目标文件路径之间时，该符号的实际作用是命令系统执行一个后台进程。',
      options: ['正确', '错误'],
      correctAnswer: '错误', explanation: '× （放置在命令和文件之间的该符号（小于号），其实际作用是“输入重定向”，也就是把文件的内容输入给前面的命令处理，而不是用来将任务放到后台执行的。）'
    },
    {
      id: 10, type: 'judge',
      question: '针对特定关键字的正则表达式拦截，攻击者通常可以通过在关键字的字母中间插入反斜杠转义符，或者插入空的一对双引号来成功打破连续性规则并实现绕过。',
      options: ['正确', '错误'],
      correctAnswer: '正确', explanation: '√ （在目标关键字的字母中间强行插入反斜杠转义符，或者插入空的一对双引号，在系统执行时会被忽略，但可以有效打断安全防护系统中正则表达式的连续字符串匹配。）'
    },
    {
      id: 11, type: 'judge',
      question: '代表系统命令行位置参数的数字型系统变量（数字一到九），在命令执行绕过的场景中，因为它们通常是没有值的空变量，所以经常被用来插入敏感字符串中以打乱关键字或辅助绕过空格限制。',
      options: ['正确', '错误'],
      correctAnswer: '正确', explanation: '√ （代表命令行位置参数的数字型系统变量（如数字一到九），在没有额外传参时默认为空。将它们插入到敏感命令中间，既不影响命令的最终执行，又能破坏关键字的完整性以绕过检测。）'
    },
    {
      id: 12, type: 'judge',
      question: '在后端代码中，用于执行动态脚本代码的函数与用于执行系统底层命令的函数，在面对完全无字母数字输入的极端限制时，两者的利用难度和底层的逃逸原理是完全一样的。',
      options: ['正确', '错误'],
      correctAnswer: '错误', explanation: '× （执行动态脚本代码的函数和执行系统底层命令的函数，在底层机制和参数解析方式上有本质的区别。因此在面对无字母数字的限制时，两者的逃逸原理和载荷构造难度是完全不同的。）'
    },
    {
      id: 13, type: 'judge',
      question: '异或运算逻辑在高级漏洞利用中常用于将两个无意义的特殊符号进行计算，从而得到常规的目标字母，这是在无字母数字限制下构建隐蔽后门程序的核心构造技巧之一。',
      options: ['正确', '错误'],
      correctAnswer: '正确', explanation: '√ （异或运算可以通过对两个非字母数字的特殊符号进行二进制位计算，从而得出常规的英文字母。这是目前绕过极端安全限制、构建隐蔽后门程序最核心、最底层的技术原理。）'
    }
  ]
]

// 状态管理
const currentRound = ref(1)
const loading = ref(true)
const loadingStep = ref(0)
const submitted = ref(false)
const answers = ref<Record<number, any>>({})

const currentQuestions = computed(() => {
  // 如果轮数超出预设，无限循环最后一轮（或重新开始）
  const idx = (currentRound.value - 1) % allRounds.length
  return allRounds[idx]
})

const getTypeValue = (type: string, idx: number) => {
  if (type === 'judge') {
    return idx === 0 ? '正确' : '错误'
  }
  return String.fromCharCode(65 + idx) // A, B, C, D...
}

// 初始化题目答案绑定
const initAnswers = () => {
  answers.value = {}
  currentQuestions.value.forEach(q => {
    answers.value[q.id] = q.type === 'multiple' ? [] : null
  })
}

// 播放加载动画
const playLoading = () => {
  loading.value = true
  submitted.value = false
  loadingStep.value = 0
  
  setTimeout(() => { loadingStep.value = 1 }, 1500)
  setTimeout(() => { loadingStep.value = 2 }, 3000)
  setTimeout(() => { 
    loading.value = false 
    initAnswers()
  }, 4000)
}

onMounted(() => {
  playLoading()
})

const allAnswered = computed(() => {
  for (const q of currentQuestions.value) {
    const ans = answers.value[q.id]
    if (q.type === 'multiple') {
      if (!ans || ans.length === 0) return false
    } else {
      if (ans === null) return false
    }
  }
  return true
})

const submitAnswers = () => {
  submitted.value = true
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const nextRound = () => {
  currentRound.value += 1
  playLoading()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const exitTraining = () => {
  router.push('/user/profile')
}

// 评判工具
const isCorrect = (id: number) => {
  const q = currentQuestions.value.find(x => x.id === id)
  if (!q) return false
  const userAns = answers.value[id]
  if (q.type === 'multiple') {
    if (!userAns || userAns.length !== q.correctAnswer.length) return false
    return (q.correctAnswer as string[]).every((val:string) => userAns.includes(val))
  }
  return userAns === q.correctAnswer
}

const getScore = () => {
  let rightCount = 0
  currentQuestions.value.forEach(q => {
    if (isCorrect(q.id)) rightCount++
  })
  return Math.round((rightCount / currentQuestions.value.length) * 100)
}

const score = computed(() => getScore())

const getOptionClass = (q: any, optIdx: number) => {
  const val = getTypeValue(q.type, optIdx)
  const isSelected = q.type === 'multiple' ? answers.value[q.id].includes(val) : answers.value[q.id] === val
  const isAnswer = q.type === 'multiple' ? q.correctAnswer.includes(val) : q.correctAnswer === val
  
  if (isAnswer) return 'bg-success/10 text-success font-bold'
  if (isSelected && !isAnswer) return 'bg-error/10 text-error line-through'
  return 'text-base-content/60'
}

</script>
