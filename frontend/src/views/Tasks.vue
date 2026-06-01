<template>
  <div class="tasks-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <div class="header-left">
            <div class="page-title">
              <el-icon class="title-icon"><List /></el-icon>
              <span>同步任务</span>
              <el-tag type="info" size="small" class="count-tag">{{ tasks.length }}</el-tag>
            </div>
            <transition name="fade">
              <el-button v-if="selectedTasks.length > 0" type="danger" size="small" @click="batchDelete">
                <el-icon><Delete /></el-icon>
                删除选中 ({{ selectedTasks.length }})
              </el-button>
            </transition>
          </div>
          <el-button type="primary" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            创建任务
          </el-button>
        </div>
      </template>

      <!-- 空状态 -->
      <div v-if="tasks.length === 0 && !loading" class="empty-page">
        <div class="empty-illustration">
          <el-icon :size="56" color="#d1d5db"><FolderOpened /></el-icon>
        </div>
        <h3>暂无同步任务</h3>
        <p>创建一个同步任务，开始自动同步文件</p>
        <el-button type="primary" @click="showAddDialog">
          <el-icon><Plus /></el-icon>
          创建第一个任务
        </el-button>
      </div>

      <el-table
        v-else
        :data="tasks"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        style="width: 100%"
        fit
        stripe
        class="enhanced-table"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column label="FTP 服务器" min-width="120" prop="server_name">
          <template #default="{ row }">
            <div class="cell-with-icon">
              <el-icon color="#3b82f6" :size="14"><Connection /></el-icon>
              <span>{{ row.server_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="本地路径" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <code class="path-code">{{ row.local_path }}</code>
          </template>
        </el-table-column>
        <el-table-column label="本地" min-width="90" align="right">
          <template #default="{ row }">
            <span class="size-text">{{ row.local_size_formatted || '0 B' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="云端" min-width="100" align="right">
          <template #default="{ row }">
            <span class="size-text">{{ row.remote_size_formatted || '0 B' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="同步状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.sync_status)" size="small">
              <el-icon v-if="row.sync_status === 'syncing'" class="is-loading"><Loading /></el-icon>
              {{ getStatusName(row.sync_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="策略" width="80" align="center">
          <template #default="{ row }">
            <el-tooltip :content="getStrategyDesc(row.sync_strategy)" placement="top">
              <el-tag size="small" type="info">{{ getStrategyName(row.sync_strategy) }}</el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="监控" width="80" align="center">
          <template #default="{ row }">
            <div class="status-cell">
              <span class="status-dot" :class="row.is_watching ? 'active' : 'inactive'"></span>
              <span style="font-size: 12px; color: var(--text-tertiary)">{{ row.is_watching ? '监控中' : '空闲' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <div class="action-cell">
              <el-tooltip content="立即同步" placement="top">
                <el-button type="primary" link size="small" @click="manualSync(row)" :loading="row.syncing">
                  <el-icon><Refresh /></el-icon>
                  同步
                </el-button>
              </el-tooltip>
              <el-button :type="row.is_active ? 'warning' : 'success'" link size="small" @click="toggleTask(row)">
                <el-icon><component :is="row.is_active ? 'VideoPause' : 'VideoPlay'" /></el-icon>
                {{ row.is_active ? '暂停' : '启动' }}
              </el-button>
              <el-button type="info" link size="small" @click="showEditDialog(row)">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button type="info" link size="small" @click="showIgnoreDialog(row)">
                <el-icon><Filter /></el-icon>
                忽略
              </el-button>
              <el-button type="danger" link size="small" @click="deleteTask(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑任务对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑同步任务' : '创建同步任务'" width="520px" align-center>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px" label-position="left">
        <el-form-item label="FTP服务器" prop="ftp_server_id">
          <el-select v-model="form.ftp_server_id" placeholder="选择服务器" style="width: 100%" :disabled="isEditing">
            <el-option v-for="s in servers" :key="s.id" :label="`${s.name} (${s.host}:${s.port})`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="本地路径" prop="local_path">
          <el-input v-model="form.local_path" placeholder="如：D:\my_sync_folder" :disabled="isEditing" />
        </el-form-item>
        <el-form-item label="同步策略">
          <el-radio-group v-model="form.sync_strategy" class="strategy-group">
            <el-radio-button value="newest">最新优先</el-radio-button>
            <el-radio-button value="size">大小优先</el-radio-button>
            <el-radio-button value="force_local">强制本地</el-radio-button>
            <el-radio-button value="force_remote">强制服务器</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="扫描间隔">
          <div class="interval-input">
            <el-input-number v-model="form.scan_interval" :min="10" :max="3600" style="width: 140px" />
            <span class="input-unit">秒（建议 60-300）</span>
          </div>
        </el-form-item>
        <el-form-item label="自动启动">
          <el-switch v-model="form.auto_sync" active-text="创建后立即启动" />
        </el-form-item>
        <el-form-item label="删除同步">
          <el-switch v-model="form.delete_sync" />
          <span class="form-hint-text">开启后，删除文件时另一端也会同步删除</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          {{ isEditing ? '保存修改' : '创建任务' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 忽略规则对话框 -->
    <el-dialog v-model="ignoreDialogVisible" title="忽略规则管理" width="480px" align-center>
      <el-alert
        title="支持 glob 模式匹配，如：*.tmp、.git、node_modules、**/*.log"
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom: 16px"
      />
      <div class="ignore-add-row">
        <el-input
          v-model="newIgnorePattern"
          placeholder="输入匹配规则，如：*.svn"
          @keyup.enter="addIgnoreRule"
        />
        <el-button type="primary" @click="addIgnoreRule">添加</el-button>
      </div>
      <div class="ignore-list">
        <div v-for="rule in ignoreRules" :key="rule.id" class="ignore-rule-item">
          <el-icon color="#6b7280"><Hide /></el-icon>
          <code class="rule-code">{{ rule.pattern }}</code>
          <el-button type="danger" link size="small" @click="deleteIgnoreRule(rule)">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        <el-empty v-if="ignoreRules.length === 0" description="暂无忽略规则" :image-size="50" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { syncApi, ftpApi } from '../api'

const tasks = ref([])
const servers = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const ignoreDialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()
const currentTaskId = ref(null)
const ignoreRules = ref([])
const newIgnorePattern = ref('')
const isEditing = ref(false)
const editingTaskId = ref(null)
const selectedTasks = ref([])

const form = reactive({
  ftp_server_id: null, local_path: '', sync_strategy: 'newest',
  scan_interval: 60, auto_sync: true, delete_sync: false
})

const rules = {
  ftp_server_id: [{ required: true, message: '请选择FTP服务器', trigger: 'change' }],
  local_path: [{ required: true, message: '请输入本地路径', trigger: 'blur' }]
}

const getStatusName = (s) => ({ pending: '未同步', synced: '已同步', syncing: '同步中', stopped: '已停止' }[s] || s)
const getStatusType = (s) => ({ pending: 'warning', synced: 'success', syncing: 'primary', stopped: 'info' }[s] || 'info')
const getStrategyName = (s) => ({ newest: '最新', size: '大小', force_local: '本地', force_remote: '服务器' }[s] || s)
const getStrategyDesc = (s) => ({
  newest: '以最后修改时间为准',
  size: '以文件大小为准',
  force_local: '强制以本地文件为准',
  force_remote: '强制以服务器文件为准'
}[s] || s)

const handleSelectionChange = (val) => { selectedTasks.value = val }

const loadData = async () => {
  loading.value = true
  try {
    const [tasksRes, serversRes] = await Promise.all([syncApi.list(), ftpApi.list()])
    tasks.value = (tasksRes.tasks || []).map(t => ({ ...t, syncing: false }))
    servers.value = serversRes.servers || []
  } catch (e) { ElMessage.error('加载失败') } finally { loading.value = false }
}

const showAddDialog = () => {
  isEditing.value = false; editingTaskId.value = null
  Object.assign(form, { ftp_server_id: null, local_path: '', sync_strategy: 'newest', scan_interval: 60, auto_sync: true, delete_sync: false })
  dialogVisible.value = true
}

const showEditDialog = (task) => {
  isEditing.value = true; editingTaskId.value = task.id
  Object.assign(form, {
    ftp_server_id: task.ftp_server_id, local_path: task.local_path,
    sync_strategy: task.sync_strategy, scan_interval: task.scan_interval,
    auto_sync: !!task.is_active, delete_sync: !!task.delete_sync
  })
  dialogVisible.value = true
}

const submitForm = async () => {
  try {
    await formRef.value.validate()
    submitting.value = true
    if (isEditing.value) {
      await syncApi.update(editingTaskId.value, { sync_strategy: form.sync_strategy, scan_interval: form.scan_interval, delete_sync: form.delete_sync })
      ElMessage.success('任务更新成功')
    } else {
      await syncApi.add(form)
      ElMessage.success('任务创建成功')
    }
    dialogVisible.value = false; loadData()
  } catch (e) { if (e?.error) ElMessage.error(e.error) }
  finally { submitting.value = false }
}

const manualSync = async (task) => {
  task.syncing = true
  try {
    const res = await syncApi.manualSync(task.id)
    const synced = res.synced_count ?? 0; const errors = res.error_count ?? 0
    if (errors > 0) ElMessage.warning(`同步完成，成功 ${synced} 个，失败 ${errors} 个`)
    else ElMessage.success(synced === 0 ? '文件已是最新，无需同步' : `同步完成，处理 ${synced} 个文件`)
    loadData()
  } catch (e) { ElMessage.error('同步失败') } finally { task.syncing = false }
}

const toggleTask = async (task) => {
  try {
    if (task.is_active) { await syncApi.pause(task.id); ElMessage.success('任务已暂停') }
    else { await syncApi.start(task.id); ElMessage.success('任务已启动') }
    loadData()
  } catch (e) { ElMessage.error('操作失败') }
}

const deleteTask = async (task) => {
  try {
    await ElMessageBox.confirm(`确定删除任务 #${task.id}？`, '删除确认', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' })
    await syncApi.delete(task.id); ElMessage.success('删除成功'); loadData()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedTasks.value.length} 个任务？`, '批量删除', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' })
    for (const task of selectedTasks.value) { await syncApi.delete(task.id) }
    ElMessage.success(`已删除 ${selectedTasks.value.length} 个任务`)
    selectedTasks.value = []; loadData()
  } catch (e) { if (e !== 'cancel') ElMessage.error('批量删除失败') }
}

const showIgnoreDialog = async (task) => {
  currentTaskId.value = task.id; newIgnorePattern.value = ''
  try { const res = await syncApi.getIgnoreRules(task.id); ignoreRules.value = res.rules || [] }
  catch (e) { ignoreRules.value = [] }
  ignoreDialogVisible.value = true
}

const addIgnoreRule = async () => {
  if (!newIgnorePattern.value.trim()) { ElMessage.warning('请输入匹配规则'); return }
  try {
    await syncApi.addIgnoreRule(currentTaskId.value, { pattern: newIgnorePattern.value.trim() })
    ElMessage.success('添加成功')
    const res = await syncApi.getIgnoreRules(currentTaskId.value); ignoreRules.value = res.rules || []
    newIgnorePattern.value = ''
  } catch (e) { ElMessage.error('添加失败') }
}

const deleteIgnoreRule = async (rule) => {
  try {
    await syncApi.deleteIgnoreRule(currentTaskId.value, rule.id)
    ElMessage.success('删除成功'); ignoreRules.value = ignoreRules.value.filter(r => r.id !== rule.id)
  } catch (e) { ElMessage.error('删除失败') }
}

onMounted(loadData)
</script>

<style scoped>
.tasks-page { height: 100%; }

.page-header { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; gap: 12px; }
.page-title { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 15px; }
.title-icon { color: var(--primary-500); font-size: 18px; }
.count-tag { font-size: 12px !important; }

/* 空状态 */
.empty-page { display: flex; flex-direction: column; align-items: center; padding: 60px 20px; gap: 12px; }
.empty-illustration { width: 96px; height: 96px; border-radius: 24px; background: var(--neutral-100); display: flex; align-items: center; justify-content: center; margin-bottom: 8px; }
.empty-page h3 { font-size: 18px; font-weight: 600; color: var(--text-primary); }
.empty-page p { font-size: 14px; color: var(--text-tertiary); margin-bottom: 8px; }

/* 单元格 */
.cell-with-icon { display: flex; align-items: center; gap: 6px; font-size: 13.5px; }
.path-code { font-family: var(--font-mono); font-size: 11.5px; background: var(--neutral-100); padding: 2px 6px; border-radius: 4px; color: var(--text-secondary); max-width: 200px; display: inline-block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.size-text { font-family: var(--font-mono); font-size: 12px; color: var(--text-tertiary); }
.status-cell { display: flex; align-items: center; justify-content: center; gap: 6px; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.status-dot.active { background: var(--success); animation: pulse 2s infinite; box-shadow: 0 0 0 2px rgba(16,185,129,0.2); }
.status-dot.inactive { background: var(--neutral-300); }
.action-cell { display: flex; align-items: center; gap: 4px; flex-wrap: nowrap; }

/* 策略单选组 */
.strategy-group { flex-wrap: wrap; }
.strategy-group :deep(.el-radio-button__inner) {
  font-size: 12px !important;
  padding: 6px 12px !important;
  border-radius: 6px !important;
}

/* 间隔输入 */
.interval-input { display: flex; align-items: center; gap: 10px; }
.input-unit { font-size: 12px; color: var(--text-tertiary); white-space: nowrap; }

/* 表单提示 */
.form-hint-text { font-size: 12px; color: var(--text-tertiary); margin-left: 10px; }

/* 忽略规则 */
.ignore-add-row { display: flex; gap: 10px; margin-bottom: 16px; }
.ignore-list { display: flex; flex-direction: column; gap: 4px; max-height: 260px; overflow-y: auto; }
.ignore-rule-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: var(--neutral-50); border-radius: 8px; border: 1px solid var(--border-light); }
.rule-code { flex: 1; font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }

/* 防止表头换行 */
.enhanced-table :deep(.el-table__header-wrapper th .cell) {
  white-space: nowrap;
}

/* 过渡 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s, transform 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: scale(0.95); }

/* 防止表单标签换行 */
.tasks-page :deep(.el-form-item__label) {
  white-space: nowrap;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(16,185,129,0.2); }
  50% { box-shadow: 0 0 0 4px rgba(16,185,129,0.08); }
}
</style>
