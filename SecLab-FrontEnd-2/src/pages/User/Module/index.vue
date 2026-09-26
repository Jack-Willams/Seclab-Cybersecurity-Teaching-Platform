<script setup lang="ts">
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import MarkdownRenderer from "../../../components/MarkdownRenderer.vue";
import VNCViewer from "../../../components/VNCViewer.vue";
import type { DisplayQuestionType } from '../../../types/Question';
import { ref, watch, computed, onMounted, onUnmounted } from 'vue';
import type {Experiment} from "../../../types/experiment.ts";
import type { Module } from './index.ts';
import { convertExperimentToModule } from './index.ts';
import axios from 'axios'
import { getModuleDetail, getUserInfo, startLabSession, submitFlagAnswer, submitQuestionAnswer, ingestEvents } from '../../../api';
import { findExperimentById } from '../../../data';
import {
  setLabRunning,
  clearLab,
  CONTAINER_NAMES,
  setLabSessionId,
  getLabSessionId,
  addLabEvent,
  getLabEvents,
  getLabDurationSeconds,
  currentLabContainer,
  setLabContext
} from '../../../composables/useLabState';
import { useCookie } from '../../../common';

const route = useRoute();
const router = useRouter();
const moduleId = route.params.id;
const isLoading = ref(true);
const cookie = useCookie();
const moduleStartedAt = Date.now();
const showEndExperimentModal = ref(false)
const isEndingExperiment = ref(false)

// 模拟实验数据 - 保留原有的experiment变量
const experiment = ref<Module>({
  id: 1,
  name: 'SQL注入基础实验',
  introduction: '本实验将帮助你理解SQL注入漏洞的原理和基本利用方法',
  difficulty: 3,
  taskPoints: [
    // ... 默认任务点
  ],
  targetMachine: {
    id: '550e8400-e29b-41d4-a716-446655440000'
  }
});

// 添加答案状态
const answerStatus = ref<{ [key: number]: { [key: number]: boolean | null } }>({})

// 存储答案 - 初始化为空对象
const answers = ref<{ [key: number]: { [key: number]: string | string[] } }>({})
const questionSubmitting = ref<{ [key: number]: { [key: number]: boolean } }>({})

// 添加 flag 提交状态和消息
const flagSubmitStatus = ref<{ 
  isSubmitted: boolean; 
  isSuccess: boolean; 
  message: string;
  taskId: number | null;
  questionId: number | null;
}>({
  isSubmitted: false,
  isSuccess: false,
  message: '',
  taskId: null,
  questionId: null
});

// 清除 flag 提交状态
const clearFlagStatus = () => {
  setTimeout(() => {
    flagSubmitStatus.value = {
      isSubmitted: false,
      isSuccess: false,
      message: '',
      taskId: null,
      questionId: null
    };
  }, 5000); // 5秒后自动清除状态
};

const getBaseLabId = () => {
  const currentId = Number(experiment.value.id) || Number(route.params.id) || 1
  return currentId >= 100 ? Math.floor(currentId / 100) : currentId
}

// 靶机环境尚未部署的实验：靶机页签只显示「建设中」占位，不启动任何靶机，
// 避免未映射 id 落到默认 SQL 靶机。（目前为空，栈溢出已接入真实靶机，见下方 PWN_TARGETS）
const TARGET_PENDING_MODULE_IDS: number[] = []
const isTargetPending = computed(() =>
  TARGET_PENDING_MODULE_IDS.includes(Number(experiment.value.id) || Number(route.params.id))
)

// TCP pwn 靶机（非 Web，无法用 iframe 展示）：靶机页签显示「连接信息」，
// 学生在操作环境桌面用 nc/pwntools 连接容器名:端口，getshell 拿 flag。
const PWN_TARGETS: Record<number, { container: string; port: number; startEndpoint: string }> = {
  15: { container: 'stack-overflow-lab-web-1', port: 70, startEndpoint: '/api/docker/start-stack' },
}
const pwnTarget = computed(() => PWN_TARGETS[Number(experiment.value.id) || Number(route.params.id)] || null)
const isPwnTarget = computed(() => Boolean(pwnTarget.value))

onMounted(async () => {
  try {
    // 如果没有提供模块ID，重定向到模块列表页面
    if (!moduleId) {
      console.log('未提供模块ID，重定向到模块列表');
      router.push('/user/modules');
      return;
    }
    
    // 尝试加载模块数据
    const id = Number(moduleId);
    console.log('当前请求的模块ID:', id, '类型:', typeof id);
    if (isNaN(id)) {
      console.error('无效的模块ID:', moduleId);
      throw new Error('无效的模块ID');
    }
    
    // 尝试从API获取数据，如果失败则使用本地数据
    try {
      console.log(`尝试从API获取ID为${id}的模块数据`);
      const response = await getModuleDetail(id);
      if (response.isSuccess === 1) {
        experiment.value = response.data as Module;
        console.log(`成功从API加载模块 #${id}: ${experiment.value.name}，实际ID: ${experiment.value.id}`);
      } else {
        console.warn(`API返回错误，尝试使用本地数据`);
        throw new Error('API返回错误');
      }
    } catch (error) {
      // 如果API调用失败，尝试使用本地数据
      console.log(`从本地数据查找ID为${id}的模块`);
      const localModule = findExperimentById(id);
      if (localModule) {
        // 转换为Module类型
        experiment.value = convertExperimentToModule(localModule);
        // 确保ID保持一致，不被覆盖
        const originalId = experiment.value.id;
        experiment.value.id = id;
        console.log(`使用本地数据加载模块 #${id}: ${experiment.value.name}，原始ID: ${originalId}，修正后ID: ${experiment.value.id}`);
      } else {
        console.error(`找不到ID为${id}的模块`);
        throw new Error(`找不到指定ID(${id})的模块`);
      }
    }
    
    // 在数据加载完成后再次确认ID是否正确
    console.log(`最终加载的模块: ID=${experiment.value.id}, 名称=${experiment.value.name}`);
    if (experiment.value.id !== id) {
      console.warn(`警告：模块ID不匹配！请求ID=${id}，实际ID=${experiment.value.id}`);
      experiment.value.id = id; // 强制修正ID
    }
    
    // 初始化答案状态和答案存储对象
    if (experiment.value && experiment.value.taskPoints) {
      experiment.value.taskPoints.forEach((task) => {
        if (!answerStatus.value[task.id]) {
          answerStatus.value[task.id] = {};
        }
        if (!answers.value[task.id]) {
          answers.value[task.id] = {};
        }
        if (task.questions) {
          task.questions.forEach((question) => {
            if (!answerStatus.value[task.id][question.id]) {
              answerStatus.value[task.id][question.id] = null;
            }
            // 初始化答案对象
            if (question.type === 'multiple-choice') {
              answers.value[task.id][question.id] = [];
            } else {
              answers.value[task.id][question.id] = '';
            }
          });
        }
      });
    }
    // 栈溢出等 TCP pwn 靶机一直默认在线：进入页面即自动准备（幂等启动 + 建立会话），
    // 使靶机徽章显示「运行中」、右侧连接卡默认展示，Flag 也可直接提交，无需手动点「准备靶机」。
    if (isPwnTarget.value) {
      void startTargetMachine();
    }
  } catch (error) {
    console.error('加载模块数据失败:', error);
    // 使用内联通知替代alert
    pointsNotification.value = {
      show: true,
      message: '加载模块数据失败，将返回模块列表'
    };
    // 延迟导航，让用户有时间看到通知
    setTimeout(() => {
      router.push('/user/modules');
    }, 2000);
  } finally {
    isLoading.value = false;
  }
});

// 添加状态控制
const showNoVNC = ref(false)
const isOperationMachineRunning = ref(false)
const isTargetMachineRunning = ref(false)

// 添加加载状态
const isTargetLoading = ref(false)

// 添加操作环境加载状态
const isOperationLoading = ref(false)

// 添加环境管理变量
const activeEnvironmentTab = ref<'operation' | 'target' | null>(null);
const targetMachineUrl = ref('')
const labSessionId = ref('')
const currentTargetContainerName = ref('')
const operationSessionId = ref('')
const operationVncWsUrl = ref('')
const operationVncPassword = '123456'
type TargetMachineStatus = 'offline' | 'starting' | 'online'

interface DockerTargetStatus {
  lab?: string
  containerId?: string
  containerExists?: boolean
  containerRunning?: boolean
  hostPort?: number | null
  portListening?: boolean
  targetUrl?: string | null
  httpReachable?: boolean
  httpStatus?: number | null
  status?: TargetMachineStatus
  message?: string
  reason?: string
}

const DOCKER_API_URL =
  import.meta.env.VITE_DOCKER_API_URL ||
  (import.meta.env.DEV ? "http://localhost:3000" : "");
const targetMachineStatus = ref<TargetMachineStatus>('offline')
const targetMachineMessage = ref('靶机环境未启动')
const targetStatusDetail = ref<DockerTargetStatus | null>(null)
const targetIframeState = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')

const normalizeEventType = (value: unknown) => String(value || '').trim().toUpperCase()

const moduleCategoryLabel = computed(() => {
  const labels: Record<number, string> = {
    1: 'SQL 注入',
    2: 'XSS 漏洞',
    3: 'CSRF 漏洞',
    4: '命令注入',
    5: '文件上传',
    6: '目录遍历',
    16: '协议分析'
  }
  return labels[getBaseLabId()] || '综合安全实验'
})

const hasLiveTargetUrl = computed(() => targetMachineStatus.value === 'online' && Boolean(targetMachineUrl.value))
const liveTargetHint = computed(() => '靶机环境未获取到实时地址')
const targetStatusBadgeClass = computed(() => {
  if (isTargetLoading.value || targetMachineStatus.value === 'starting') return 'badge-warning'
  return targetMachineStatus.value === 'online' ? 'badge-success' : 'badge-error'
})
const targetStatusLabel = computed(() => {
  if (isTargetLoading.value) return '启动中'
  if (targetMachineStatus.value === 'online') return '运行中'
  if (targetMachineStatus.value === 'starting') return '启动中'
  return '未就绪'
})
const targetPanelVisible = computed(() => activeEnvironmentTab.value === 'target' && (isPwnTarget.value || isTargetPending.value || isTargetLoading.value || targetMachineStatus.value !== 'offline' || Boolean(targetMachineUrl.value)))
const operationTargetUrl = computed(() => {
  const urls: Record<number, string> = {
    1: 'http://sqli-lab-web-1/index.php',
    2: 'http://xss-lab-web-1/index.php',
    3: 'http://csrf-lab-web-1/index.php',
    4: 'http://command-inject-web-1/index.html',
    5: 'http://file-upload-lab-web-1/index.php',
    6: 'http://directory-traversal-lab-web-1/index.php',
    16: 'http://protocol-analysis-lab-web-1/index.php',
  }
  return urls[getBaseLabId()] || ''
})

