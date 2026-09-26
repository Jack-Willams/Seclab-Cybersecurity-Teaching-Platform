<script setup lang="ts">
import { ref, watch } from 'vue';

const props = defineProps<{
  phone: string;
}>();

const emit = defineEmits<{
  (e: 'reset'): void;
  (e: 'back'): void;
}>();

const newPassword = ref('');
const confirmPassword = ref('');
const passwordStrength = ref(0);
const passwordMatch = ref(true);
const passwordWarning = ref('');
const duplicateCount = ref(0);

// 常见弱密码列表及对应重复次数
const commonPasswords = {
  '123456': 1053,
  'password': 982,
  '12345678': 765,
  'qwerty': 635,
  '123456789': 544,
  '111111': 487,
  '1234567': 352,
  'sunshine': 331,
  'qwerty123': 326,
  'iloveyou': 294,
  'admin': 285,
  'welcome': 261,
  'monkey': 252,
  'login': 247,
  'abc123': 238,
  'starwars': 220,
  'dragon': 214,
  'passw0rd': 203,
  'master': 192,
  'football': 188,
  '123123': 180,
  '654321': 173,
  'bailey': 152,
  'freedom': 144,
  'shadow': 139,
  'qwertyuiop': 121,
  '12345': 119,
  'batman': 111,
  'trustno1': 103
};

// 检查密码是否匹配
watch(confirmPassword, () => {
  if (confirmPassword.value && newPassword.value) {
    passwordMatch.value = confirmPassword.value === newPassword.value;
  } else {
    passwordMatch.value = true;
  }
});

// 检查密码强度和重复度
watch(newPassword, () => {
  checkPasswordStrength();
  
  // 清空确认密码，确保用户重新输入
  if (confirmPassword.value) {
    confirmPassword.value = '';
    passwordMatch.value = true;
  }
});

// 评估密码强度并检查常见密码
const checkPasswordStrength = () => {
  const password = newPassword.value;
  
  // 重置警告
  passwordWarning.value = '';
  duplicateCount.value = 0;
  
  if (!password) {
    passwordStrength.value = 0;
    return;
  }
  
  // 检查是否是常见密码
  if (commonPasswords[password]) {
    duplicateCount.value = commonPasswords[password];
    passwordWarning.value = `此密码已被使用 ${duplicateCount.value} 次，请设置更安全的密码`;
    passwordStrength.value = 1; // 弱密码
    return;
  }
  
  // 密码强度评估
  let strength = 0;
  
  // 长度检查
  if (password.length >= 8) strength += 1;
  if (password.length >= 12) strength += 1;
  
  // 复杂度检查
  if (/[A-Z]/.test(password)) strength += 1;
  if (/[a-z]/.test(password)) strength += 1;
  if (/[0-9]/.test(password)) strength += 1;
  if (/[^A-Za-z0-9]/.test(password)) strength += 1;
  
  // 设置强度值 (最高5)
  passwordStrength.value = Math.min(5, strength);
  
  // 额外检查简单模式
  if (
    /^123/.test(password) || 
    /^abc/.test(password) || 
    /^qwerty/.test(password) || 
    /^password/i.test(password)
  ) {
    // 模拟常见简单模式
    duplicateCount.value = Math.floor(Math.random() * 300) + 100;
    passwordWarning.value = `此类密码已被使用 ${duplicateCount.value} 次，请设置更安全的密码`;
    passwordStrength.value = Math.min(passwordStrength.value, 2);
  }
};

// 获取密码强度描述
const getStrengthText = () => {
  const strength = passwordStrength.value;
  if (strength === 0) return '';
  if (strength === 1) return '非常弱';
  if (strength === 2) return '弱';
  if (strength === 3) return '中等';
  if (strength === 4) return '强';
  return '非常强';
};

// 获取密码强度颜色
const getStrengthColor = () => {
  const strength = passwordStrength.value;
  if (strength <= 1) return 'bg-error';
  if (strength === 2) return 'bg-warning';
  if (strength === 3) return 'bg-info';
  if (strength >= 4) return 'bg-success';
  return '';
};

