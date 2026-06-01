<template>
  <div class="layout-root">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: isCollapse }">
      <!-- Logo -->
      <div class="sidebar-logo" @click="router.push('/dashboard')">
        <div class="logo-icon">
          <el-icon :size="20" color="white"><Connection /></el-icon>
        </div>
        <transition name="logo-text-fade">
          <span v-if="!isCollapse" class="logo-name">云同步系统</span>
        </transition>
      </div>

      <!-- 导航菜单 -->
      <nav class="sidebar-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
        >
          <div class="nav-icon">
            <el-icon :size="18"><component :is="item.icon" /></el-icon>
          </div>
          <transition name="nav-text-fade">
            <span v-if="!isCollapse" class="nav-label">{{ item.label }}</span>
          </transition>
          <div v-if="!isCollapse && route.path === item.path" class="active-indicator"></div>
        </router-link>
      </nav>

      <!-- 底部折叠按钮 -->
      <div class="sidebar-footer">
        <button class="collapse-btn" @click="isCollapse = !isCollapse">
          <el-icon :size="16">
            <component :is="isCollapse ? 'Expand' : 'Fold'" />
          </el-icon>
          <span v-if="!isCollapse" class="collapse-label">收起菜单</span>
        </button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-wrapper">
      <!-- 顶部栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <!-- 面包屑 -->
          <div class="breadcrumb-area">
            <el-icon class="breadcrumb-home" @click="router.push('/dashboard')"><HomeFilled /></el-icon>
            <el-icon class="breadcrumb-sep"><ArrowRight /></el-icon>
            <span class="breadcrumb-current">{{ currentTitle }}</span>
          </div>
        </div>

        <div class="topbar-right">
          <!-- FTP 状态指示 -->
          <div class="ftp-badge" :class="ftpStatus.is_running ? 'online' : 'offline'">
            <span class="badge-dot"></span>
            <span class="badge-text">FTP {{ ftpStatus.is_running ? '运行中' : '已停止' }}</span>
          </div>

          <!-- 分隔线 -->
          <div class="divider"></div>

          <!-- 用户信息 -->
          <el-dropdown @command="handleCommand" trigger="click">
            <div class="user-chip">
              <div class="user-avatar">{{ username.charAt(0).toUpperCase() }}</div>
              <span class="user-name">{{ username }}</span>
              <el-icon :size="14" class="user-arrow"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu class="user-menu">
                <el-dropdown-item disabled>
                  <span class="menu-user-info">
                    <strong>{{ username }}</strong>
                    <small>当前登录用户</small>
                  </span>
                </el-dropdown-item>
                <el-dropdown-item divided command="logout" class="logout-item">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 内容区 -->
      <main class="page-content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ftpApi } from '../api'

const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)
const ftpStatus = ref({ is_running: false })

const menuItems = [
  { path: '/dashboard', label: '控制面板', icon: 'DataBoard' },
  { path: '/servers', label: 'FTP服务器', icon: 'Connection' },
  { path: '/tasks', label: '同步任务', icon: 'List' },
  { path: '/files', label: '文件浏览', icon: 'FolderOpened' },
  { path: '/history', label: '同步历史', icon: 'Clock' },
]

const username = computed(() => {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  return user.username || '用户'
})

const currentTitle = computed(() => {
  const titles = {
    '/dashboard': '控制面板',
    '/servers': 'FTP 服务器',
    '/tasks': '同步任务',
    '/files': '文件浏览',
    '/history': '同步历史'
  }
  return titles[route.path] || '首页'
})

const handleCommand = (cmd) => {
  if (cmd === 'logout') {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    router.push('/login')
  }
}

const checkFtpStatus = async () => {
  try {
    ftpStatus.value = await ftpApi.builtinStatus()
  } catch (e) {}
}

onMounted(() => {
  checkFtpStatus()
  setInterval(checkFtpStatus, 10000)
})
</script>

<style scoped>
/* ===== 布局根容器 ===== */
.layout-root {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-page);
}

/* ===== 侧边栏 ===== */
.sidebar {
  width: 220px;
  height: 100vh;
  background: #0d1117;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 100;
  box-shadow: 2px 0 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.sidebar.collapsed {
  width: 64px;
}

/* Logo */
.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  cursor: pointer;
  flex-shrink: 0;
  overflow: hidden;
}

.logo-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.35);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.sidebar-logo:hover .logo-icon {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.45);
}

.logo-name {
  color: white;
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  letter-spacing: 0.3px;
}

/* 导航 */
.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  text-decoration: none;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  font-weight: 500;
  position: relative;
  transition: all 0.2s ease;
  white-space: nowrap;
  overflow: hidden;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.85);
}

.nav-item.active {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.nav-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.nav-item.active .nav-icon {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.nav-label {
  flex: 1;
  transition: opacity 0.2s ease;
}

.active-indicator {
  width: 3px;
  height: 18px;
  background: #3b82f6;
  border-radius: 2px;
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
}

/* 侧边栏底部 */
.sidebar-footer {
  padding: 12px 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
}

.collapse-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border: none;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.35);
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s ease;
  overflow: hidden;
  white-space: nowrap;
}

.collapse-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.65);
}

.collapse-label {
  font-size: 13px;
}

/* ===== 主内容区 ===== */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

/* Topbar */
.topbar {
  height: 60px;
  background: white;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
  box-shadow: var(--shadow-xs);
  z-index: 10;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.breadcrumb-area {
  display: flex;
  align-items: center;
  gap: 8px;
}

.breadcrumb-home {
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color 0.2s;
  font-size: 16px;
}

.breadcrumb-home:hover { color: var(--primary-500); }

.breadcrumb-sep {
  color: var(--neutral-300);
  font-size: 12px;
}

.breadcrumb-current {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

/* Topbar 右侧 */
.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.divider {
  width: 1px;
  height: 20px;
  background: var(--border-medium);
}

/* FTP 状态徽章 */
.ftp-badge {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.ftp-badge.online {
  background: rgba(16, 185, 129, 0.08);
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.ftp-badge.offline {
  background: rgba(239, 68, 68, 0.08);
  color: #dc2626;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.online .badge-dot {
  background: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.25);
  animation: pulse 2s infinite;
}

.offline .badge-dot {
  background: #ef4444;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.25); }
  50% { box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.1); }
}

/* 用户 Chip */
.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px 5px 6px;
  border-radius: 24px;
  border: 1px solid var(--border-light);
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.user-chip:hover {
  border-color: var(--primary-300);
  background: var(--primary-50);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: white;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.user-arrow {
  color: var(--text-tertiary);
}

/* 用户下拉菜单 */
.user-menu :deep(.el-dropdown-menu__item) {
  font-size: 13px !important;
}

.menu-user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 0;
}

.menu-user-info strong {
  font-size: 13px;
  color: var(--text-primary);
}

.menu-user-info small {
  font-size: 11px;
  color: var(--text-tertiary);
}

.logout-item {
  color: var(--danger) !important;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 内容区 */
.page-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px;
  background: var(--bg-page);
}

/* 页面切换动画 */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Logo 文字动画 */
.logo-text-fade-enter-active,
.logo-text-fade-leave-active {
  transition: opacity 0.15s ease, width 0.3s ease;
}
.logo-text-fade-enter-from,
.logo-text-fade-leave-to {
  opacity: 0;
  width: 0;
}

/* nav 文字动画 */
.nav-text-fade-enter-active,
.nav-text-fade-leave-active {
  transition: opacity 0.15s ease;
}
.nav-text-fade-enter-from,
.nav-text-fade-leave-to {
  opacity: 0;
}
</style>