const moduleOverviewCards = computed(() => {
  const totalScore = experiment.value.taskPoints.reduce((sum, task) => sum + Number(task.score || 0), 0)
  const questionCount = experiment.value.taskPoints.reduce((sum, task) => sum + Number(task.questions?.length || 0), 0)
  const estimatedPoints = experiment.value.difficulty * 30 + Math.min(Math.round((totalScore / 10) * 10), 50)

  return [
    {
      title: '实验类型',
      value: moduleCategoryLabel.value,
      desc: '当前实验主题与任务类型',
      badge: `${experiment.value.difficulty} 星难度`,
      badgeClass: 'badge-warning',
      icon: 'fa-layer-group',
      iconClass: 'text-primary'
    },
    {
      title: '任务点数量',
      value: `${experiment.value.taskPoints.length}`,
      desc: '按任务逐步完成实验挑战',
      badge: `${questionCount} 道题`,
      badgeClass: 'badge-info',
      icon: 'fa-list-check',
      iconClass: 'text-secondary'
    },
    {
      title: '预估积分',
      value: `${estimatedPoints}`,
      desc: '完成实验后可获得的积分参考',
      badge: `${totalScore} 分任务`,
      badgeClass: 'badge-success',
      icon: 'fa-coins',
      iconClass: 'text-accent'
    },
    {
      title: '环境模式',
      value: hasLiveTargetUrl.value ? '实时靶机' : '等待启动',
      desc: hasLiveTargetUrl.value ? '右侧可直接查看实时环境' : '点击开始挑战后显示靶机环境',
      badge: hasLiveTargetUrl.value ? '实时' : '待启动',
      badgeClass: hasLiveTargetUrl.value ? 'badge-success' : 'badge-warning',
      icon: 'fa-display',
      iconClass: 'text-info'
    }
  ]
})

const operationGuideSteps = computed(() => [
  `打开操作面板后先确认实验主题：${moduleCategoryLabel.value}`,
  '按任务点顺序完成信息收集、漏洞验证和结果记录。',
  '遇到报错时优先记录关键现象，再结合题解讨论区整理复盘结论。'
])

const targetPreviewSteps = computed(() => experiment.value.taskPoints.slice(0, 3).map((task, index) => ({
  title: `阶段 ${index + 1}：${task.name}`,
  desc: task.description || '围绕当前任务点完成漏洞验证与实验记录。'
})))

const targetPreviewHighlights = computed(() => [
  `${moduleCategoryLabel.value} 环境地址会按靶机启动结果展示。`,
  `当前模块共 ${experiment.value.taskPoints.length} 个任务点，适合按阶段讲解。`,
  '题目提交支持补充判定，即使容器状态未同步也能继续记录结果。'
])

// 在experiment加载完成后初始化答案状态
watch(experiment, (newExperiment) => {
  if (newExperiment && newExperiment.taskPoints) {
    newExperiment.taskPoints.forEach((x) => {
      if (!answerStatus.value[x.id]) {
  answerStatus.value[x.id] = {}
      }
      if (!answers.value[x.id]) {
        answers.value[x.id] = {}
      }
      if (x.questions) {
  x.questions.forEach((y) => {
          if (!answerStatus.value[x.id][y.id]) {
    answerStatus.value[x.id][y.id] = null
          }
          // 初始化答案对象
          if (y.type === 'multiple-choice') {
            answers.value[x.id][y.id] = [];
          } else if (!answers.value[x.id][y.id]) {
            answers.value[x.id][y.id] = '';
          }
        })
      }
    })
  }
}, { immediate: true })

// 调用 ai-agent-service 拉起 per-user noVNC 操作桌面。
const toggleOperationMachine = async () => {
  if (!isOperationMachineRunning.value) {
    isOperationLoading.value = true
    try {
      const userContext = await getCurrentUserContext()
      const response = await axios.post('/api/docker/operation/start', {
        user_id: userContext.user_id ?? 0,
        module_id: experiment.value.id,
        course_id: null,
      })
      const data = response.data?.data
      if (!data?.session_id || !data?.ws_path) {
        throw new Error('后端未返回操作环境连接信息')
      }

      operationSessionId.value = data.session_id
      const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
      operationVncWsUrl.value = `${wsScheme}://${window.location.host}${data.ws_path}`
      isOperationMachineRunning.value = true
      activeEnvironmentTab.value = 'operation'
    } catch (error: any) {
      console.error('[OperationEnv] 启动操作环境失败:', error)
      pointsNotification.value = {
        show: true,
        message: error?.response?.data?.detail || error?.message || '启动操作环境失败，请检查 ai-agent-service 与 Docker 是否就绪',
      }
      clearPointsNotification()
    } finally {
      isOperationLoading.value = false
    }
  } else {
    const sessionId = operationSessionId.value
    isOperationMachineRunning.value = false
    operationSessionId.value = ''
    operationVncWsUrl.value = ''
    if (activeEnvironmentTab.value === 'operation') {
      activeEnvironmentTab.value = isTargetMachineRunning.value ? 'target' : null
    }
    if (sessionId) {
      axios.post('/api/docker/operation/stop', { session_id: sessionId })
        .catch((error) => console.warn('[OperationEnv] 停止操作环境失败:', error))
    }
  }
}

// 添加URL清理函数，防止URL重复
const cleanUrl = (url: string): string => {
  let result = url;

  // 检查URL是否包含重复的域名或路径
  const urlPattern = /(https?:\/\/[^\/]+)(\/.*)?/;
  const match = result.match(urlPattern);

  if (match) {
    const domain = match[1]; // 例如 http://localhost:8095
    let path = match[2] || ''; // 例如 /index.html 或 /http://localhost:8095/index.html

    // 检查路径中是否包含域名
    if (path.includes(domain)) {
      // 从路径中移除重复的域名
      path = path.replace(domain, '');
      console.log(`检测到URL重复，已清理: ${url} -> ${domain}${path}`);
      result = `${domain}${path}`;
    }
  }

  // 靶机地址统一改写成走 Vite 代理的相对子路径 /lab-<端口>。
  // 后端和前端兜底都返回 http://localhost:<端口>，直接塞进 iframe 时，
  // 通过公网隧道访问的人会去连自己本机的端口而失败；改成子路径后由
  // 5173 的代理转发到靶场容器，一条隧道即可覆盖所有靶场，本地开发也照常工作。
  const labProxy = result.match(/^https?:\/\/(?:localhost|127\.0\.0\.1):(\d+)(\/.*)?$/i);
  if (labProxy) {
    result = `/lab-${labProxy[1]}${labProxy[2] || ''}`;
  }

  return result;
};

const getDockerLabKey = (baseId: number): string => {
  switch (baseId) {
    case 1:
      return 'sqli';
    case 2:
      return 'xss';
    case 3:
      return 'csrf';
    case 4:
      return 'cmd';
    case 5:
      return 'upload';
    case 6:
      return 'dir';
    case 16:
      return 'protocol';
    default:
      return 'sqli';
  }
};

const normalizeTargetUrl = (url?: string | null): string => {
  const cleaned = cleanUrl(String(url || '').trim());
  if (!cleaned) return '';
  const baseId = getBaseLabId();
  if (baseId === 4) {
    if (cleaned.endsWith('/')) return `${cleaned}index.html`;
    if (cleaned.endsWith('index.php')) return cleaned.replace('index.php', 'index.html');
    if (!cleaned.endsWith('.php') && !cleaned.endsWith('.html')) return `${cleaned}/index.html`;
    return cleaned;
  }
  if (cleaned.endsWith('/')) return `${cleaned}index.php`;
  if (cleaned.endsWith('index.html')) return cleaned.replace('index.html', 'index.php');
  if (!cleaned.endsWith('.php') && !cleaned.endsWith('.html')) return `${cleaned}/index.php`;
  return cleaned;
};

const applyTargetStatus = (statusData: DockerTargetStatus | null) => {
  targetStatusDetail.value = statusData;
  const normalizedStatus = statusData?.status || 'offline';
  targetMachineStatus.value = normalizedStatus;
  targetMachineMessage.value = statusData?.message || (normalizedStatus === 'online' ? '靶机 Web 服务可访问' : '靶机 Web 服务未就绪，请稍后刷新或重启实验环境。');
  targetMachineUrl.value = normalizeTargetUrl(statusData?.targetUrl);
  isTargetMachineRunning.value = normalizedStatus === 'online' && Boolean(targetMachineUrl.value);

  if (isTargetMachineRunning.value) {
    targetIframeState.value = 'loading';
    activeEnvironmentTab.value = 'target';
    showNoVNC.value = true;
  } else {
    targetIframeState.value = normalizedStatus === 'offline' ? 'idle' : 'error';
    showNoVNC.value = false;
    clearLab();
  }
};

const fetchTargetStatus = async (baseId = getBaseLabId()) => {
  const labKey = getDockerLabKey(baseId);
  const response = await axios.get(`${DOCKER_API_URL}/api/docker/target-status/${labKey}`);
  return response.data?.data as DockerTargetStatus;
};

const getDockerStartEndpoint = (baseId: number): string => {
  switch (baseId) {
    case 1:
      return '/api/docker/start-sqli';
    case 2:
      return '/api/docker/start-xss';
    case 3:
      return '/api/docker/start-csrf';
    case 4:
      return '/api/docker/start-cmd';
    case 5:
      return '/api/docker/start-upload';
    case 6:
      return '/api/docker/start-dir';
    case 16:
      return '/api/docker/start-protocol';
    default:
      return '/api/docker/start-sqli';
  }
};

const getDefaultTargetUrl = (baseId: number): string => {
  switch (baseId) {
    case 1:
      return 'http://localhost:8091/index.php';
    case 2:
      return 'http://localhost:8092/index.php';
    case 3:
      return 'http://localhost:8093/index.php';
    case 4:
      return 'http://localhost:8090/index.html';
    case 5:
      return 'http://localhost:8094/index.php';
    case 6:
      return 'http://localhost:8095/index.php';
    default:
      return 'http://localhost:8091/index.php';
  }
};

const registerOnlineTargetSession = async (baseId: number) => {
  const containerName = CONTAINER_NAMES[baseId] || 'sqli-lab-web-1'
  currentTargetContainerName.value = containerName
  setLabRunning(containerName)
  setLabContext({
    moduleId: Number(moduleId),
    moduleName: moduleCategoryLabel.value,
    experimentId: experiment.value.id,
    experimentTitle: experiment.value.name,
    labSessionId: getLabSessionId(),
    containerName,
    currentLabContainer: containerName,
    targetUrl: targetMachineUrl.value,
    targetMachineUrl: targetMachineUrl.value,
    courseId: null
  })

  try {
    const userContext = await getCurrentUserContext()
    const session = await startLabSession({
      ...userContext,
      course_id: null,
      module_id: Number(moduleId),
      task_id: null,
      container_name: containerName,
      container_id: targetStatusDetail.value?.containerId || experiment.value.targetMachine?.id || null,
      target_url: targetMachineUrl.value,
      request_id: `lab-start-${Date.now()}-${Math.random().toString(16).slice(2)}`
    })
    labSessionId.value = session.session_id
    setLabSessionId(session.session_id)
    setLabContext({
      labSessionId: session.session_id,
      userId: userContext.user_id,
      classId: userContext.class_id
    })
  } catch (error: any) {
    console.error('创建靶机会话失败:', error)
    pointsNotification.value = {
      show: true,
      message: error?.response?.data?.detail || error?.message || '靶机会话创建失败，Flag 提交暂不可用'
    }
    clearPointsNotification()
  }
};

