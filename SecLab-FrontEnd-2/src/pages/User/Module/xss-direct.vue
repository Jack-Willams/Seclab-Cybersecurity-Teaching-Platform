<script setup lang="ts">
import { XSSExperiment } from '../../../data/XSSExperiment';
import MarkdownRenderer from "../../../components/MarkdownRenderer.vue";
import { ref, onMounted } from 'vue';

// 这个组件是一个简化版的XSS测试环境，专门用于直接展示XSS漏洞
const message = ref('');
const displayedMessage = ref('');
const flag = ref('XSS_FLAG{this_is_a_hidden_flag_for_xss_test}');

function submitMessage() {
  // 故意不过滤，直接插入HTML，模拟XSS漏洞
  displayedMessage.value = message.value;
}

onMounted(() => {
  // 在页面加载时添加一些示例消息
  const exampleMessages = [
    '欢迎来到XSS测试环境',
    '这是一个<b>安全</b>的消息',
    '请尝试提交一些测试内容'
  ];
  
  displayedMessage.value = exampleMessages[0];
});
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <div class="bg-base-200 p-4 shadow-lg rounded-lg mb-6">
      <div class="flex justify-between items-center">
        <div class="flex items-center gap-2">
          <i class="fas fa-bug text-warning text-2xl"></i>
          <h1 class="text-2xl font-bold">XSS漏洞测试环境</h1>
        </div>
        <div class="badge badge-warning">直接测试</div>
      </div>
      <p class="mt-2">这是一个用于测试XSS漏洞的简单环境，请尝试注入脚本以获取隐藏的flag值。</p>
    </div>

    <!-- 留言板模拟 -->
    <div class="card bg-base-100 shadow-xl">
      <div class="card-body">
        <h2 class="card-title">留言板</h2>
        <p>在下方输入您的留言，点击提交后将显示在留言区域。</p>
        
        <div class="form-control">
          <label class="label">
            <span class="label-text">您的留言：</span>
          </label>
          <textarea v-model="message" class="textarea textarea-bordered h-24" placeholder="输入留言内容..."></textarea>
        </div>
        
        <div class="card-actions justify-end mt-4">
          <button @click="submitMessage" class="btn btn-primary">提交留言</button>
        </div>
        
        <!-- 留言显示区域 -->
        <div class="mt-6">
          <h3 class="font-bold mb-2">留言区：</h3>
          <div class="bg-base-200 p-4 rounded-lg min-h-[100px]">
            <!-- 故意使用v-html以允许XSS -->
            <div v-html="displayedMessage"></div>
          </div>
        </div>
        
        <!-- 隐藏的flag -->
        <div style="display: none;">
          <span id="hidden-flag">{{ flag }}</span>
        </div>
      </div>
    </div>
    
    <!-- 提示区域 -->
    <div class="card bg-base-100 shadow-xl mt-6">
      <div class="card-body">
        <h2 class="card-title">
          <i class="fas fa-lightbulb text-warning mr-2"></i>
          提示
        </h2>
        <ul class="list-disc list-inside space-y-2">
          <li>尝试在留言中插入JavaScript代码</li>
          <li>页面中隐藏了一个flag值，请尝试通过XSS获取它</li>
          <li>成功的XSS攻击可以操作页面的DOM元素</li>
          <li>考虑使用<code>document.getElementById</code>或其他DOM API</li>
        </ul>
      </div>
    </div>
  </div>
</template> 