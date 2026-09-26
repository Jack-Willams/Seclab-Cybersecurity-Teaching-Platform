<template>
  <div class="min-h-screen flex flex-col mt-16">
    <!-- 页面内容 -->
    <div class="w-full mx-auto flex-grow flex flex-col px-4 py-8">
      <div class="card bg-base-100 shadow-xl border border-base-200 max-w-4xl mx-auto w-full">
        <div class="card-body">
          <h2 class="card-title text-2xl font-bold mb-4">悬浮聊天窗页面</h2>
          
          <div class="mb-8">
            <p class="mb-4">这个页面展示了如何在其他页面中使用悬浮聊天窗组件。用户可以在浏览其他内容的同时，随时与AI助手进行交流。</p>
            
            <div class="alert alert-info mb-4">
              <i class="fas fa-info-circle mr-2"></i>
              <span>悬浮窗可以拖动到屏幕的任意位置，也可以最小化、最大化或关闭。</span>
            </div>
            
            <div class="flex gap-4 flex-wrap">
              <button 
                @click="toggleChatVisibility" 
                class="btn btn-primary"
              >
                <i class="fas fa-comment-alt mr-2"></i>
                {{ isChatVisible ? '隐藏聊天窗' : '显示聊天窗' }}
              </button>
              
              <button 
                @click="resetChatPosition" 
                class="btn btn-outline"
              >
                <i class="fas fa-undo mr-2"></i>
                重置位置
              </button>
            </div>
          </div>
          
          <div class="divider">页面内容示例</div>
          
          <!-- 示例内容 -->
          <div class="prose max-w-none">
            <h3>网络安全学习路径</h3>
            <p>网络安全是一个广泛的领域，包含多个专业方向。以下是一些常见的学习路径：</p>
            
            <ul>
              <li><strong>Web安全</strong> - 包括XSS、CSRF、SQL注入等常见漏洞的理解与防御</li>
              <li><strong>网络渗透测试</strong> - 学习如何评估系统安全性并找出潜在漏洞</li>
              <li><strong>安全开发</strong> - 编写安全的代码，学习安全编码实践</li>
              <li><strong>密码学</strong> - 加密算法、哈希函数、数字签名等</li>
              <li><strong>恶意软件分析</strong> - 学习如何分析病毒、木马等恶意程序</li>
            </ul>
            
            <p>无论您选择哪个方向，建议先建立扎实的计算机网络、操作系统和编程基础知识。可以随时通过悬浮聊天窗口向AI助手询问更详细的学习建议！</p>

            <h3>实践项目建议</h3>
            <p>以下是一些实践项目建议，可以帮助您巩固所学知识：</p>
            
            <ol>
              <li>搭建一个简单的网站并进行安全加固</li>
              <li>使用开源工具对靶场环境进行安全测试</li>
              <li>开发一个简单的加密通信工具</li>
              <li>参与CTF（Capture The Flag）比赛</li>
              <li>贡献开源安全项目</li>
            </ol>
            
            <p>如果您对任何项目感兴趣，可以点击右下角的聊天图标，向AI助手询问更多详细信息。</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 悬浮聊天窗组件 -->
    <FloatingChat 
      v-if="isChatVisible" 
      :initial-position="chatPosition"
      @close="isChatVisible = false" 
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FloatingChat from '../../../components/FloatingChat.vue'

// 控制聊天窗口的显示状态
const isChatVisible = ref(true)
const chatPosition = ref({ x: 20, y: 20 })

// 切换聊天窗口显示状态
const toggleChatVisibility = () => {
  isChatVisible.value = !isChatVisible.value
}

// 重置聊天窗口位置
const resetChatPosition = () => {
  chatPosition.value = { x: 20, y: 20 }
}
</script>

<style scoped>
.divider {
  margin: 2rem 0;
}
</style> 