const refreshTargetMachineStatus = async () => {
  if (isTargetLoading.value) return;
  isTargetLoading.value = true;
  try {
    const statusData = await fetchTargetStatus();
    applyTargetStatus(statusData);
  } catch (error: any) {
    targetMachineStatus.value = 'offline';
    isTargetMachineRunning.value = false;
    targetIframeState.value = 'error';
    targetMachineMessage.value = error?.response?.data?.message || error?.message || 'URL 暂不可访问';
    clearLab();
  } finally {
    isTargetLoading.value = false;
  }
};

// 修改启动靶机函数
const startTargetMachine = async () => {
  // TCP pwn 靶机：确保容器运行 + 建立靶机会话（用于 Flag 提交），并切到「连接信息」页签
  if (isPwnTarget.value) {
    activeEnvironmentTab.value = 'target';
    if (isTargetLoading.value) return;
    isTargetLoading.value = true;
    try {
      await axios.post(`${DOCKER_API_URL}${pwnTarget.value!.startEndpoint}`);
      isTargetMachineRunning.value = true;
      targetMachineStatus.value = 'online';
      await registerOnlineTargetSession(getBaseLabId());
    } catch (error: any) {
      pointsNotification.value = {
        show: true,
        message: error?.response?.data?.message || error?.message || '靶机准备失败，请确认 docker-api 与靶机容器已就绪'
      };
      clearPointsNotification();
    } finally {
      isTargetLoading.value = false;
    }
    return;
  }
  if (isTargetPending.value) { activeEnvironmentTab.value = 'target'; return; } // 靶机环境建设中：仅切到占位页签，不启动靶机
  if (isTargetLoading.value) return; // 防止重复点击
  isTargetLoading.value = true;
  const minLoadingTime = 3000; // 最少显示3秒
  const startTime = Date.now();

  try {
    const urlId = Number(route.params.id);
    if (experiment.value.id !== urlId) {
      experiment.value.id = urlId;
    }

    const baseId = getBaseLabId();
    const response = await axios.post(`${DOCKER_API_URL}${getDockerStartEndpoint(baseId)}`);
    const statusData = response.data?.data as DockerTargetStatus | null;
    applyTargetStatus(statusData);

    if (targetMachineStatus.value === 'online' && targetMachineUrl.value) {
      await registerOnlineTargetSession(baseId);
    } else {
      pointsNotification.value = {
        show: true,
        message: targetMachineMessage.value || '靶机 Web 服务未就绪，请稍后刷新或重启实验环境。'
      };
      clearPointsNotification();
    }
  } catch (error: any) {
    targetMachineStatus.value = 'offline';
    isTargetMachineRunning.value = false;
    showNoVNC.value = false;
    targetIframeState.value = 'error';
    targetMachineMessage.value = error?.response?.data?.message || error?.message || 'URL 暂不可访问';
    clearLab();
    pointsNotification.value = {
      show: true,
      message: targetMachineMessage.value
    };
    clearPointsNotification();
  } finally {
    const elapsed = Date.now() - startTime;
    const finish = () => {
      isTargetLoading.value = false;
      activeEnvironmentTab.value = targetMachineStatus.value !== 'offline'
        ? 'target'
        : (isOperationMachineRunning.value ? 'operation' : null);
    };
    if (elapsed < minLoadingTime) {
      setTimeout(finish, minLoadingTime - elapsed);
    } else {
      finish();
    }
  }
  return;

  let url: string | null = null;
  try {
    // 根据模块ID确定正确的API端点
    let apiEndpoint = '/api/docker/start-sqli';
    
    // 获取当前模块的基础ID（对于101-104等变体，获取其基础类型）
    const currentId = experiment.value.id;
    console.log(`启动靶机前，当前模块ID: ${currentId}`);
    
    // 强制检查ID是否与URL参数一致
    const urlId = Number(route.params.id);
    if (currentId !== urlId) {
      console.warn(`警告：模块ID与URL不一致！URL ID=${urlId}, 当前ID=${currentId}`);
      // 如果不一致，使用URL中的ID
      experiment.value.id = urlId;
    }
    
    // 计算基础ID：对于大于100的ID，提取第一位作为基础类型
    const baseId = getBaseLabId();
    console.log(`计算得到基础ID: ${baseId}`);
                  
    // 根据基础ID选择正确的API端点
    switch(baseId) {
      case 1: // SQL注入
        apiEndpoint = '/api/docker/start-sqli';
        break;
      case 2: // XSS
        apiEndpoint = '/api/docker/start-xss';
        break;
      case 3: // CSRF
        apiEndpoint = '/api/docker/start-csrf';
        break;
      case 4: // 命令注入
        apiEndpoint = '/api/docker/start-cmd';
        break;
      case 5: // 文件上传
        apiEndpoint = '/api/docker/start-upload';
        break;
      case 6: // 目录遍历
        apiEndpoint = '/api/docker/start-dir';
        break;
      default:
        console.log(`未知的基础ID ${baseId}，默认使用SQL注入靶机`);
        apiEndpoint = '/api/docker/start-sqli';
    }
    
    console.log(`启动靶机，模块ID: ${currentId}, 基础ID: ${baseId}, 使用API: ${apiEndpoint}`);
    
    // 导入Docker API URL
    // 尝试调用API启动靶机
    async function fetchData(retryCount = 0) {
      try {
        const res = await axios.post(`${DOCKER_API_URL}${apiEndpoint}`);
        console.log('API response:', res.data);
        
        if (res.data && res.data.data && res.data.data.url) {
          // 获取API返回的URL
          let apiUrl = res.data.data.url;
          
          // 清理可能的URL重复问题
          apiUrl = cleanUrl(apiUrl);
          
          // 对于目录遍历漏洞实验，使用index.php作为入口
          if (baseId === 6) { // 目录遍历
            if (apiUrl.endsWith('/')) {
              apiUrl += 'index.php';
            } else if (apiUrl.endsWith('index.html')) {
              apiUrl = apiUrl.replace('index.html', 'index.php');
            } else if (!apiUrl.endsWith('.php')) {
              apiUrl += '/index.php';
            }
          }
          // 对于SQL注入漏洞实验，使用index.php作为入口
          else if (baseId === 1) { // SQL注入
            if (apiUrl.endsWith('/')) {
              apiUrl += 'index.php';
            } else if (apiUrl.endsWith('index.html')) {
              apiUrl = apiUrl.replace('index.html', 'index.php');
            } else if (!apiUrl.endsWith('.php')) {
              apiUrl += '/index.php';
            }
          }
          // 对于XSS漏洞实验，使用index.php作为入口
          else if (baseId === 2) { // XSS
            if (apiUrl.endsWith('/')) {
              apiUrl += 'index.php';
            } else if (apiUrl.endsWith('index.html')) {
              apiUrl = apiUrl.replace('index.html', 'index.php');
            } else if (!apiUrl.endsWith('.php')) {
              apiUrl += '/index.php';
            }
          }
          // 对于CSRF漏洞实验，使用index.php作为入口
          else if (baseId === 3) { // CSRF
            if (apiUrl.endsWith('/')) {
              apiUrl += 'index.php';
            } else if (apiUrl.endsWith('index.html')) {
              apiUrl = apiUrl.replace('index.html', 'index.php');
            } else if (!apiUrl.endsWith('.php')) {
              apiUrl += '/index.php';
            }
          }
          // 对于命令注入漏洞实验，使用index.php作为入口
          else if (baseId === 4) { // 命令注入
            if (apiUrl.endsWith('/')) {
              apiUrl += 'index.php';
            } else if (apiUrl.endsWith('index.html')) {
              apiUrl = apiUrl.replace('index.html', 'index.php');
            } else if (!apiUrl.endsWith('.php')) {
              apiUrl += '/index.php';
            }
          }
          // 对于文件上传漏洞实验，使用index.php作为入口
          else if (baseId === 5) { // 文件上传
            if (apiUrl.endsWith('/')) {
              apiUrl += 'index.php';
            } else if (apiUrl.endsWith('index.html')) {
              apiUrl = apiUrl.replace('index.html', 'index.php');
            } else if (!apiUrl.endsWith('.php')) {
              apiUrl += '/index.php';
            }
          }
          // 其他实验默认使用index.html
          else {
            if (apiUrl.endsWith('/')) {
              apiUrl += 'index.html';
            } else if (!apiUrl.endsWith('.html') && !apiUrl.endsWith('.php')) {
              apiUrl += '/index.html';
            }
          }
          
          // 再次清理URL，确保没有重复
          apiUrl = cleanUrl(apiUrl);
          console.log('处理后的URL:', apiUrl);
          return apiUrl;
        } else {
          console.log('API response not as expected:', res.data);
          throw new Error('Invalid API response');
        }
      } catch (error) {
        console.log(`API request failed (attempt ${retryCount + 1}/3):`, error);
        if (retryCount < 2) {
          // 重试最多3次
          await new Promise(resolve => setTimeout(resolve, 1000));
          return fetchData(retryCount + 1);
        } else {
          const fallbackUrl = getDefaultTargetUrl(baseId);
          console.log('API 多次重试失败，使用默认靶机 URL:', fallbackUrl);
          return cleanUrl(fallbackUrl);
        }
      }
    }
    
    // 尝试获取URL，失败后使用原来的默认靶机 URL 兜底
    url = await fetchData();
  } catch (e) {
    const fallbackUrl = getDefaultTargetUrl(getBaseLabId());
    url = cleanUrl(fallbackUrl);
    console.error('启动靶机失败，使用默认靶机 URL:', e);
  } finally {
    const elapsed = Date.now() - startTime;
    const finishLoading = async () => {
      targetMachineUrl.value = url || '';
      isTargetMachineRunning.value = Boolean(url);
      isTargetLoading.value = false;
      showNoVNC.value = Boolean(url);
      // 设置活动环境标签为靶机
      activeEnvironmentTab.value = url ? 'target' : (isOperationMachineRunning.value ? 'operation' : null);

      // 打印调试信息
      console.log('靶机启动成功，URL:', targetMachineUrl.value);
      console.log('当前活动标签:', activeEnvironmentTab.value);

      // ── 通知 Agent 悬浮窗：靶机已启动 ──────────────────────
      const labId = Number(baseId) || 1
      const containerName = CONTAINER_NAMES[labId] || 'sqli-lab-web-1'
      if (url) {
        currentTargetContainerName.value = containerName
        setLabRunning(containerName)
        setLabContext({
          moduleId: Number(moduleId),
          moduleName: moduleCategoryLabel.value,
          experimentId: experiment.value.id,
          experimentTitle: experiment.value.name,
          labSessionId: getLabSessionId(),
          containerName,
          currentLabContainer: containerName,
          targetUrl: targetMachineUrl.value,
          targetMachineUrl: targetMachineUrl.value,
          courseId: null
        })
        try {
          const userContext = await getCurrentUserContext()
          const session = await startLabSession({
            ...userContext,
            course_id: null,
            module_id: Number(moduleId),
            task_id: null,
            container_name: containerName,
            container_id: experiment.value.targetMachine?.id ?? null,
            target_url: targetMachineUrl.value,
            request_id: `lab-start-${Date.now()}-${Math.random().toString(16).slice(2)}`
          })
          labSessionId.value = session.session_id
          setLabSessionId(session.session_id)
          setLabContext({
            labSessionId: session.session_id,
            userId: userContext.user_id,
            classId: userContext.class_id
          })
        } catch (error: any) {
          console.error('创建靶机会话失败:', error)
          pointsNotification.value = {
            show: true,
            message: error?.response?.data?.detail || error?.message || '靶机会话创建失败，Flag 提交暂不可用'
          }
          clearPointsNotification()
        }
      }
      console.log('[AgentState] 靶机容器:', containerName);
    };
    if (elapsed < minLoadingTime) {
      setTimeout(() => { void finishLoading() }, minLoadingTime - elapsed);
    } else {
      void finishLoading();
    }
  }
};