// 提交重置密码
const handleSubmit = () => {
  if (!newPassword.value) {
    alert('请输入新密码');
    return;
  }
  
  if (!confirmPassword.value) {
    alert('请确认新密码');
    return;
  }
  
  if (newPassword.value !== confirmPassword.value) {
    alert('两次输入的密码不一致');
    return;
  }
  
  if (passwordStrength.value < 3) {
    const confirmWeak = confirm('您设置的密码强度较弱，是否继续使用？');
    if (!confirmWeak) return;
  }
  
  // 模拟密码重置
  emit('reset');
};

// 返回上一步
const goBack = () => {
  emit('back');
};
</script>

<template>
  <div class="reset-password-form">
    <div class="phone-info mb-6 text-center">
      <div class="badge badge-neutral mb-2">
        <i class="fas fa-phone-alt mr-2"></i>
        {{ phone || '手机验证成功' }}
      </div>
      <p class="text-sm text-base-content/60">请设置您的新密码</p>
    </div>
    
    <div class="form-control">
      <label class="label">
        <span class="label-text flex items-center gap-2">
          <i class="fas fa-lock text-primary"></i>
          新密码
        </span>
      </label>
      <input 
        type="password" 
        v-model="newPassword" 
        placeholder="请输入新密码" 
        class="input input-bordered bg-base-200/50 focus:bg-base-100 transition-all
               hover:input-primary focus:input-primary"
      />
      
      <!-- 密码强度指示器 -->
      <div v-if="newPassword" class="password-strength mt-2">
        <div class="flex items-center justify-between mb-1">
          <span class="text-xs">密码强度：{{ getStrengthText() }}</span>
          <span class="text-xs" :class="passwordStrength >= 3 ? 'text-success' : 'text-warning'">
            {{ passwordStrength >= 3 ? '安全' : '不安全' }}
          </span>
        </div>
        <div class="w-full bg-base-300 rounded-full h-1.5">
          <div 
            class="h-1.5 rounded-full transition-all duration-300" 
            :class="getStrengthColor()"
            :style="{ width: `${passwordStrength * 20}%` }"
          ></div>
        </div>
      </div>
      
      <!-- 密码警告 -->
      <div v-if="passwordWarning" class="password-warning mt-2 text-sm text-error flex items-center gap-2">
        <i class="fas fa-exclamation-triangle"></i>
        <span>{{ passwordWarning }}</span>
      </div>
    </div>
    
    <div class="form-control mt-4">
      <label class="label">
        <span class="label-text flex items-center gap-2">
          <i class="fas fa-check-circle text-primary"></i>
          确认密码
        </span>
      </label>
      <input 
        type="password" 
        v-model="confirmPassword" 
        placeholder="请再次输入新密码" 
        class="input input-bordered bg-base-200/50 focus:bg-base-100 transition-all
               hover:input-primary focus:input-primary"
        :class="{ 'input-error': !passwordMatch && confirmPassword }"
      />
      <label class="label" v-if="!passwordMatch && confirmPassword">
        <span class="label-text-alt text-error">两次输入的密码不一致</span>
      </label>
    </div>
    
    <div class="password-tips mt-4">
      <p class="text-xs text-base-content/60">
        <i class="fas fa-info-circle mr-1"></i>
        密码安全提示：
      </p>
      <ul class="text-xs text-base-content/60 mt-1 list-disc list-inside space-y-1">
        <li>长度至少8个字符</li>
        <li>包含大小写字母、数字和特殊符号</li>
        <li>避免使用常见密码和个人信息</li>
      </ul>
    </div>
    
    <div class="form-actions mt-6 flex flex-col gap-4">
      <button 
        @click="handleSubmit" 
        class="btn btn-primary w-full" 
        :disabled="!newPassword || !confirmPassword || !passwordMatch"
      >
        <i class="fas fa-check-circle mr-2"></i>
        确认重置
      </button>
      
      <button 
        @click="goBack" 
        class="btn btn-outline btn-neutral w-full"
      >
        <i class="fas fa-arrow-left mr-2"></i>
        返回
      </button>
    </div>
  </div>
</template>

<style scoped>
.reset-password-form {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.form-control input {
  transition: all 0.3s ease;
}

.form-control input:focus {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.password-warning {
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-5px); }
  40%, 80% { transform: translateX(5px); }
}

.badge {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 0.7; }
  50% { opacity: 1; }
  100% { opacity: 0.7; }
}
</style> 