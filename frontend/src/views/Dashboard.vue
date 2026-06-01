<template>
  <div class="dashboard-page">
    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div class="stat-card animate-fadeInUp delay-1" style="--card-color: #3b82f6; --card-shadow: rgba(59,130,246,0.25)">
        <div class="stat-card-bg"></div>
        <div class="stat-content">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Connection /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-num">{{ stats.servers || 0 }}</div>
            <div class="stat-label">FTP 服务器</div>
          </div>
        </div>
        <div class="stat-footer">
          <span @click="$router.push('/servers')" class="stat-link">管理服务器 →</span>
        </div>
      </div>

      <div class="stat-card animate-fadeInUp delay-2" style="--card-color: #8b5cf6; --card-shadow: rgba(139,92,246,0.25)">
        <div class="stat-card-bg"></div>
        <div class="stat-content">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><List /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-num">{{ stats.tasks || 0 }}</div>
            <div class="stat-label">同步任务</div>
          </div>
        </div>
        <div class="stat-footer">
          <span @click="$router.push('/tasks')" class="stat-link">管理任务 →</span>
        </div>
      </div>

      <div class="stat-card animate-fadeInUp delay-3" style="--card-color: #10b981; --card-shadow: rgba(16,185,129,0.25)">
        <div class="stat-card-bg"></div>
        <div class="stat-content">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><SuccessFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-num">{{ syncStats.success || 0 }}</div>
            <div class="stat-label">成功同步</div>
          </div>
        </div>
        <div class="stat-footer">
          <span class="stat-rate" v-if="syncStats.total > 0">
            成功率 {{ Math.round((syncStats.success / syncStats.total) * 100) }}%
          </span>
        </div>
      </div>

      <div class="stat-card animate-fadeInUp delay-4" style="--card-color: #ef4444; --card-shadow: rgba(239,68,68,0.25)">
        <div class="stat-card-bg"></div>
        <div class="stat-content">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><CircleCloseFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-num">{{ syncStats.failed || 0 }}</div>
            <div class="stat-label">失败同步</div>
          </div>
        </div>
        <div class="stat-footer">
          <span @click="$router.push('/history')" class="stat-link">查看历史 →</span>
        </div>
      </div>
    </div>

    <!-- 第二行：FTP状态 + 最近历史 -->
    <div class="content-grid">
      <!-- FTP服务器状态 -->
      <el-card class="ftp-card">
        <template #header>
          <div class="card-header-flex">
            <div class="header-title">
              <div class="header-dot" :class="ftpStatus.is_running ? 'online' : 'offline'"></div>
              <span>内置 FTP 服务器</span>
            </div>
            <div class="header-actions">
              <el-button
                :type="ftpStatus.is_running ? 'danger' : 'primary'"
                size="small"
                @click="toggleFtp"
              >
                {{ ftpStatus.is_running ? '停止' : '启动' }}
              </el-button>
              <el-button plain size="small" @click="restartFtp">
                <el-icon><RefreshRight /></el-icon>
                重启
              </el-button>
            </div>
          </div>
        </template>

        <div class="ftp-info-grid">
          <div class="info-item">
            <div class="info-label">运行状态</div>
            <div class="info-value">
              <el-tag :type="ftpStatus.is_running ? 'success' : 'danger'" size="small">
                {{ ftpStatus.is_running ? '✓ 运行中' : '✗ 已停止' }}
              </el-tag>
            </div>
          </div>
          <div class="info-item">
            <div class="info-label">服务器地址</div>
            <div class="info-value mono">127.0.0.1:2121</div>
          </div>
          <div class="info-item">
            <div class="info-label">FTP 根目录</div>
            <div class="info-value mono truncate">{{ ftpStatus.ftp_root || '未配置' }}</div>
          </div>
          <div class="info-item">
            <div class="info-label">默认账号</div>
            <div class="info-value mono">admin / admin123</div>
          </div>
        </div>
      </el-card>

      <!-- 最近同步历史 -->
      <el-card class="history-card">
        <template #header>
          <div class="card-header-flex">
            <span>最近同步动态</span>
            <el-button text size="small" @click="$router.push('/history')" type="primary">
              查看全部
            </el-button>
          </div>
        </template>

        <div v-if="recentHistory.length === 0" class="empty-state">
          <el-icon :size="40" color="#d1d5db"><Clock /></el-icon>
          <p>暂无同步记录</p>
        </div>

        <div v-else class="history-list">
          <div v-for="item in recentHistory" :key="item.id" class="history-item">
            <div class="history-icon" :class="item.status">
              <el-icon :size="14">
                <component :is="item.direction === 'local_to_remote' ? 'Top' : 'Bottom'" />
              </el-icon>
            </div>
            <div class="history-body">
              <div class="history-file">{{ item.file_name }}</div>
              <div class="history-meta">
                <span :class="item.direction === 'local_to_remote' ? 'tag-upload' : 'tag-download'">
                  {{ item.direction === 'local_to_remote' ? '↑ 上传' : '↓ 下载' }}
                </span>
                <span class="history-action">{{ getActionName(item.action) }}</span>
              </div>
            </div>
            <div class="history-status">
              <span :class="item.status === 'success' ? 'dot-success' : 'dot-error'"></span>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 第三行：监控状态 -->
    <el-card class="watcher-card">
      <template #header>
        <div class="card-header-flex">
          <div class="header-title">
            <el-icon color="#3b82f6"><View /></el-icon>
            <span>文件监控状态</span>
          </div>
          <el-button @click="refreshStatus" size="small" plain>
            <el-icon><Refresh /></el-icon>
            刷新状态
          </el-button>
        </div>
      </template>

      <div v-if="watcherList.length === 0" class="empty-state-sm">
        <el-empty description="暂无监控任务，请先创建同步任务" :image-size="80" />
      </div>
      <div v-else class="watcher-grid">
        <div v-for="w in watcherList" :key="w.task_id" class="watcher-item" :class="{ active: w.is_alive }">
          <div class="watcher-dot" :class="w.is_alive ? 'alive' : 'dead'"></div>
          <div class="watcher-info">
            <div class="watcher-id">任务 #{{ w.task_id }}</div>
            <div class="watcher-path">{{ w.path }}</div>
          </div>
          <el-tag :type="w.is_alive ? 'success' : 'info'" size="small">
            {{ w.is_alive ? '监控中' : '已停止' }}
          </el-tag>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ftpApi, syncApi, historyApi } from '../api'

