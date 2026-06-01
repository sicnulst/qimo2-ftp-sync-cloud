<template>
  <div class="login-page">
    <!-- 动态背景 -->
    <div class="bg-mesh"></div>
    <div class="bg-orbs">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-card animate-fadeInUp">
      <!-- Logo 区域 -->
      <div class="brand-area">
        <div class="brand-icon">
          <el-icon :size="32" color="white"><Connection /></el-icon>
        </div>
        <div class="brand-text">
          <h1>FTP 私有云盘</h1>
          <p>基于 watchdog 的文件自动同步系统</p>
        </div>
      </div>

      <!-- Tab 切换 -->
      <div class="tab-switch">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'login' }"
          @click="activeTab = 'login'"
        >
          登录
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'register' }"
          @click="activeTab = 'register'"
        >
          注册
        </button>
        <div class="tab-indicator" :class="activeTab === 'register' ? 'right' : 'left'"></div>
      </div>

      <!-- 登录表单 -->
      <transition name="form-fade" mode="out-in">
        <div v-if="activeTab === 'login'" key="login" class="form-area">
          <el-form :model="loginForm" :rules="rules" ref="loginRef" @submit.prevent="handleLogin">
            <el-form-item prop="username">
              <div class="input-wrapper">
                <el-icon class="input-icon"><User /></el-icon>
                <el-input
                  v-model="loginForm.username"
                  placeholder="请输入用户名"
                  size="large"
                  class="custom-input"
                />
              </div>
            </el-form-item>
            <el-form-item prop="password">
              <div class="input-wrapper">
                <el-icon class="input-icon"><Lock /></el-icon>
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="请输入密码"
                  size="large"
                  show-password
                  class="custom-input"
                  @keyup.enter="handleLogin"
                />
              </div>
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              class="submit-btn"
              :loading="loading"
              @click="handleLogin"
            >
              <span v-if="!loading">登 录</span>
              <span v-else>登录中...</span>
            </el-button>
          </el-form>
          <p class="form-hint">还没有账号？<a @click="activeTab = 'register'">立即注册 →</a></p>
        </div>

        <!-- 注册表单 -->
        <div v-else key="register" class="form-area">
          <el-form :model="registerForm" :rules="registerRules" ref="registerRef" @submit.prevent="handleRegister">
            <el-form-item prop="username">
              <div class="input-wrapper">
                <el-icon class="input-icon"><User /></el-icon>
                <el-input
                  v-model="registerForm.username"
                  placeholder="用户名（至少3位）"
                  size="large"
                  class="custom-input"
                />
              </div>
            </el-form-item>
            <el-form-item prop="password">
              <div class="input-wrapper">
                <el-icon class="input-icon"><Lock /></el-icon>
                <el-input
                  v-model="registerForm.password"
                  type="password"
                  placeholder="密码（至少6位）"
                  size="large"
                  show-password
                  class="custom-input"
                />
              </div>
            </el-form-item>
            <el-form-item prop="confirmPassword">
              <div class="input-wrapper">
                <el-icon class="input-icon"><CircleCheck /></el-icon>
                <el-input
                  v-model="registerForm.confirmPassword"
                  type="password"
                  placeholder="确认密码"
                  size="large"
                  show-password
                  class="custom-input"
                />
              </div>
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              class="submit-btn"
              :loading="loading"
              @click="handleRegister"
            >
              <span v-if="!loading">创建账号</span>
              <span v-else>注册中...</span>
            </el-button>
          </el-form>
          <p class="form-hint">已有账号？<a @click="activeTab = 'login'">← 返回登录</a></p>
        </div>
      </transition>
    </div>

    <!-- 底部版权 -->
    <div class="footer-text">
      FTP私有同步云盘系统 &nbsp;·&nbsp; 学习用途
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '../api'