// 关闭靶机环境 → 改为结束实验
const closeTargetMachine = async () => {
  if (isTargetMachineRunning.value) {
    confirmEndExperiment()
    return
  }

  labSessionId.value = ''
  currentTargetContainerName.value = ''
  isTargetMachineRunning.value = false
  showNoVNC.value = false
  targetMachineUrl.value = ''
  targetMachineStatus.value = 'offline'
  targetMachineMessage.value = '靶机环境未启动'
  targetStatusDetail.value = null
  targetIframeState.value = 'idle'
  clearLab()   // 通知 Agent：靶机已关闭
}

// 获取难度星级显示
const getDifficultyStars = (difficulty: number) => '★'.repeat(difficulty) + '☆'.repeat(5 - difficulty)

const findQuestion = (taskId: number, questionId: number) => {
  const task = experiment.value.taskPoints.find((item) => item.id === taskId)
  return task?.questions.find((item) => item.id === questionId) as any
}

const getCurrentUserContext = async () => {
  const token = cookie.get('token')
  if (!token) return { user_id: null, class_id: null }

  try {
    const result = await getUserInfo(token)
    return {
      user_id: result.data?.userId ?? null,
      class_id: result.data?.classId ?? null
    }
  } catch (error) {
    console.warn('获取用户上下文失败，将以空身份提交', error)
    return { user_id: null, class_id: null }
  }
}

const buildEventsPayload = async () => {
  const userContext = await getCurrentUserContext()
  const sessionId = labSessionId.value || getLabSessionId()
  const containerName = currentTargetContainerName.value || currentLabContainer.value || CONTAINER_NAMES[getBaseLabId()] || ''
  const trackedEvents = getLabEvents()
    .filter((event) => {
      const eventType = normalizeEventType(event.event_type)
      if (eventType === 'LAB_START') {
        return !labSessionId.value
      }
      if (eventType === 'FLAG_SUBMIT') {
        return false
      }
      return true
    })
    .map((event) => ({
      event_id: event.event_id,
      request_id: `req-${event.event_id}`,
      event_type: event.event_type,
      event_time: event.event_time,
      user_id: userContext.user_id,
      class_id: userContext.class_id,
      course_id: null,
      module_id: Number(moduleId),
      task_id: null,
      question_id: null,
      lab_session_id: sessionId,
      source: 'external-agent',
      container_name: containerName,
      ...event,
    }))

  trackedEvents.push({
    event_id: `evt-lab-stop-${Date.now()}`,
    request_id: `req-lab-stop-${Date.now()}`,
    event_type: 'LAB_STOP',
    event_time: new Date().toISOString(),
    user_id: userContext.user_id,
    class_id: userContext.class_id,
    course_id: null,
    module_id: Number(moduleId),
    task_id: null,
    question_id: null,
    lab_session_id: sessionId,
    source: 'external-agent',
    container_name: containerName,
    extra: {
      status: 'stopped',
      stop_reason: 'user_ended',
      duration_seconds: getLabDurationSeconds(),
      completed: flagSubmitStatus.value.isSuccess,
    },
  })

  return {
    batch_id: `batch-${Date.now()}`,
    source_system: 'external-agent',
    generated_at: new Date().toISOString(),
    user_context: {
      user_id: userContext.user_id,
      class_id: userContext.class_id,
      course_id: null,
      module_id: Number(moduleId),
      task_id: null,
      question_id: null,
      lab_session_id: sessionId,
    },
    events: trackedEvents,
    ai_generated_questions: [],
    profile_rebuild: {
      user_id: userContext.user_id,
      class_id: userContext.class_id,
      rebuild_after_ingest: Boolean(userContext.user_id),
    },
  }
}

const confirmEndExperiment = () => {
  showEndExperimentModal.value = true
}

const cancelEndExperiment = () => {
  if (isEndingExperiment.value) return
  showEndExperimentModal.value = false
}

const sendEventsAndEndLab = async () => {
  if (isEndingExperiment.value) return
  isEndingExperiment.value = true

  try {
    const payload = await buildEventsPayload()
    const result = await ingestEvents(payload)
    if (result.isSuccess !== 1 && result.status !== 200) {
      console.warn('[EndExperiment] 事件上报返回非成功状态:', result)
    }
  } catch (error) {
    console.error('[EndExperiment] 事件上报失败:', error)
  }

  try {
    pointsNotification.value = {
      show: true,
      message: '实验已结束，已保留共享靶机并关闭个人操作环境',
    }
    clearPointsNotification()
  } catch (error) {
    console.error('[EndExperiment] 结束实验提示失败:', error)
    pointsNotification.value = {
      show: true,
      message: '实验事件已提交，但结束提示显示失败',
    }
    clearPointsNotification()
  } finally {
    if (operationSessionId.value) {
      try {
        await axios.post('/api/docker/operation/stop', { session_id: operationSessionId.value })
      } catch (error) {
        console.warn('[EndExperiment] 停止操作环境失败:', error)
      }
      operationSessionId.value = ''
      operationVncWsUrl.value = ''
      isOperationMachineRunning.value = false
    }
    labSessionId.value = ''
    currentTargetContainerName.value = ''
    isTargetMachineRunning.value = false
    showNoVNC.value = false
    targetMachineUrl.value = ''
    targetMachineStatus.value = 'offline'
    targetMachineMessage.value = '靶机环境未启动'
    targetStatusDetail.value = null
    targetIframeState.value = 'idle'
    activeEnvironmentTab.value = null
    clearLab()
    showEndExperimentModal.value = false
    isEndingExperiment.value = false
  }
}

const isFlagQuestion = (question: any) => {
  const content = String(question?.content || '').toLowerCase()
  return Boolean(question?.requiresTarget) || content.includes('flag')
}