const ftpStatus = ref({ is_running: false })
const stats = ref({ servers: 0, tasks: 0 })
const syncStats = ref({ success: 0, failed: 0, total: 0 })
const recentHistory = ref([])
const watcherList = ref([])

const getActionName = (action) => {
  const names = {
    upload_new: '新增上传', upload_update: '更新上传',
    download_new: '新增下载', download_update: '更新下载',
    delete_remote: '远端删除', delete_local: '本地删除'
  }
  return names[action] || action
}

const toggleFtp = async () => {
  try {
    if (ftpStatus.value.is_running) {
      await ftpApi.builtinStop(); ElMessage.success('FTP服务器已停止')
    } else {
      await ftpApi.builtinStart(); ElMessage.success('FTP服务器已启动')
    }
    await loadFtpStatus()
  } catch (e) { ElMessage.error('操作失败') }
}

const restartFtp = async () => {
  try {
    await ftpApi.builtinRestart(); ElMessage.success('FTP服务器已重启')
    await loadFtpStatus()
  } catch (e) { ElMessage.error('重启失败') }
}

const loadFtpStatus = async () => {
  try { ftpStatus.value = await ftpApi.builtinStatus() } catch (e) {}
}

const loadStats = async () => {
  try {
    const [servers, tasks, historyStats] = await Promise.all([
      ftpApi.list(), syncApi.list(), historyApi.getStats()
    ])
    stats.value.servers = servers.servers?.length || 0
    stats.value.tasks = tasks.tasks?.length || 0
    syncStats.value = { ...historyStats, total: (historyStats.success || 0) + (historyStats.failed || 0) }
  } catch (e) {}
}

