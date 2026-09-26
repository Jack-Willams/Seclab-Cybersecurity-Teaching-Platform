<script setup lang="ts">
import { ref, watch } from 'vue';

const emit = defineEmits<{
  (e: 'verify', phone: string): void;
  (e: 'back'): void;
}>();

const phone = ref('');
const verificationCode = ref('');
const countdown = ref(0);
const canSubmit = ref(false);
const phoneError = ref('');
const isPhoneValid = ref(false);
const isPhoneRegistered = ref(false);

// 手机号验证规则
const phoneRegex = /^1[3-9]\d{9}$/;

// 检查手机号是否有效
const validatePhone = (phoneNumber: string) => {
  if (!phoneNumber) {
    phoneError.value = '请输入手机号';
    isPhoneValid.value = false;
    return false;
  }
  
  if (!phoneRegex.test(phoneNumber)) {
    phoneError.value = '请输入有效的手机号';
    isPhoneValid.value = false;
    return false;
  }
  
  // 检查是否已注册（模拟：只有11111111111未注册）
  if (phoneNumber === '11111111111') {
    phoneError.value = '该手机号未注册';
    isPhoneRegistered.value = false;
    isPhoneValid.value = false;
    return false;
  }
  
  phoneError.value = '';
  isPhoneValid.value = true;
  isPhoneRegistered.value = true;
  return true;
};

// 监听手机号变化
watch(phone, (newPhone) => {
  validatePhone(newPhone);
});

// 发送验证码
const sendVerificationCode = () => {
  if (!validatePhone(phone.value)) {
    return;
  }
  
  // 设置60秒倒计时
  countdown.value = 60;
  const timer = setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) {
      clearInterval(timer);
    }
  }, 1000);
  
  // 启用提交按钮
  canSubmit.value = true;
};

// 验证验证码
const verifyCode = () => {
  if (!verificationCode.value) {
    alert('请输入验证码');
    return;
  }
  
  // 模拟验证通过，任何验证码都可以
  emit('verify', phone.value);
};

// 返回登录
const backToLogin = () => {
  emit('back');
};
</script>

<template>
  <div class="forgot-password-form">
    <div class="form-control">
      <label class="label">
        <span class="label-text flex items-center gap-2">
          <i class="fas fa-mobile-alt text-primary"></i>
          手机号码
        </span>
      </label>
      <div class="relative">
        <input 
          type="text" 
          v-model="phone" 
          placeholder="请输入手机号" 
          class="input input-bordered bg-base-200/50 focus:bg-base-100 transition-all
                 hover:input-primary focus:input-primary w-full"
          :class="{
            'input-error': phoneError,
            'input-success': isPhoneValid && !phoneError
          }"
          maxlength="11"
        />
        <div v-if="phone" class="absolute right-3 top-1/2 -translate-y-1/2">
          <i 
            :class="[
              'fas text-lg',
              isPhoneValid ? 'fa-check-circle text-success' : 'fa-times-circle text-error'
            ]"
          ></i>
        </div>
      </div>
      <label class="label" v-if="phoneError">
        <span class="label-text-alt text-error">{{ phoneError }}</span>
      </label>
    </div>
    
    <div class="form-control mt-4">
      <label class="label">
        <span class="label-text flex items-center gap-2">
          <i class="fas fa-key text-primary"></i>
          验证码
        </span>
      </label>
      <div class="flex gap-2">
        <input 
          type="text" 
          v-model="verificationCode" 
          placeholder="请输入验证码" 
          class="input input-bordered bg-base-200/50 focus:bg-base-100 transition-all
                 hover:input-primary focus:input-primary flex-grow"
          maxlength="6"
        />
        <button 
          @click="sendVerificationCode" 
          class="btn btn-outline btn-primary" 
          :disabled="countdown > 0 || !isPhoneValid"
          :class="[
            countdown > 0 ? 'opacity-70' : '',
            !isPhoneValid ? 'btn-disabled' : ''
          ]"
        >
          {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
        </button>
      </div>
    </div>
    
    <div class="form-actions mt-6 flex flex-col gap-4">
      <button 
        @click="verifyCode" 
        class="btn btn-primary w-full" 
        :disabled="!canSubmit || !verificationCode"
      >
        <i class="fas fa-check-circle mr-2"></i>
        重置密码
      </button>
      
      <button 
        @click="backToLogin" 
        class="btn btn-outline btn-neutral w-full"
      >
        <i class="fas fa-arrow-left mr-2"></i>
        返回登录
      </button>
    </div>
    
    <div class="form-info mt-6 text-sm text-center text-base-content/60">
      <p>我们将发送验证码到您的手机，请注意查收</p>
      <p class="mt-2">如果您没有收到验证码，可以在倒计时结束后重新发送</p>
    </div>
  </div>
</template>

<style scoped>
.forgot-password-form {
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

.form-actions button {
  transition: all 0.3s ease;
}

.form-actions button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.input-success {
  border-color: #2ecc71;
}

.input-error {
  border-color: #ff4757;
}

.btn-disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* 添加输入框右侧图标的动画 */
.fa-check-circle, .fa-times-circle {
  animation: scaleIn 0.3s ease-out;
}

@keyframes scaleIn {
  from {
    transform: scale(0);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}
</style> 