const router = useRouter()
const activeTab = ref('login')
const loading = ref(false)
const loginRef = ref()
const registerRef = ref()

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', password: '', confirmPassword: '' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少3位', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPassword: [{ required: true, message: '请确认密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  try {
    await loginRef.value.validate()
    loading.value = true
    const res = await authApi.login(loginForm)
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('user', JSON.stringify(res.user))
    ElMessage({ message: '登录成功，欢迎回来！', type: 'success', duration: 2000 })
    router.push('/dashboard')
  } catch (e) {
    if (e && e.error) ElMessage.error(e.error)
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  try {
    await registerRef.value.validate()
    if (registerForm.password !== registerForm.confirmPassword) {
      ElMessage.error('两次输入的密码不一致')
      return
    }
    loading.value = true
    const res = await authApi.register(registerForm)
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('user', JSON.stringify(res.user))
    ElMessage({ message: '注册成功，欢迎使用！', type: 'success', duration: 2000 })
    router.push('/dashboard')
  } catch (e) {
    if (e && e.error) ElMessage.error(e.error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 页面容器 */
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0e1a;
  position: relative;
  overflow: hidden;
}

/* 网格背景 */
.bg-mesh {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(59, 130, 246, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 130, 246, 0.05) 1px, transparent 1px);
  background-size: 40px 40px;
  mask-image: radial-gradient(ellipse at center, black 40%, transparent 80%);
}

/* 光晕球 */
.bg-orbs { position: absolute; inset: 0; pointer-events: none; }
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
}
.orb-1 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, #3b82f6, transparent);
  top: -100px; left: -100px;
  animation: orbFloat 8s ease-in-out infinite;
}
.orb-2 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, #8b5cf6, transparent);
  bottom: -80px; right: -80px;
  animation: orbFloat 10s ease-in-out infinite reverse;
}
.orb-3 {
  width: 300px; height: 300px;
  background: radial-gradient(circle, #10b981, transparent);
  top: 40%; left: 50%;
  transform: translate(-50%, -50%);
  animation: orbFloat 12s ease-in-out infinite;
}

@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -20px) scale(1.05); }
  66% { transform: translate(-20px, 30px) scale(0.95); }
}

/* 卡片 */
.login-card {
  position: relative;
  z-index: 10;
  width: 420px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 24px;
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow:
    0 32px 64px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.06) inset;
}

/* 品牌区 */
.brand-area {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
}

.brand-icon {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.4);
  flex-shrink: 0;
}

.brand-text h1 {
  font-size: 22px;
  font-weight: 700;
  color: white;
  line-height: 1.2;
}

.brand-text p {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  margin-top: 4px;
}

/* Tab 切换 */
.tab-switch {
  position: relative;
  display: flex;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 28px;
}

.tab-btn {
  flex: 1;
  padding: 9px 0;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 8px;
  position: relative;
  z-index: 2;
  transition: color 0.25s ease;
}

.tab-btn.active {
  color: white;
}

.tab-indicator {
  position: absolute;
  top: 4px;
  bottom: 4px;
  width: calc(50% - 4px);
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
  transition: left 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  z-index: 1;
}
.tab-indicator.left { left: 4px; }
.tab-indicator.right { left: calc(50%); }

/* 表单 */
.form-area {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-area :deep(.el-form-item) {
  margin-bottom: 14px !important;
}

.input-wrapper {
  position: relative;
  width: 100%;
}

.input-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  color: rgba(255, 255, 255, 0.4);
  font-size: 16px;
  pointer-events: none;
}

.custom-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.15) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  padding-left: 40px !important;
  transition: all 0.25s ease !important;
}

.custom-input :deep(.el-input__wrapper:hover) {
  background: rgba(255, 255, 255, 0.08) !important;
  border-color: rgba(59, 130, 246, 0.5) !important;
  box-shadow: none !important;
}

.custom-input :deep(.el-input__wrapper.is-focus) {
  background: rgba(59, 130, 246, 0.08) !important;
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
}

.custom-input :deep(.el-input__inner) {
  color: white !important;
  font-size: 14px !important;
  background: transparent !important;
}

.custom-input :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.3) !important;
}

.custom-input :deep(.el-input__suffix) {
  color: rgba(255, 255, 255, 0.3) !important;
}

/* 提交按钮 */
.submit-btn {
  width: 100% !important;
  height: 46px !important;
  border-radius: 12px !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  margin-top: 6px !important;
  background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
  border-color: transparent !important;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.45) !important;
  transition: all 0.25s ease !important;
  letter-spacing: 1px;
}

.submit-btn:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.5) !important;
}

.submit-btn:active {
  transform: translateY(0) !important;
}

/* 底部提示 */
.form-hint {
  text-align: center;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.35);
  margin-top: 16px;
}

.form-hint a {
  color: #60a5fa;
  cursor: pointer;
  transition: color 0.2s;
}

.form-hint a:hover {
  color: #93c5fd;
  text-decoration: underline;
}

/* 底部 */
.footer-text {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  color: rgba(255, 255, 255, 0.2);
  font-size: 12px;
  white-space: nowrap;
  z-index: 10;
}

/* 表单过渡动画 */
.form-fade-enter-active,
.form-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.form-fade-enter-from {
  opacity: 0;
  transform: translateX(10px);
}
.form-fade-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

/* 表单验证错误 */
.form-area :deep(.el-form-item__error) {
  color: #f87171 !important;
  font-size: 12px !important;
  padding-top: 3px !important;
}

/* 覆写全局卡片样式（登录页专用） */
.login-card {
  border-radius: 24px !important;
  box-shadow: 0 32px 64px rgba(0, 0, 0, 0.4) !important;
}

/* 登录页输入框：清除全局灰色底色 */
.login-page :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.05) !important;
  box-shadow: none !important;
}
</style>