const loadRecentHistory = async () => {
  try {
    const res = await historyApi.getAllHistory(1)
    recentHistory.value = (res.history || []).slice(0, 6)
  } catch (e) {}
}

const loadWatcherStatus = async () => {
  try {
    const res = await syncApi.watcherStatus()
    watcherList.value = Object.entries(res).map(([id, info]) => ({ task_id: id, ...info }))
  } catch (e) {}
}

const refreshStatus = () => {
  loadFtpStatus(); loadWatcherStatus()
  ElMessage({ message: '已刷新状态', type: 'success', duration: 1500 })
}

onMounted(() => {
  loadFtpStatus(); loadStats(); loadRecentHistory(); loadWatcherStatus()
})
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* === 统计卡片网格 === */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
  transition: all 0.3s ease;
  cursor: default;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px var(--card-shadow);
  border-color: var(--card-color);
}

.stat-card-bg {
  position: absolute;
  top: -30px;
  right: -30px;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: var(--card-color);
  opacity: 0.06;
  transition: all 0.3s ease;
}

.stat-card:hover .stat-card-bg {
  opacity: 0.1;
  transform: scale(1.3);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.stat-icon-wrap {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: var(--card-color);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
  box-shadow: 0 4px 12px var(--card-shadow);
}

.stat-num {
  font-size: 32px;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1;
  letter-spacing: -1px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-tertiary);
  margin-top: 4px;
  font-weight: 500;
}

.stat-footer {
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.stat-link {
  font-size: 12px;
  color: var(--card-color);
  cursor: pointer;
  font-weight: 500;
  transition: opacity 0.2s;
}

.stat-link:hover { opacity: 0.7; }

.stat-rate {
  font-size: 12px;
  color: var(--text-tertiary);
  font-weight: 500;
}

/* === 内容网格 === */
.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* FTP 卡片 */
.card-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.header-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.header-dot.online {
  background: var(--success);
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
  animation: pulse 2s infinite;
}

.header-dot.offline { background: var(--danger); }

.header-actions {
  display: flex;
  gap: 8px;
}

.ftp-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.info-item {}

.info-label {
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.info-value {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.info-value.mono {
  font-family: var(--font-mono);
  font-size: 12px;
  background: var(--neutral-50);
  padding: 4px 8px;
  border-radius: 6px;
  display: inline-block;
}

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

/* 历史列表 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 32px 0;
  color: var(--text-tertiary);
  font-size: 13px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 8px;
  border-radius: 8px;
  transition: background 0.15s;
}

.history-item:hover { background: var(--neutral-50); }

.history-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.history-icon.success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.history-icon.error, .history-icon.failed {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.history-body { flex: 1; min-width: 0; }

.history-file {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 3px;
}

.tag-upload {
  font-size: 11px;
  color: #2563eb;
  background: rgba(59, 130, 246, 0.08);
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.tag-download {
  font-size: 11px;
  color: #059669;
  background: rgba(16, 185, 129, 0.08);
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.history-action {
  font-size: 11px;
  color: var(--text-tertiary);
}

.history-status { flex-shrink: 0; }

.dot-success {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--success);
}

.dot-error {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--danger);
}

/* Watcher 状态 */
.empty-state-sm {
  padding: 8px 0;
}

.watcher-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.watcher-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 10px;
  background: var(--neutral-50);
  border: 1px solid var(--border-light);
  transition: all 0.2s;
}

.watcher-item.active {
  background: rgba(59, 130, 246, 0.04);
  border-color: rgba(59, 130, 246, 0.15);
}

.watcher-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.watcher-dot.alive {
  background: var(--success);
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
  animation: pulse 2s infinite;
}

.watcher-dot.dead { background: var(--neutral-300); }

.watcher-info { flex: 1; min-width: 0; }

.watcher-id {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.watcher-path {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
}

/* 动画 */
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2); }
  50% { box-shadow: 0 0 0 5px rgba(16, 185, 129, 0.08); }
}

/* 响应式 */
@media (max-width: 1200px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .stat-grid { grid-template-columns: 1fr; }
  .content-grid { grid-template-columns: 1fr; }
}
</style>