const submitQuestionToBackend = async (taskId: number, questionId: number) => {
  console.log('提交题目到后端判题:', questionId, answers.value[taskId]?.[questionId])

  if (!answers.value[taskId]) answers.value[taskId] = {}
  if (!answerStatus.value[taskId]) answerStatus.value[taskId] = {}
  if (!questionSubmitting.value[taskId]) questionSubmitting.value[taskId] = {}

  const question = findQuestion(taskId, questionId)
  if (!question) {
    flagSubmitStatus.value = {
      isSubmitted: true,
      isSuccess: false,
      message: '未找到题目信息，无法提交',
      taskId,
      questionId
    }
    clearFlagStatus()
    return
  }
  setLabContext({
    currentTask: question.content || question.title || question.name || `task-${taskId}-${questionId}`
  })

  if (answers.value[taskId][questionId] === undefined || answers.value[taskId][questionId] === null) {
    answers.value[taskId][questionId] = question.type === 'multiple-choice' ? [] : ''
  }
  const submittedAnswer = answers.value[taskId][questionId]

  questionSubmitting.value[taskId][questionId] = true
  try {
    const userContext = await getCurrentUserContext()
    if (isFlagQuestion(question)) {
      if (!labSessionId.value) {
        throw new Error('请先启动靶机环境，再提交 Flag')
      }
      const flagText = Array.isArray(submittedAnswer) ? submittedAnswer.join(',') : String(submittedAnswer ?? '')
      const response = await submitFlagAnswer({
        ...userContext,
        course_id: null,
        module_id: Number(moduleId),
        task_id: taskId,
        lab_session_id: labSessionId.value,
        container_name: currentTargetContainerName.value || CONTAINER_NAMES[getBaseLabId()] || null,
        flag_text: flagText,
        score: question.score,
        request_id: `flag-${Date.now()}-${Math.random().toString(16).slice(2)}`
      })
      answerStatus.value[taskId][questionId] = response.is_correct
      flagSubmitStatus.value = {
        isSubmitted: true,
        isSuccess: response.is_correct,
        message: response.message || (response.is_correct ? 'Flag 正确' : 'Flag 错误，请重试'),
        taskId,
        questionId
      }
      addLabEvent({
        event_type: 'FLAG_SUBMIT',
        container_name: currentTargetContainerName.value || currentLabContainer.value,
        flag_text: flagText,
        is_correct: response.is_correct,
        score: response.score,
        extra: { task_id: taskId, question_id: questionId }
      })
      return
    }

    const response = await submitQuestionAnswer({
      ...userContext,
      course_id: null,
      module_id: Number(moduleId),
      task_id: taskId,
      question_id: questionId,
      question_type: question.type,
      answer: submittedAnswer,
      cost_time: Math.max(0, Math.round((Date.now() - moduleStartedAt) / 1000)),
      request_id: `question-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      question_score: question.score,
      standard_answer: question.answer ?? question.correctAnswer ?? null,
      question_snapshot: {
        id: question.id,
        content: question.content,
        score: question.score,
        type: question.type,
        options: question.options || [],
        answer: question.answer ?? question.correctAnswer ?? null
      }
    })

    answerStatus.value[taskId][questionId] = response.is_correct
    flagSubmitStatus.value = {
      isSubmitted: true,
      isSuccess: response.is_correct !== false,
      message: response.message || (response.is_correct ? '答案正确' : '答案错误，请重试'),
      taskId,
      questionId
    }
  } catch (error: any) {
    console.error('题目提交失败:', error)
    answerStatus.value[taskId][questionId] = false
    flagSubmitStatus.value = {
      isSubmitted: true,
      isSuccess: false,
      message: error?.response?.data?.detail || error?.message || '提交失败，请稍后重试',
      taskId,
      questionId
    }
  } finally {
    questionSubmitting.value[taskId][questionId] = false
    clearFlagStatus()
  }
}

const checkAnswer = (taskId: number, questionId: number) => submitQuestionToBackend(taskId, questionId)
const submitAnswer = (taskId: number, questionId: number) => submitQuestionToBackend(taskId, questionId)

// 修改计算积分的方法
const calculatePoints = computed(() => {
  // 难度基础分：每星30分（5星最高150分）
  const difficultyPoints = experiment.value.difficulty * 30

  // 时间加成：每小时10分（最长5小时，最高50分）
  const totalHours = experiment.value.taskPoints.reduce((total, task) => {
    return total + task.score / 10 // 假设每10分的任务需要1小时
  }, 0)
  // 限制最大计算时长为5小时
  const timePoints = Math.min(Math.round(totalHours * 10), 50)

  // 总分 = 难度分 + 时间分（自然限制在200分以内）
  return difficultyPoints + timePoints
})

// 添加页面状态控制，用于切换做题和题解讨论页面
const currentTab = ref('practice') // 'practice'或'discussion'

// 添加iframe显示控制
const isIframeVisible = computed(() => isOperationMachineRunning.value || isTargetMachineRunning.value || targetPanelVisible.value)

// 计算查看题解所需积分
const getSolutionCost = (difficulty: number) => {
  const costs = {
    1: 40, // 1星40分
    2: 80, // 2星80分
    3: 140, // 3星140分
    4: 180, // 4星180分
    5: 250 // 5星250分
  }
  return costs[difficulty as keyof typeof costs]
}

// 显示积分确认弹窗
const showCostModal = ref(false)
const solutionCost = computed(() => getSolutionCost(experiment.value.difficulty))

// 模拟用户积分余额
const userPoints = ref(5000)

// 添加已付费查看标记
const hasViewedDiscussion = ref(false)

// 添加积分不足通知状态
const pointsNotification = ref({
  show: false,
  message: ''
});

// 清除积分通知
const clearPointsNotification = () => {
  setTimeout(() => {
    pointsNotification.value.show = false;
  }, 5000); // 5秒后自动清除
};

// 查看题解讨论
const viewDiscussion = () => {
  if (!hasViewedDiscussion.value) {
    // 首次查看需要支付积分
    if (userPoints.value < solutionCost.value) {
      // 使用内联通知替代alert
      pointsNotification.value = {
        show: true,
        message: `积分不足，需要${solutionCost.value}积分才能查看题解`
      };
      clearPointsNotification();
      return
    }

    // 显示确认对话框
    showCostModal.value = true
  } else {
    // 已经查看过，直接切换到讨论页面，不扣除积分
    currentTab.value = 'discussion'
  }
}

// 确认查看题解
const confirmViewDiscussion = () => {
  // 如果已查看过，不再扣费
  if (!hasViewedDiscussion.value) {
    userPoints.value -= solutionCost.value
    hasViewedDiscussion.value = true
  }
  
  // 关闭确认弹窗，切换到讨论页面
  showCostModal.value = false
  currentTab.value = 'discussion'
}

// 模拟讨论数据
const discussions = ref([
  {
    id: 1,
    author: {
      name: '安全专家',
      avatar: '/student11.png'
    },
    content: '这个实验主要考察了SQL注入的基本原理和防御技术，关键在于理解参数化查询的重要性。',
    createdAt: '2023-10-15 14:30',
    likes: 12
  },
  {
    id: 2,
    author: {
      name: '学习者',
      avatar: '/student12.png'
    },
    content: '我在做第三个任务点时遇到了一些困难，特别是构造UNION SELECT语句时。后来发现需要先确定表的列数，才能成功注入。',
    createdAt: '2023-10-16 09:15',
    likes: 8
  }
])

// 在新窗口打开环境
const openInNewWindow = (type: 'operation' | 'target') => {
  if (type === 'operation') {
    console.info('[OperationEnv] noVNC 操作环境当前嵌入在页面内，暂不支持直接新窗口打开')
    return
  } else if (type === 'target' && targetMachineUrl.value) {
    // 确保URL有效
    if (targetMachineUrl.value) {
      console.log('在新窗口打开靶机:', targetMachineUrl.value);
      window.open(targetMachineUrl.value, '_blank');
    } else {
      console.error('靶机URL无效，无法在新窗口打开');
    }
  }
}

// 添加环境标签页的自动切换监听
watch([isOperationMachineRunning, isTargetMachineRunning], ([newOpRunning, newTargetRunning]) => {
  // 如果操作环境刚刚启动，并且没有活动的标签或靶机已关闭
  if (newOpRunning && (!activeEnvironmentTab.value || activeEnvironmentTab.value === 'target' && !newTargetRunning)) {
    activeEnvironmentTab.value = 'operation';
  }
  // 如果靶机刚刚启动，并且没有活动的标签或操作环境已关闭
  else if (newTargetRunning && (!activeEnvironmentTab.value || activeEnvironmentTab.value === 'operation' && !newOpRunning)) {
    activeEnvironmentTab.value = 'target';
  }
  // 如果两个环境都关闭了
  else if (!newOpRunning && !newTargetRunning) {
    activeEnvironmentTab.value = null;
  }
});

onBeforeRouteLeave((_to, _from, next) => {
  if (isTargetMachineRunning.value || isOperationMachineRunning.value) {
    showEndExperimentModal.value = true
    next(false)
    return
  }
  next()
})

const handleBeforeUnload = (event: BeforeUnloadEvent) => {
  if (!isTargetMachineRunning.value && !isOperationMachineRunning.value) {
    return
  }
  event.preventDefault()
  event.returnValue = ''
}

onMounted(() => {
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
})

// 添加刷新iframe方法
const refreshIframe = async () => {
  await refreshTargetMachineStatus();
  if (targetMachineStatus.value !== 'online' || !targetMachineUrl.value) return;

  const iframe = document.querySelector('.target-iframe') as HTMLIFrameElement;
  if (iframe) {
    targetIframeState.value = 'loading';
    console.log('刷新iframe:', targetMachineUrl.value);
    iframe.src = targetMachineUrl.value;
  }
};

// 添加直接导航方法
const handleTargetIframeLoad = () => {
  targetIframeState.value = targetMachineStatus.value === 'online' ? 'ready' : 'error';
};

const handleTargetIframeError = () => {
  targetIframeState.value = 'error';
  targetMachineMessage.value = '靶机 Web 服务未就绪，请稍后刷新或重启实验环境。';
};

const openDirectUrl = () => {
  if (targetMachineUrl.value) {
    console.log('直接导航到:', targetMachineUrl.value);
    window.open(targetMachineUrl.value, '_blank');
  }
};

// 添加复制到剪贴板功能
const showCopyNotice = (message: string) => {
  pointsNotification.value = {
    show: true,
    message
  };
  setTimeout(() => {
    pointsNotification.value.show = false;
  }, 5000);
};

const fallbackCopyText = (text: string) => {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.select();
  const ok = document.execCommand('copy');
  document.body.removeChild(textarea);
  if (!ok) throw new Error('execCommand copy failed');
};

const copyToClipboard = async (text: string) => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
    } else {
      fallbackCopyText(text);
    }
    console.log('URL已复制到剪贴板:', text);
    showCopyNotice('URL已复制到剪贴板');
  } catch (err) {
    console.error('复制失败:', err);
    showCopyNotice('复制失败，请手动选中复制');
  }
};
</script>

<template>
  <div class="container-fluid">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="flex justify-center items-center h-screen">
      <div class="text-center">
        <div class="loading loading-spinner loading-lg"></div>
        <p class="mt-4">加载模块数据中...</p>
      </div>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="!experiment" class="flex justify-center items-center h-screen">
      <div class="text-center">
        <div class="text-error text-5xl mb-4">
          <i class="fas fa-exclamation-circle"></i>
        </div>
        <p class="text-xl">无法加载模块数据</p>
        <button @click="router.push('/user/modules')" class="btn btn-primary mt-4">
          返回模块列表
        </button>
      </div>
    </div>
    
    <!-- 模块内容 -->
    <div v-else class="container-fluid px-4 py-6 overflow-x-hidden h-full min-h-0 flex flex-col">
      <!-- 积分不足通知 -->
      <div v-if="pointsNotification.show" 
           class="alert alert-warning fixed top-4 right-4 z-50 shadow-lg animate-fade-in-down max-w-md">
        <div class="flex items-center">
          <i class="fas fa-coins mr-2"></i>
          <span>{{ pointsNotification.message }}</span>
          <button @click="pointsNotification.show = false" class="btn btn-sm btn-ghost ml-auto">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
      
      <!-- 返回按钮 -->
      <div class="mb-4 animate-slide-down">
        <button @click="router.go(-1)" class="btn btn-sm btn-ghost gap-2 hover:bg-base-200">
          <i class="fas fa-arrow-left"></i>
          <span>返回</span>
        </button>
      </div>

      <div class="flex flex-1 min-h-0 overflow-visible">
        <!-- 左侧内容区域 -->
        <div class="flex flex-col min-h-0 overflow-y-auto" :class="{ 'w-half': isIframeVisible, 'w-full': !isIframeVisible }">
          <!-- 导航栏 -->
          <div class="bg-base-100 border-b border-base-300">
            <div class="flex items-center gap-6 px-6 py-3">
              <div class="flex items-center gap-2 cursor-pointer" :class="currentTab === 'practice' ? 'text-primary font-semibold' : 'hover:text-primary transition-colors'" @click="currentTab = 'practice'">
                <i class="fas fa-code"></i>
                <span>做题</span>
              </div>
              <div class="flex items-center gap-2 cursor-pointer" :class="currentTab === 'discussion' ? 'text-primary font-semibold' : 'hover:text-primary transition-colors'" @click="viewDiscussion()">
                <i class="fas fa-comments"></i>
                <span>题解讨论</span>
                <span v-if="!hasViewedDiscussion" class="badge badge-xs badge-primary ml-1"> {{ solutionCost }}分 </span>
              </div>
            </div>
          </div>

          <!-- 做题页面 -->
          <div v-if="currentTab === 'practice'" class="flex-1 flex flex-col">
            <!-- 顶部区域 -->
            <div class="bg-base-200 p-4 shadow-lg space-y-4 animate-slide-down">
              <!-- 标题和难度行 -->
              <div class="flex justify-between items-center">
                <div class="flex items-center gap-2">
                  <i class="fas fa-flask text-primary text-2xl"></i>
                  <h1 class="text-2xl font-bold">
                    <span class="text-sm font-mono opacity-70 mr-2">#{{ experiment.id }}</span>
                    {{ experiment.name }}
                  </h1>
                </div>
                <div class="flex items-center gap-4">
                  <!-- 添加积分显示 -->
                  <div class="flex items-center gap-2 text-secondary">
                    <i class="fas fa-coins"></i>
                    <span class="font-semibold">{{ calculatePoints }}积分</span>
                  </div>
                  <!-- 原有的难度显示 -->
                  <div class="text-yellow-500">
                    <i class="fas fa-star mr-2"></i>
                    难度: {{ getDifficultyStars(experiment.difficulty) }}
                  </div>
                </div>
              </div>

              <!-- 环境控制行 -->
              <div class="flex environment-controls justify-between flex-col gap-4">
                <!-- 靶机控制 -->
                <div class="flex items-center gap-4">
                  <i class="fas fa-server text-info"></i>
                  <span>靶机环境</span>
                  <span class="badge badge-sm" :class="targetStatusBadgeClass">
                    {{ isTargetPending ? '建设中' : isTargetLoading ? '启动中' : isTargetMachineRunning ? '运行中' : '未启动' }}
                  </span>
                  <span v-if="isTargetMachineRunning && hasLiveTargetUrl" class="badge badge-sm badge-success">
                    实时环境
                  </span>
                  <button
                    id="start-target-btn"
                    class="btn btn-sm"
                    :class="(!isPwnTarget && isTargetMachineRunning) ? 'btn-error' : 'btn-primary'"
                    @click="isPwnTarget ? startTargetMachine() : (isTargetMachineRunning ? closeTargetMachine() : startTargetMachine())"
                    :disabled="isTargetLoading || isTargetPending"
                  >
                    <span class="loading loading-spinner loading-xs" v-if="isTargetLoading"></span>
                    <i :class="(!isPwnTarget && isTargetMachineRunning) ? 'fas fa-stop' : 'fas fa-play'" class="mr-1" v-else></i>
                    {{ isTargetPending ? '建设中'
                       : isTargetLoading ? '正在准备靶机...'
                       : isPwnTarget ? (isTargetMachineRunning ? '已就绪·查看连接' : '准备靶机')
                       : isTargetMachineRunning ? '结束实验' : '开始挑战' }}
                  </button>
                  <div v-if="isTargetPending" class="text-sm text-base-content/60">靶机环境正在建设中，敬请期待</div>
                  <div v-if="isTargetLoading" class="text-sm text-info">靶机环境正在准备中，请稍候...</div>
                  <div v-else-if="isTargetMachineRunning" class="text-sm text-success">
                    靶机已启动，可以在右侧查看
                    <button 
                      class="btn btn-xs btn-ghost text-primary" 
                      @click="activeEnvironmentTab = 'target'"
                    >
                      <i class="fas fa-arrow-right"></i> 切换到靶机
                    </button>
                  </div>
                </div>

                <!-- 靶机URL显示和复制 -->
                <div v-if="targetMachineUrl" class="flex items-center gap-2 bg-base-200 p-2 rounded">
                  <span class="text-sm font-semibold">靶机URL:</span>
                  <div class="bg-base-300 px-2 py-1 rounded text-sm font-mono flex-grow">
                    {{ targetMachineUrl }}
                  </div>
                  <button 
                    class="btn btn-xs btn-ghost" 
                    @click="copyToClipboard(targetMachineUrl)"
                    title="复制URL"
                  >
                    <i class="fas fa-copy"></i>
                  </button>
                  <button 
                    class="btn btn-xs btn-ghost" 
                    @click="openDirectUrl"
                    title="直接导航"
                  >
                    <i class="fas fa-external-link-alt"></i>
                  </button>
                </div>

                <div
                  v-if="isTargetMachineRunning && isOperationMachineRunning && operationTargetUrl"
                  class="flex items-center gap-2 bg-info/10 p-2 rounded"
                >
                  <span class="text-sm font-semibold">操作环境内访问:</span>
                  <div class="bg-base-300 px-2 py-1 rounded text-sm font-mono flex-grow">
                    {{ operationTargetUrl }}
                  </div>
                  <button
                    class="btn btn-xs btn-ghost"
                    @click="copyToClipboard(operationTargetUrl)"
                    title="复制操作环境内访问地址"
                  >
                    <i class="fas fa-copy"></i>
                  </button>
                </div>

                <!-- 操作环境控制 -->
                <div class="flex items-center gap-4">
                  <i class="fas fa-desktop text-info"></i>
                  <span>操作环境</span>
                  <span class="badge badge-sm" :class="isOperationLoading ? 'badge-info' : isOperationMachineRunning ? 'badge-success' : 'badge-warning'">
                    {{ isOperationLoading ? '启动中' : isOperationMachineRunning ? '运行中' : '未启动' }}
                  </span>
                  <button 
                    class="btn btn-sm" 
                    :class="isOperationMachineRunning ? 'btn-error' : 'btn-primary'" 
                    @click="toggleOperationMachine" 
                    :disabled="isOperationLoading"
                  >
                    <span class="loading loading-spinner loading-xs" v-if="isOperationLoading"></span>
                    <i :class="isOperationMachineRunning ? 'fas fa-stop' : 'fas fa-play'" class="mr-1" v-else></i>
                    {{ isOperationLoading ? '正在启动...' : isOperationMachineRunning ? '关闭操作环境' : '启动操作环境' }}
                  </button>
                  <div v-if="isOperationLoading" class="text-sm text-info">操作环境正在准备中，请稍候...</div>
                </div>
              </div>
            </div>

            <!-- 主要内容区域 -->
            <div class="transition-all duration-300 p-4 overflow-y-auto flex-1 w-full">
              <!-- 实验介绍 -->
              <div class="card bg-base-100 shadow-xl mb-6 animate-slide-up">
                <div class="card-body">
                  <h2 class="text-xl font-semibold mb-2">
                    <i class="fas fa-info-circle text-primary mr-2"></i>
                    实验介绍
                  </h2>
                  <p>{{ experiment.introduction }}</p>
                </div>
              </div>

              <!-- 任务点列表 -->
              <div class="card bg-base-100 shadow-xl animate-slide-up">
                <div class="card-body">
                  <h2 class="text-xl font-semibold mb-4">
                    <i class="fas fa-tasks text-primary mr-2"></i>
                    任务点
                  </h2>
                  <div class="space-y-4">
                    <div v-for="task in experiment.taskPoints" :key="task.id" class="collapse collapse-arrow border-base-300 bg-base-200 border">
                      <input type="checkbox" />
                      <div class="collapse-title text-xl font-semibold flex items-center gap-2">
                        <i class="fas fa-tasks"></i>
                        {{ task.name }}
                        <div class="badge badge-primary badge-lg">
                          <span class="font-bold">{{ task.score }}</span>分
                        </div>
                      </div>
                      <div class="collapse-content">
                        <p>{{ task.description }}</p>

                        <!-- 添加Markdown文档渲染 -->
                        <div class="mt-4">
                          <h4 class="font-semibold mb-2">任务说明</h4>
                          <div class="card bg-base-100 p-4 w-full max-w-full overflow-x-auto">
                            <div class="w-full prose prose-sm max-w-none break-words">
                              <div class="markdown-content">
                                <MarkdownRenderer :content="task.document" />
                              </div>
                            </div>
                          </div>
                        </div>

                        <!-- 任务问题列表 -->
                        <div class="mt-4 space-y-2">
                          <div v-for="question in task.questions" :key="question.id" class="card bg-base-300">
                            <div class="card-body">
                              <div class="flex justify-between items-center">
                                <p>{{ question.content }}</p>
                                <span class="badge">{{ question.score }}分</span>
                              </div>
                              <div class="mt-2">
                                <!-- 带答案的开放题 -->
                                <div v-if="question.type === 'open-ended-with-answer'" class="space-y-2">
                                  <textarea v-model="answers[task.id][question.id]" placeholder="请输入答案" class="textarea textarea-bordered w-full h-24" />
                                  <div class="flex items-center gap-2">
                                    <button @click="checkAnswer(task.id, question.id)" class="btn btn-primary" :disabled="questionSubmitting[task.id]?.[question.id]">{{ questionSubmitting[task.id]?.[question.id] ? '提交中...' : '检查答案' }}</button>
                                    <span v-if="answerStatus[task.id][question.id] !== null" :class="answerStatus[task.id][question.id] ? 'text-success' : 'text-error'" class="flex items-center">
                                      <i :class="answerStatus[task.id][question.id] ? 'fa-check' : 'fa-times'" class="fas mr-1"></i>
                                      {{ answerStatus[task.id][question.id] ? '答案正确' : '答案错误' }}
                                    </span>
                                  </div>
                                  
                                  <!-- Flag 提交结果显示 -->
                                  <div v-if="flagSubmitStatus.isSubmitted && flagSubmitStatus.taskId === task.id && flagSubmitStatus.questionId === question.id" 
                                      :class="flagSubmitStatus.isSuccess ? 'alert alert-success' : 'alert alert-error'"
                                      class="mt-2 animate-fade-in">
                                    <div class="flex items-center">
                                      <i :class="flagSubmitStatus.isSuccess ? 'fa-check-circle' : 'fa-times-circle'" class="fas mr-2"></i>
                                      <span>{{ flagSubmitStatus.message }}</span>
                                    </div>
                                  </div>
                                </div>

                                <!-- 无答案的开放题 -->
                                <div v-else-if="question.type === 'open-ended-without-answer'" class="space-y-2">
                                  <textarea v-model="answers[task.id][question.id]" placeholder="请输入答案" class="textarea textarea-bordered w-full h-24" />
                                  <button @click="submitAnswer(task.id, question.id)" class="btn btn-primary" :disabled="questionSubmitting[task.id]?.[question.id]">{{ questionSubmitting[task.id]?.[question.id] ? '提交中...' : '提交答案' }}</button>
                                  
                                  <!-- Flag 提交结果显示 -->
                                  <div v-if="flagSubmitStatus.isSubmitted && flagSubmitStatus.taskId === task.id && flagSubmitStatus.questionId === question.id" 
                                      class="alert alert-success mt-2 animate-fade-in">
                                    <div class="flex items-center">
                                      <i class="fas fa-check-circle mr-2"></i>
                                      <span>{{ flagSubmitStatus.message }}</span>
                                    </div>
                                  </div>
                                </div>

                                <!-- 单选题 -->
                                <div v-else-if="question.type === 'single-choice'" class="space-y-2">
                                  <div v-for="(option, index) in question.options" :key="index" class="flex items-center gap-2">
                                    <input type="radio" v-model="answers[task.id][question.id]" :name="'q' + question.id" :value="option" class="radio radio-primary" />
                                    <span>{{ option }}</span>
                                  </div>
                                  <div class="flex items-center gap-2 mt-2">
                                    <button @click="checkAnswer(task.id, question.id)" class="btn btn-primary" :disabled="questionSubmitting[task.id]?.[question.id]">{{ questionSubmitting[task.id]?.[question.id] ? '提交中...' : '检查答案' }}</button>
                                    <span v-if="answerStatus[task.id][question.id] !== null" :class="answerStatus[task.id][question.id] ? 'text-success' : 'text-error'" class="flex items-center">
                                      <i :class="answerStatus[task.id][question.id] ? 'fa-check' : 'fa-times'" class="fas mr-1"></i>
                                      {{ answerStatus[task.id][question.id] ? '答案正确' : '答案错误' }}
                                    </span>
                                  </div>
                                  
                                  <!-- Flag 提交结果显示 -->
                                  <div v-if="flagSubmitStatus.isSubmitted && flagSubmitStatus.taskId === task.id && flagSubmitStatus.questionId === question.id" 
                                      :class="flagSubmitStatus.isSuccess ? 'alert alert-success' : 'alert alert-error'"
                                      class="mt-2 animate-fade-in">
                                    <div class="flex items-center">
                                      <i :class="flagSubmitStatus.isSuccess ? 'fa-check-circle' : 'fa-times-circle'" class="fas mr-2"></i>
                                      <span>{{ flagSubmitStatus.message }}</span>
                                    </div>
                                  </div>
                                </div>

                                <!-- 多选题 -->
                                <div v-else-if="question.type === 'multiple-choice'" class="space-y-2">
                                  <div v-for="(option, index) in question.options" :key="index" class="flex items-center gap-2">
                                    <input type="checkbox" v-model="answers[task.id][question.id]" :value="option" class="checkbox checkbox-primary" />
                                    <span>{{ option }}</span>
                                  </div>
                                  <div class="flex items-center gap-2 mt-2">
                                    <button @click="checkAnswer(task.id, question.id)" class="btn btn-primary" :disabled="questionSubmitting[task.id]?.[question.id]">{{ questionSubmitting[task.id]?.[question.id] ? '提交中...' : '检查答案' }}</button>
                                    <span v-if="answerStatus[task.id][question.id] !== null" :class="answerStatus[task.id][question.id] ? 'text-success' : 'text-error'" class="flex items-center">
                                      <i :class="answerStatus[task.id][question.id] ? 'fa-check' : 'fa-times'" class="fas mr-1"></i>
                                      {{ answerStatus[task.id][question.id] ? '答案正确' : '答案错误' }}
                                    </span>
                                  </div>
                                  
                                  <!-- Flag 提交结果显示 -->
                                  <div v-if="flagSubmitStatus.isSubmitted && flagSubmitStatus.taskId === task.id && flagSubmitStatus.questionId === question.id" 
                                      :class="flagSubmitStatus.isSuccess ? 'alert alert-success' : 'alert alert-error'"
                                      class="mt-2 animate-fade-in">
                                    <div class="flex items-center">
                                      <i :class="flagSubmitStatus.isSuccess ? 'fa-check-circle' : 'fa-times-circle'" class="fas mr-2"></i>
                                      <span>{{ flagSubmitStatus.message }}</span>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 题解讨论页面 -->
          <div v-if="currentTab === 'discussion'" class="flex-1 flex flex-col relative min-h-[70vh]">
            <!-- 题解讨论内容 -->
            <div class="p-4 overflow-y-auto">
              <h2 class="text-xl font-semibold mb-4">题解与讨论</h2>
              <div class="discussion-list space-y-4">
                <div v-for="discussion in discussions" :key="discussion.id" class="card bg-base-100 shadow-md">
                  <div class="card-body p-4">
                    <div class="flex items-start gap-3">
                      <div class="avatar">
                        <div class="w-12 h-12 rounded-full">
                          <img :src="discussion.author.avatar" alt="avatar" />
                        </div>
                      </div>
                      <div class="flex-1">
                        <div class="flex justify-between items-center mb-2">
                          <h3 class="font-semibold">{{ discussion.author.name }}</h3>
                          <span class="text-xs text-base-content/60">{{ discussion.createdAt }}</span>
                        </div>
                        <p class="text-sm mb-3">{{ discussion.content }}</p>
                        <div class="flex items-center justify-end">
                          <button class="btn btn-sm btn-ghost gap-1">
                            <i class="fas fa-thumbs-up"></i>
                            <span>{{ discussion.likes }}</span>
                          </button>
                          <button class="btn btn-sm btn-ghost">
                            <i class="fas fa-reply"></i>
                            <span>回复</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 讨论输入框 -->
            <div class="discussion-input-fixed">
              <div class="discussion-input-container">
                <textarea 
                  class="textarea textarea-bordered w-full h-24" 
                  placeholder="分享你的解题思路和心得..."
                ></textarea>
                <div class="flex justify-end mt-3">
                  <button class="btn btn-primary">发表题解</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- iframe部分 -->
        <div v-if="isIframeVisible" class="environment-frame w-half min-h-0 border-l border-base-300 relative flex flex-col">
          <!-- 环境标签页 -->
          <div class="tabs tabs-boxed bg-base-200 p-2 border-b border-base-300 flex-shrink-0">
            <a 
              class="tab flex-1 gap-2" 
              :class="{ 'tab-active': activeEnvironmentTab === 'operation' }"
              @click="isOperationMachineRunning ? activeEnvironmentTab = 'operation' : toggleOperationMachine()"
            >
              <i class="fas fa-desktop"></i>
              操作环境
              <span class="badge badge-xs" :class="isOperationMachineRunning ? 'badge-success' : 'badge-error'"></span>
            </a>
            <a 
              class="tab flex-1 gap-2" 
              :class="{ 'tab-active': activeEnvironmentTab === 'target' }"
              @click="isTargetMachineRunning ? activeEnvironmentTab = 'target' : startTargetMachine()"
            >
              <i class="fas fa-server"></i>
              靶机环境
              <span class="badge badge-xs" :class="targetStatusBadgeClass"></span>
            </a>
          </div>

          <!-- 新窗口打开按钮 -->
          <button
            v-if="activeEnvironmentTab === 'target' && isTargetMachineRunning"
            class="btn btn-sm btn-circle absolute top-3 right-3 z-10 bg-base-100/80 hover:bg-base-100"
            @click="openInNewWindow(activeEnvironmentTab)"
            title="在新窗口打开"
          >
            <i class="fas fa-external-link-alt"></i>
          </button>

          <!-- 操作环境iframe -->
          <div v-if="activeEnvironmentTab === 'operation'" class="w-full flex-1 min-h-0 overflow-hidden">
            <div v-if="isOperationMachineRunning && operationVncWsUrl" class="w-full h-full">
              <VNCViewer :wsUrl="operationVncWsUrl" :password="operationVncPassword" />
            </div>
            <div v-else class="flex flex-col items-center justify-center h-full p-4 text-center">
              <div class="text-6xl text-base-content/20 mb-4">
                <i class="fas fa-desktop"></i>
              </div>
              <h3 class="text-xl font-semibold mb-2">操作环境未启动</h3>
              <p class="text-base-content/70 mb-4">
                请先启动操作环境
              </p>
              <button class="btn btn-primary btn-sm" @click="toggleOperationMachine" :disabled="isOperationLoading">
                <span class="loading loading-spinner loading-xs" v-if="isOperationLoading"></span>
                <i class="fas fa-play mr-1" v-else></i>
                {{ isOperationLoading ? '正在启动...' : '启动操作环境' }}
              </button>
            </div>
          </div>

          <!-- 靶机环境iframe -->
          <div v-if="activeEnvironmentTab === 'target'" class="w-full flex-1 min-h-0 overflow-visible">
            <!-- TCP pwn 靶机：连接信息卡（栈溢出等，需在操作环境桌面里连接） -->
            <div v-if="isPwnTarget" class="flex flex-col h-full p-4 gap-4 overflow-y-auto">
              <div class="alert alert-info">
                <i class="fas fa-terminal"></i>
                <span>本靶机是 <b>TCP pwn 服务</b>，无法在网页中直接展示。请在左侧「操作环境」桌面的终端里连接它。</span>
              </div>
              <div class="card bg-base-200 flex-1">
                <div class="card-body p-6 gap-4 justify-center">
                  <div class="flex items-center gap-2">
                    <i class="fas fa-server text-primary text-lg"></i>
                    <span class="font-semibold text-lg">连接目标</span>
                    <span class="badge" :class="isTargetMachineRunning ? 'badge-success' : 'badge-ghost'">
                      {{ isTargetMachineRunning ? '已就绪' : '未准备' }}
                    </span>
                  </div>
                  <div class="font-mono bg-base-300 rounded px-3 py-2 text-base">{{ pwnTarget?.container }} : {{ pwnTarget?.port }}</div>
                  <div class="text-sm opacity-70">在操作环境终端里用 nc 连接：</div>
                  <div class="font-mono bg-base-300 rounded px-3 py-2 text-base">nc {{ pwnTarget?.container }} {{ pwnTarget?.port }}</div>
                  <div class="text-sm opacity-70">或用 pwntools 编写 exp：</div>
                  <pre class="bg-base-300 rounded p-3 text-sm overflow-x-auto"><code>from pwn import *
io = remote('{{ pwnTarget?.container }}', {{ pwnTarget?.port }})</code></pre>
                  <div class="text-sm opacity-60 mt-2">
                    提示：靶机已默认就绪并接入操作环境桌面网络，可直接按上述地址连接。找到栈溢出点、编写 exp 拿到 shell 后 <span class="font-mono">cat flag</span>，把 flag 填到下方任务点提交。
                  </div>
                </div>
              </div>
            </div>
            <!-- 靶机环境建设中占位（后续接入的实验） -->
            <div v-else-if="isTargetPending" class="flex flex-col items-center justify-center h-full p-4 text-center">
              <div class="text-6xl text-base-content/20 mb-4">
                <i class="fas fa-hard-hat"></i>
              </div>
              <h3 class="text-xl font-semibold mb-2">靶机环境建设中</h3>
              <p class="text-base-content/70 max-w-md">
                本实验的靶机环境正在建设中，敬请期待。<br />
                当前请在「操作环境」中自行编写栈溢出程序完成本地练习；后续将接入真实靶机，用于远程 getshell 拿 flag。
              </p>
            </div>
            <div v-else-if="targetMachineStatus === 'online' && targetMachineUrl" class="target-panel w-full flex flex-col">
              <!-- 添加调试信息和控制按钮 -->
              <div class="p-2 bg-info/10 text-info flex items-center justify-between flex-shrink-0">
                <div class="text-xs flex-grow flex items-center gap-2 flex-wrap">
                  <span>本机访问:</span>
                  <span class="font-mono">{{ targetMachineUrl }}</span>
                  <button 
                    class="btn btn-xs btn-ghost" 
                    @click="copyToClipboard(targetMachineUrl)"
                    title="复制本机访问地址"
                  >
                    <i class="fas fa-copy"></i>
                  </button>
                  <template v-if="operationTargetUrl">
                    <span class="opacity-60">|</span>
                    <span>操作环境内:</span>
                    <span class="font-mono">{{ operationTargetUrl }}</span>
                    <button
                      class="btn btn-xs btn-ghost"
                      @click="copyToClipboard(operationTargetUrl)"
                      title="复制操作环境内访问地址"
                    >
                      <i class="fas fa-copy"></i>
                    </button>
                  </template>
                </div>
                <div class="flex gap-2">
                  <button 
                    class="btn btn-xs btn-ghost" 
                    @click="refreshIframe"
                    title="刷新靶机"
                  >
                    <i class="fas fa-sync-alt"></i>
                  </button>
                  <button 
                    class="btn btn-xs btn-ghost" 
                    @click="openInNewWindow('target')"
                    title="在新窗口打开"
                  >
                    <i class="fas fa-external-link-alt"></i>
                  </button>
                  <button 
                    class="btn btn-xs btn-ghost" 
                    @click="openDirectUrl"
                    title="直接导航"
                  >
                    <i class="fas fa-link"></i>
                  </button>
                </div>
              </div>
              <iframe 
                :src="targetMachineUrl" 
                class="w-full flex-1 min-h-0 border-none target-iframe"
                @load="() => console.log('靶机iframe加载完成')"
                @error="(e) => console.error('靶机iframe加载失败', e)"
              ></iframe>
            </div>
            <div v-else class="flex flex-col items-center justify-center h-full p-4 text-center">
              <div class="text-6xl text-base-content/20 mb-4">
                <i class="fas fa-server"></i>
              </div>
              <div v-if="targetMachineStatus !== 'offline'" class="alert alert-warning max-w-md mb-4 text-left">
                <i class="fas fa-exclamation-triangle"></i>
                <div>
                  <h3 class="font-bold">靶机 Web 服务未就绪</h3>
                  <div class="text-sm">{{ targetMachineMessage || '靶机 Web 服务未就绪，请稍后刷新或重启实验环境。' }}</div>
                  <div v-if="targetMachineUrl" class="text-xs font-mono mt-1 break-all">{{ targetMachineUrl }}</div>
                </div>
              </div>
              <h3 class="text-xl font-semibold mb-2">靶机环境未启动</h3>
              <p class="text-base-content/70 mb-4">
                请先启动靶机环境
              </p>
              <button class="btn btn-primary btn-sm" @click="startTargetMachine" :disabled="isTargetLoading">
                <span class="loading loading-spinner loading-xs" v-if="isTargetLoading"></span>
                <i class="fas fa-play mr-1" v-else></i>
                {{ isTargetLoading ? '正在启动靶机...' : '启动靶机' }}
              </button>
            </div>
          </div>

          <!-- 未启动任何环境的提示 -->
          <div v-if="!activeEnvironmentTab" class="flex flex-col items-center justify-center flex-1 min-h-0 p-4 text-center">
            <div class="text-6xl text-base-content/20 mb-4">
              <i class="fas fa-desktop"></i>
            </div>
            <h3 class="text-xl font-semibold mb-2">未启动任何环境</h3>
            <p class="text-base-content/70 mb-4">
              请先启动操作环境或靶机环境
            </p>
            <div class="flex gap-2">
              <button class="btn btn-primary btn-sm" @click="toggleOperationMachine" :disabled="isOperationLoading">
                <i class="fas fa-play mr-1"></i>
                启动操作环境
              </button>
              <button class="btn btn-primary btn-sm" @click="startTargetMachine" :disabled="isTargetLoading">
                <i class="fas fa-play mr-1"></i>
                启动靶机
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 积分确认弹窗 -->
      <Transition name="modal">
        <dialog :class="{ modal: true, 'modal-open': showCostModal }">
          <div class="modal-box">
            <h3 class="font-bold text-lg">确认查看题解</h3>
            <p class="py-4">
              确认使用 {{ solutionCost }} 积分查看题解讨论吗？
              <span v-if="hasViewedDiscussion" class="text-success"> (您已经支付过，无需再次支付) </span>
            </p>
            <div class="flex justify-between items-center mb-4 border-t border-b py-2 mt-2">
              <span class="font-medium">当前积分余额:</span>
              <span class="text-success font-bold">{{ userPoints }} 积分</span>
            </div>
            <div class="modal-action">
              <button class="btn" @click="showCostModal = false">取消</button>
              <button class="btn btn-primary" @click="confirmViewDiscussion">确认</button>
            </div>
          </div>
        </dialog>
      </Transition>

      <Transition name="modal">
        <dialog :class="{ modal: true, 'modal-open': showEndExperimentModal }">
          <div class="modal-box">
            <h3 class="font-bold text-lg">
              <i class="fas fa-exclamation-triangle text-warning mr-2"></i>
              结束实验
            </h3>
            <p class="py-4">
              实验正在进行中，确定要结束实验吗？结束后系统将自动汇总实验事件并关闭靶机环境。
            </p>
            <div class="bg-base-200 p-3 rounded-lg mb-4">
              <div class="flex items-center gap-2 text-sm">
                <i class="fas fa-clock text-info"></i>
                <span>实验时长: {{ getLabDurationSeconds() }} 秒</span>
              </div>
              <div class="flex items-center gap-2 text-sm mt-1">
                <i class="fas fa-server text-info"></i>
                <span>靶机: {{ currentLabContainer || currentTargetContainerName || '未识别容器' }}</span>
              </div>
            </div>
            <div class="modal-action">
              <button class="btn" @click="cancelEndExperiment" :disabled="isEndingExperiment">继续实验</button>
              <button class="btn btn-error" @click="sendEventsAndEndLab" :disabled="isEndingExperiment">
                <span class="loading loading-spinner loading-xs" v-if="isEndingExperiment"></span>
                <i class="fas fa-stop mr-1" v-else></i>
                {{ isEndingExperiment ? '正在结束...' : '确认结束' }}
              </button>
            </div>
          </div>
        </dialog>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.container-fluid {
  width: 100%;
  max-width: 100%;
  margin: -20px auto;
  overflow-y: auto;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

/* 隐藏 Webkit 浏览器的滚动条 */
.container-fluid::-webkit-scrollbar {
  display: none;
}

html,
body {
  overflow-x: hidden;
  margin: 0;
  padding: 0;
  width: 100%;
}

/* 悬浮讨论输入框样式 */
.discussion-input-fixed {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 1rem;
  background-color: oklch(var(--b3));
  border-top: 2px solid oklch(var(--p));
  box-shadow: 0 -4px 6px -1px rgba(0, 0, 0, 0.3);
  z-index: 40;
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.discussion-input-container {
  background-color: oklch(var(--b2));
  padding: 1.25rem;
  border-radius: 0.75rem;
  border: 2px solid oklch(var(--p));
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  position: relative;
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  max-width: 100%;
  margin: 0 auto;
}

.discussion-input-container::before {
  content: '发表你的题解';
  position: absolute;
  top: -12px;
  left: 20px;
  background-color: oklch(var(--b3));
  padding: 0 10px;
  font-size: 14px;
  font-weight: bold;
  color: oklch(var(--p));
}

/* 讨论列表区域样式 */
.discussion-list {
  padding: 1rem;
  border-radius: 0.5rem;
  background-color: oklch(var(--b1));
  margin-bottom: 100px; /* 为底部固定输入框留出更多空间 */
}

.animate-float {
  animation: float 10s ease-in-out infinite;
}

.animate-slide-down {
  animation: slideDown 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.animate-slide-up {
  opacity: 0;
  animation: slideUp 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(10deg);
  }
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
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

@keyframes particleFloat {
  0% {
    transform: translateY(0) translateX(0);
    opacity: 0;
  }
  20% {
    opacity: 1;
  }
  80% {
    opacity: 1;
  }
  100% {
    transform: translateY(-100vh) translateX(50px);
    opacity: 0;
  }
}

/* 页面切换动画 */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1);
  position: absolute;
  width: 100%;
}

.slide-fade-enter-from {
  opacity: 0;
  transform: scale(0.95);
  filter: blur(10px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
  filter: blur(10px);
}

.slide-fade-enter-to,
.slide-fade-leave-from {
  opacity: 1;
  transform: scale(1);
  filter: blur(0);
}

/* 添加内容动画 */
.content-enter-active,
.content-leave-active {
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.content-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.content-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* 添加卡片动画 */
.card {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

/* 添加按钮动画 */
.btn {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

/* 添加讨论列表动画 */
.discussion-list > div {
  opacity: 0;
  animation: slideIn 0.5s ease-out forwards;
}

.discussion-list > div:nth-child(1) {
  animation-delay: 0.1s;
}
.discussion-list > div:nth-child(2) {
  animation-delay: 0.2s;
}
.discussion-list > div:nth-child(3) {
  animation-delay: 0.3s;
}
.discussion-list > div:nth-child(4) {
  animation-delay: 0.4s;
}
.discussion-list > div:nth-child(5) {
  animation-delay: 0.5s;
}
.discussion-list > div:nth-child(n + 6) {
  animation-delay: 0.6s;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 添加环境切换动画 */
.environment-tab-enter-active,
.environment-tab-leave-active {
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.environment-tab-enter-from,
.environment-tab-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

/* 添加模态框动画 */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

/* 添加加载动画 */
.loading-spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 环境控制按钮布局切换动画 */
.environment-controls {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  width: 100%;
  padding: 1rem 0;
}

.environment-controls > div {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 当切换为垂直布局时的动画 */
.environment-controls.flex-col > div {
  transform-origin: top;
  animation: slideDown 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

/* 当切换为水平布局时的动画 */
.environment-controls:not(.flex-col) > div {
  transform-origin: left;
  animation: slideRight 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slideRight {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.markdown-content {
  width: 100%;
  overflow-wrap: break-word;
  word-wrap: break-word;
  word-break: break-word;
}

.markdown-content :deep(pre) {
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-x: auto;
  max-width: 100%;
}

.markdown-content :deep(code) {
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-x: auto;
  max-width: 100%;
}

.markdown-content :deep(p) {
  max-width: 100%;
  overflow-wrap: break-word;
}

/* 移除之前的宽度调整样式 */
.w-half {
  width: 50%;
  transition: width 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.w-full {
  width: 100%;
  transition: width 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.environment-frame {
  height: calc(100vh - 6.5rem);
  min-height: 860px;
  overflow: hidden;
}

.target-panel {
  height: 100%;
  min-height: 0;
}

/* 确保环境标签页的层级正确 */
.fixed {
  z-index: 50;
}

/* 当环境标签页打开时，调整讨论输入框的位置 */
.fixed + .discussion-input-fixed {
  right: 50%;
}

.animate-fade-in {
  animation: fadeIn 0.5s ease-out;
}

.animate-fade-in-down {
  animation: fadeInDown 0.5s ease-out forwards;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 添加 flag 提交结果样式 */
.alert {
  padding: 0.75rem;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
}

.alert-success {
  background-color: oklch(var(--su) / 0.1);
  color: oklch(var(--su));
  border: 1px solid oklch(var(--su));
}

.alert-error {
  background-color: oklch(var(--er) / 0.1);
  color: oklch(var(--er));
  border: 1px solid oklch(var(--er));
}
</style>
