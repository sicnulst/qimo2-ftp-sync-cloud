<template>
  <div class="files-page">
    <!-- 任务选择器 -->
    <el-card class="selector-card">
      <div class="selector-row">
        <div class="selector-left">
          <el-icon color="#3b82f6" :size="16"><FolderOpened /></el-icon>
          <el-select
            v-model="selectedTask"
            placeholder="选择同步任务查看文件"
            style="width: 280px"
            @change="onTaskChange"
          >
            <el-option
              v-for="t in tasks"
              :key="t.id"
              :label="`${t.server_name || 'FTP'} · ${t.sync_strategy === 'newest' ? '最新' : t.sync_strategy === 'size' ? '大小' : t.sync_strategy === 'force_local' ? '本地' : '服务器'}优先`"
              :value="t.id"
            />
          </el-select>
        </div>

        <div class="selector-actions">
          <el-button
            type="primary"
            :loading="diffLoading"
            :disabled="!selectedTask"
            @click="runDiff"
          >
            <el-icon><DocumentChecked /></el-icon>
            差异对比
          </el-button>
          <el-button :disabled="!selectedTask" @click="refreshFiles">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>

          <!-- 差异摘要 -->
          <div v-if="diffSummary" class="diff-summary">
            <el-tooltip content="文件一致" placement="top">
              <span class="diff-badge same">✓ {{ diffSummary.same }}</span>
            </el-tooltip>
            <el-tooltip content="内容不一致" placement="top">
              <span class="diff-badge diff">≠ {{ diffSummary.different }}</span>
            </el-tooltip>
            <el-tooltip content="仅本地有" placement="top">
              <span class="diff-badge local">↑ {{ diffSummary.local_only }}</span>
            </el-tooltip>
            <el-tooltip content="仅远端有" placement="top">
              <span class="diff-badge remote">↓ {{ diffSummary.remote_only }}</span>
            </el-tooltip>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 差异对比结果 -->
    <el-card v-if="diffResults.length > 0" class="diff-card">
      <template #header>
        <div class="card-header-flex">
          <div class="header-title">
            <el-icon color="#3b82f6"><DocumentChecked /></el-icon>
            <span>文件同步状态对比</span>
          </div>
          <el-button text size="small" @click="diffResults = []; diffSummary = null">
            <el-icon><Close /></el-icon>
            关闭
          </el-button>
        </div>
      </template>
      <el-table :data="diffResults" style="width: 100%" max-height="280" stripe class="enhanced-table">
        <el-table-column label="文件名" prop="name" min-width="200">
          <template #default="{ row }">
            <div class="file-name-cell">
              <el-icon :size="14" color="#9ca3af"><Document /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="本地大小" min-width="100" align="right">
          <template #default="{ row }">
            <span class="size-mono">{{ row.local_size != null ? formatSize(row.local_size) : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="云端大小" min-width="100" align="right">
          <template #default="{ row }">
            <span class="size-mono">{{ row.remote_size != null ? formatSize(row.remote_size) : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="light" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 双栏文件浏览 -->
    <div class="file-panels-grid">
      <!-- 本地文件 -->
      <el-card class="file-panel">
        <template #header>
          <div class="panel-header">
            <div class="panel-title">
              <div class="panel-icon local">
                <el-icon :size="14"><FolderOpened /></el-icon>
              </div>
              <div>
                <div class="panel-name">本地文件夹</div>
                <div class="panel-path" v-if="currentTaskInfo">{{ currentTaskInfo.local_path }}</div>
              </div>
            </div>
            <div class="panel-actions" v-if="currentTaskInfo">
              <el-upload :show-file-list="false" :before-upload="() => false" @change="handleLocalUpload" accept="*">
                <el-button type="primary" size="small">
                  <el-icon><Upload /></el-icon>
                  上传
                </el-button>
              </el-upload>
              <el-button type="success" size="small" @click="showLocalMkdir">
                <el-icon><FolderAdd /></el-icon>
                新建
              </el-button>
            </div>
          </div>
        </template>

        <!-- 路径导航 -->
        <div class="path-breadcrumb" v-if="localPathParts.length > 0 || true">
          <span class="path-root" @click="loadLocalFiles('/')">
            <el-icon><House /></el-icon>
          </span>
          <template v-if="localPathParts.length > 0">
            <el-icon :size="12" class="path-sep"><ArrowRight /></el-icon>
            <span
              v-for="(part, i) in localPathParts"
              :key="i"
              class="path-part"
              @click="navigateLocal(i)"
            >{{ part }}</span>
          </template>
        </div>

        <el-table
          :data="localFiles"
          v-loading="localLoading"
          max-height="420"
          style="width: 100%"
          stripe
        >
          <el-table-column label="名称" min-width="180">
            <template #default="{ row }">
              <div
                class="file-row"
                :class="[{ clickable: row.is_dir }, diffStatusClass(row.name)]"
                @click="row.is_dir && loadLocalFiles(row.path)"
              >
                <el-icon :size="16" :class="row.is_dir ? 'icon-folder' : 'icon-file'">
                  <component :is="row.is_dir ? 'Folder' : 'Document'" />
                </el-icon>
                <span class="row-name">{{ row.name }}</span>
                <el-icon v-if="row.is_dir" :size="12" class="arrow-icon"><ArrowRight /></el-icon>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="大小" width="90" align="right">
            <template #default="{ row }">
              <span class="size-mono">{{ row.is_dir ? '—' : formatSize(row.size) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="" width="60" align="center">
            <template #default="{ row }">
              <el-button type="danger" link size="small" @click.stop="deleteLocal(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="localFiles.length === 0 && !localLoading" class="panel-empty">
          <el-icon :size="36" color="#d1d5db"><FolderOpened /></el-icon>
          <span>文件夹为空</span>
        </div>
      </el-card>

      <!-- 服务器文件 -->
      <el-card class="file-panel">
        <template #header>
          <div class="panel-header">
            <div class="panel-title">
              <div class="panel-icon remote">
                <el-icon :size="14"><Connection /></el-icon>
              </div>
              <div>
                <div class="panel-name">云端文件夹</div>
                <div class="panel-path" v-if="currentTaskInfo">{{ currentTaskInfo.server_name || 'FTP 服务器' }}</div>
              </div>
            </div>
            <div class="panel-actions" v-if="currentTaskInfo">
              <el-upload :show-file-list="false" :before-upload="() => false" @change="handleRemoteUpload" accept="*">
                <el-button type="primary" size="small">
                  <el-icon><Upload /></el-icon>
                  上传
                </el-button>
              </el-upload>
              <el-button type="success" size="small" @click="showRemoteMkdir">
                <el-icon><FolderAdd /></el-icon>
                新建
              </el-button>
            </div>
          </div>
        </template>

        <div class="path-breadcrumb">
          <span class="path-root" @click="loadRemoteFilesFromTask()">
            <el-icon><House /></el-icon>
          </span>
          <template v-if="remotePathParts.length > 0">
            <el-icon :size="12" class="path-sep"><ArrowRight /></el-icon>
            <span
              v-for="(part, i) in remotePathParts"
              :key="i"
              class="path-part"
              @click="navigateRemote(i)"
            >{{ part }}</span>
          </template>
        </div>

        <el-table
          :data="remoteFiles"
          v-loading="remoteLoading"
          max-height="420"
          style="width: 100%"
          stripe
        >
          <el-table-column label="名称" min-width="160">
            <template #default="{ row }">
              <div
                class="file-row"
                :class="[{ clickable: row.is_dir }, diffStatusClass(row.name)]"
                @click="row.is_dir && navigateRemoteInto(row.path)"
              >
                <el-icon :size="16" :class="row.is_dir ? 'icon-folder' : 'icon-file'">
                  <component :is="row.is_dir ? 'Folder' : 'Document'" />
                </el-icon>
                <span class="row-name">{{ row.name }}</span>
                <el-icon v-if="row.is_dir" :size="12" class="arrow-icon"><ArrowRight /></el-icon>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="大小" width="90" align="right">
            <template #default="{ row }">
              <span class="size-mono">{{ row.is_dir ? '—' : formatSize(row.size) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="" width="90" align="center">
            <template #default="{ row }">
              <el-button v-if="!row.is_dir" type="primary" link size="small" @click.stop="downloadRemote(row)">
                <el-icon><Download /></el-icon>
              </el-button>
              <el-button type="danger" link size="small" @click.stop="deleteRemote(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="remoteFiles.length === 0 && !remoteLoading" class="panel-empty">
          <el-icon :size="36" color="#d1d5db"><Connection /></el-icon>
          <span>文件夹为空</span>
        </div>
      </el-card>
    </div>

    <!-- 新建文件夹 -->
    <el-dialog v-model="mkdirVisible" title="新建文件夹" width="380px" align-center>
      <el-input
        v-model="newFolderName"
        placeholder="请输入文件夹名称"
        @keyup.enter="confirmMkdir"
        autofocus
        size="large"
      />
      <template #footer>
        <el-button @click="mkdirVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmMkdir">创建</el-button>
      </template>
    </el-dialog>

    <!-- 未选任务提示 -->
    <div v-if="!selectedTask && tasks.length > 0" class="no-task-hint">
      <el-icon :size="48" color="#d1d5db"><FolderOpened /></el-icon>
      <h3>请选择一个同步任务</h3>
      <p>选择左上角的任务以查看本地和云端文件</p>
    </div>

    <div v-if="tasks.length === 0" class="no-task-hint">
      <el-icon :size="48" color="#d1d5db"><FolderOpened /></el-icon>
      <h3>暂无同步任务</h3>
      <p>请先创建同步任务，然后再浏览文件</p>
      <el-button type="primary" @click="$router.push('/tasks')">去创建任务</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { syncApi, filesApi } from '../api'
import api from '../api'
import { Folder, FolderOpened, FolderAdd, Document, DocumentChecked, Refresh, Download, Upload, House, ArrowRight, Delete, Close, Connection } from '@element-plus/icons-vue'

const route = useRoute()
const tasks = ref([])
const selectedTask = ref(null)
const currentTaskInfo = ref(null)
const localFiles = ref([])
const remoteFiles = ref([])
const localLoading = ref(false)
const remoteLoading = ref(false)
const localCurrentPath = ref('/')
const remoteCurrentPath = ref('/')
const diffResults = ref([])
const diffSummary = ref(null)
const diffLoading = ref(false)
const diffMap = ref({})
const mkdirVisible = ref(false)
const newFolderName = ref('')
const mkdirTarget = ref('local')

let refreshTimer = null

const localPathParts = computed(() => localCurrentPath.value.split('/').filter(Boolean))
const remotePathParts = computed(() => remoteCurrentPath.value.split('/').filter(Boolean))

const formatSize = (bytes) => {
  if (bytes == null || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++ }
  return `${bytes.toFixed(1)} ${units[i]}`
}

const statusTagType = (s) => ({ same: 'success', different: 'danger', local_only: 'warning', remote_only: 'info' }[s] || '')
const statusLabel = (s) => ({ same: '已同步', different: '不一致', local_only: '仅本地', remote_only: '仅远端' }[s] || s)
const diffStatusClass = (name) => {
  const s = diffMap.value[name]
  return (!s || s === 'same') ? '' : `diff-${s}`
}

const loadLocalFiles = async (subpath = '/') => {
  if (!currentTaskInfo.value) return
  localLoading.value = true
  localCurrentPath.value = subpath
  try {
    const data = await api.get('/files/local', { params: { path: currentTaskInfo.value.local_path, subpath } })
    localFiles.value = data.files || []
  } catch (e) { localFiles.value = [] } finally { localLoading.value = false }
}

const loadRemoteFilesFromTask = async (subpath = '/') => {
  if (!currentTaskInfo.value) return
  const task = currentTaskInfo.value
  const base = task.remote_path || '/'
  const fullRemote = subpath === '/' ? base : `${base.replace(/\/$/, '')}/${subpath.replace(/^\//, '')}`
  remoteLoading.value = true
  remoteCurrentPath.value = subpath
  try {
    const res = await api.get(`/ftp/servers/${task.ftp_server_id}/files?path=${encodeURIComponent(fullRemote)}`)
    remoteFiles.value = (res.files || []).filter(f => f.name !== '.' && f.name !== '..')
  } catch (e) { remoteFiles.value = [] } finally { remoteLoading.value = false }
}

const refreshFiles = () => {
  if (!currentTaskInfo.value) return
  loadLocalFiles(localCurrentPath.value)
  loadRemoteFilesFromTask(remoteCurrentPath.value)
  ElMessage({ message: '已刷新', type: 'success', duration: 1500 })
}

const startAutoRefresh = () => {
  stopAutoRefresh()
  refreshTimer = setInterval(() => {
    if (currentTaskInfo.value && !localLoading.value && !remoteLoading.value) {
      loadLocalFiles(localCurrentPath.value)
      loadRemoteFilesFromTask(remoteCurrentPath.value)
    }
  }, 15000)
}
const stopAutoRefresh = () => { if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null } }

const navigateRemoteInto = (path) => { remoteCurrentPath.value = path; loadRemoteFilesFromTask(path) }
const navigateLocal = (index) => { loadLocalFiles('/' + localPathParts.value.slice(0, index + 1).join('/')) }
const navigateRemote = (index) => { loadRemoteFilesFromTask('/' + remotePathParts.value.slice(0, index + 1).join('/')) }

const onTaskChange = () => {
  const task = tasks.value.find(t => t.id === selectedTask.value)
  currentTaskInfo.value = task || null
  diffResults.value = []; diffSummary.value = null; diffMap.value = {}
  localCurrentPath.value = '/'; remoteCurrentPath.value = '/'
  if (task) { loadLocalFiles('/'); loadRemoteFilesFromTask('/'); startAutoRefresh() }
  else { stopAutoRefresh() }
}

const runDiff = async () => {
  const task = currentTaskInfo.value; if (!task) return
  diffLoading.value = true
  try {
    const res = await api.post('/files/diff', {
      local_path: task.local_path, ftp_host: task.host, ftp_port: task.port,
      ftp_username: task.username, ftp_password: task.password, remote_path: task.remote_path || '/'
    })
    diffResults.value = res.files || []; diffSummary.value = res.summary || null
    const map = {}; for (const f of diffResults.value) map[f.name] = f.status
    diffMap.value = map
    const s = res.summary
    if (s) {
      if (s.different === 0 && s.local_only === 0 && s.remote_only === 0)
        ElMessage({ message: `全部 ${s.same} 个文件已同步一致 ✓`, type: 'success' })
      else
        ElMessage({ message: `发现 ${s.different} 个不一致、${s.local_only} 个仅本地、${s.remote_only} 个仅远端`, type: 'warning' })
    }
  } catch (e) { ElMessage.error('差异对比失败') } finally { diffLoading.value = false }
}

const downloadRemote = async (fileRow) => {
  const task = currentTaskInfo.value; if (!task || fileRow.is_dir) return
  try {
    const blob = await filesApi.downloadRemote(task.host, task.port, task.username, task.password, fileRow.path)
    const url = window.URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a'); link.href = url; link.setAttribute('download', fileRow.name)
    document.body.appendChild(link); link.click(); link.remove(); window.URL.revokeObjectURL(url)
    ElMessage.success(`已拉取：${fileRow.name}`)
  } catch (e) { ElMessage.error('拉取失败') }
}

const handleLocalUpload = async (uploadFile) => {
  const task = currentTaskInfo.value; if (!task) return
  const formData = new FormData()
  formData.append('file', uploadFile.raw); formData.append('path', task.local_path); formData.append('subpath', localCurrentPath.value)
  try { await filesApi.localUpload(formData); ElMessage.success('上传成功'); loadLocalFiles(localCurrentPath.value) }
  catch (e) { ElMessage.error(e?.error || '上传失败') }
}

const handleRemoteUpload = async (uploadFile) => {
  const task = currentTaskInfo.value; if (!task) return
  const base = task.remote_path || '/'
  const fullRemote = remoteCurrentPath.value === '/' ? base : `${base.replace(/\/$/, '')}/${remoteCurrentPath.value.replace(/^\//, '')}`
  const formData = new FormData()
  formData.append('file', uploadFile.raw); formData.append('ftp_host', task.host); formData.append('ftp_port', task.port)
  formData.append('ftp_username', task.username); formData.append('ftp_password', task.password); formData.append('remote_path', fullRemote)
  try { await filesApi.remoteUpload(formData); ElMessage.success('上传成功'); loadRemoteFilesFromTask(remoteCurrentPath.value) }
  catch (e) { ElMessage.error(e?.error || '上传失败') }
}

const showLocalMkdir = () => { mkdirTarget.value = 'local'; newFolderName.value = ''; mkdirVisible.value = true }
const showRemoteMkdir = () => { mkdirTarget.value = 'remote'; newFolderName.value = ''; mkdirVisible.value = true }
const confirmMkdir = async () => {
  if (!newFolderName.value.trim()) { ElMessage.warning('请输入文件夹名称'); return }
  const task = currentTaskInfo.value; if (!task) return
  try {
    if (mkdirTarget.value === 'local') {
      await filesApi.localMkdir(task.local_path, localCurrentPath.value, newFolderName.value.trim())
      ElMessage.success('本地文件夹创建成功'); loadLocalFiles(localCurrentPath.value)
    } else {
      const base = task.remote_path || '/'
      const fullRemote = remoteCurrentPath.value === '/' ? base : `${base.replace(/\/$/, '')}/${remoteCurrentPath.value.replace(/^\//, '')}`
      await filesApi.remoteMkdir(task.host, task.port, task.username, task.password, fullRemote, newFolderName.value.trim())
      ElMessage.success('云端文件夹创建成功'); loadRemoteFilesFromTask(remoteCurrentPath.value)
    }
    mkdirVisible.value = false
  } catch (e) { ElMessage.error(e?.error || '创建失败') }
}

const deleteLocal = async (fileRow) => {
  const task = currentTaskInfo.value; if (!task) return
  try {
    await ElMessageBox.confirm(`确定删除「${fileRow.name}」？`, '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' })
    const filePath = localCurrentPath.value === '/' ? fileRow.name : `${localCurrentPath.value}/${fileRow.name}`
    await filesApi.localDelete(task.local_path, filePath)
    ElMessage.success('删除成功'); loadLocalFiles(localCurrentPath.value)
  } catch (e) { if (e !== 'cancel') ElMessage.error(e?.error || '删除失败') }
}

const deleteRemote = async (fileRow) => {
  const task = currentTaskInfo.value; if (!task) return
  try {
    await ElMessageBox.confirm(`确定删除远端「${fileRow.name}」？`, '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' })
    await filesApi.remoteDelete(task.host, task.port, task.username, task.password, fileRow.path, fileRow.is_dir)
    ElMessage.success('删除成功'); loadRemoteFilesFromTask(remoteCurrentPath.value)
  } catch (e) { if (e !== 'cancel') ElMessage.error(e?.error || '删除失败') }
}

onMounted(async () => {
  try {
    const tasksRes = await syncApi.list()
    tasks.value = tasksRes.tasks || []
    const taskId = route.query.task_id
    if (taskId) { selectedTask.value = parseInt(taskId); onTaskChange() }
  } catch (e) {}
})

onUnmounted(() => { stopAutoRefresh() })
</script>

<style scoped>
.files-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
}

/* 选择器卡片 */
.selector-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.selector-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.selector-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

/* 差异摘要 */
.diff-summary {
  display: flex;
  gap: 6px;
  align-items: center;
}

.diff-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  cursor: default;
}

.diff-badge.same { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.diff-badge.diff { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
.diff-badge.local { background: rgba(245, 158, 11, 0.1); color: #d97706; }
.diff-badge.remote { background: rgba(107, 114, 128, 0.1); color: #6b7280; }

/* 差异卡片标题 */
.card-header-flex { display: flex; justify-content: space-between; align-items: center; }
.header-title { display: flex; align-items: center; gap: 8px; font-weight: 600; }

/* 双栏面板 */
.file-panels-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* 文件面板 */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.panel-icon.local {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.panel-icon.remote {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.panel-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-path {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
}

.panel-actions {
  display: flex;
  gap: 6px;
}

/* 路径面包屑 */
.path-breadcrumb {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: var(--neutral-50);
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 12px;
  flex-wrap: wrap;
}

.path-root {
  display: flex;
  align-items: center;
  color: var(--primary-500);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background 0.15s;
}

.path-root:hover { background: rgba(59, 130, 246, 0.1); }

.path-sep { color: var(--neutral-300); }

.path-part {
  color: var(--text-secondary);
  cursor: pointer;
  padding: 1px 5px;
  border-radius: 4px;
  transition: all 0.15s;
  font-weight: 500;
}

.path-part:hover { background: rgba(59, 130, 246, 0.1); color: var(--primary-500); }
.path-part:last-child { color: var(--text-primary); }

/* 文件行 */
.file-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0;
  border-radius: 6px;
  transition: all 0.15s;
}

.file-row.clickable { cursor: pointer; }
.file-row.clickable:hover { color: var(--primary-500); }

.icon-folder { color: #f59e0b; }
.icon-file { color: #9ca3af; }

.row-name {
  flex: 1;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrow-icon { color: var(--neutral-300); margin-left: auto; }

/* diff 颜色 */
.diff-different { color: #ef4444 !important; }
.diff-local_only { color: #f59e0b !important; }
.diff-remote_only { color: #9ca3af !important; }

/* 尺寸字体 */
.size-mono { font-family: var(--font-mono); font-size: 12px; color: var(--text-tertiary); }

/* 空状态 */
.panel-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px 0;
  color: var(--text-tertiary);
  font-size: 13px;
}

/* 全局空状态 */
.no-task-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 20px;
  background: white;
  border-radius: 14px;
  border: 1px solid var(--border-light);
}

.no-task-hint h3 { font-size: 18px; font-weight: 600; color: var(--text-primary); }
.no-task-hint p { font-size: 14px; color: var(--text-tertiary); }

/* 文件表格大小 */
.file-name-cell { display: flex; align-items: center; gap: 7px; }

/* 防止表头换行 */
.enhanced-table :deep(.el-table__header-wrapper th .cell) {
  white-space: nowrap;
}

/* 响应式 */
@media (max-width: 900px) {
  .file-panels-grid { grid-template-columns: 1fr; }
}
</style>
