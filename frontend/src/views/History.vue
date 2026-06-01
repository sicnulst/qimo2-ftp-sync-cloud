<template>
  <div class="history-page">
    <!-- 顶部统计卡片 -->
    <div class="stats-bar">
      <div class="stat-chip total">
        <div class="chip-icon"><el-icon :size="16"><DataAnalysis /></el-icon></div>
        <div class="chip-body">
          <div class="chip-num">{{ stats.total || 0 }}</div>
          <div class="chip-label">总同步次数</div>
        </div>
      </div>
      <div class="stat-chip success">
        <div class="chip-icon"><el-icon :size="16"><CircleCheck /></el-icon></div>
        <div class="chip-body">
          <div class="chip-num">{{ stats.success || 0 }}</div>
          <div class="chip-label">成功次数</div>
        </div>
      </div>
      <div class="stat-chip failed">
        <div class="chip-icon"><el-icon :size="16"><CircleClose /></el-icon></div>
        <div class="chip-body">
          <div class="chip-num">{{ stats.failed || 0 }}</div>
          <div class="chip-label">失败次数</div>
        </div>
      </div>
      <div class="stat-chip rate" v-if="stats.total > 0">
        <div class="chip-icon"><el-icon :size="16"><TrendCharts /></el-icon></div>
        <div class="chip-body">
          <div class="chip-num">{{ Math.round((stats.success / stats.total) * 100) }}%</div>
          <div class="chip-label">成功率</div>
        </div>
      </div>
    </div>

    <!-- 主卡片 -->
    <el-card>
      <template #header>
        <div class="page-header">
          <div class="header-left">
            <el-icon class="title-icon"><Clock /></el-icon>
            <span class="header-title">同步历史记录</span>
          </div>
          <div class="header-right">
            <el-select
              v-model="selectedTask"
              placeholder="全部任务"
              clearable
              style="width: 200px"
              @change="onTaskChange"
            >
              <el-option label="全部任务" value="" />
              <el-option
                v-for="t in tasks"
                :key="t.id"
                :label="`#${t.id} ${t.local_path}`"
                :value="t.id"
              />
            </el-select>
            <el-button @click="loadHistory" size="default">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <!-- 历史表格 -->
      <el-table
        :data="history"
        v-loading="loading"
        style="width: 100%"
        stripe
        class="enhanced-table"
      >
        <el-table-column label="同步时间" width="170">
          <template #default="{ row }">
            <div class="time-cell">
              <div class="time-main">{{ formatTimeMain(row.sync_time) }}</div>
              <div class="time-date">{{ formatTimeDate(row.sync_time) }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="文件名" width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="file-cell">
              <el-icon :size="14" :color="getFileIconColor(row.file_name)">
                <Document />
              </el-icon>
              <span class="file-name">{{ row.file_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="文件路径" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <code class="path-code-sm">{{ row.file_path }}</code>
          </template>
        </el-table-column>
        <el-table-column label="方向" width="110" align="center">
          <template #default="{ row }">
            <div class="direction-cell" :class="row.direction === 'local_to_remote' ? 'upload' : 'download'">
              <el-icon :size="12">
                <component :is="row.direction === 'local_to_remote' ? 'Top' : 'Bottom'" />
              </el-icon>
              <span>{{ row.direction === 'local_to_remote' ? '上传' : '下载' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getActionType(row.action)" size="small">
              {{ getActionName(row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="90" align="center">
          <template #default="{ row }">
            <div class="result-cell" :class="row.status">
              <el-icon :size="14">
                <component :is="row.status === 'success' ? 'CircleCheckFilled' : 'CircleCloseFilled'" />
              </el-icon>
              <span>{{ row.status === 'success' ? '成功' : '失败' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="错误信息" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.error_message" class="error-text">{{ row.error_message }}</span>
            <span v-else class="no-error">—</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-bar">
        <span class="total-hint">共 {{ total }} 条记录</span>
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="50"
          :total="total"
          layout="prev, pager, next"
          @current-change="loadHistory"
          background
        />
      </div>

      <el-empty v-if="history.length === 0 && !loading" description="暂无同步历史记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { historyApi, syncApi } from '../api'

const history = ref([])
const tasks = ref([])
const stats = ref({ total: 0, success: 0, failed: 0 })
const loading = ref(false)
const currentPage = ref(1)
const total = ref(0)
const selectedTask = ref('')

const formatTimeMain = (time) => {
  if (!time) return '-'
  const d = time.includes('T') ? new Date(time) : new Date(time.replace(' ', 'T'))
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const formatTimeDate = (time) => {
  if (!time) return '-'
  const d = time.includes('T') ? new Date(time) : new Date(time.replace(' ', 'T'))
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const getFileIconColor = (name) => {
  if (!name) return '#9ca3af'
  const ext = name.split('.').pop()?.toLowerCase()
  const colors = { js: '#f7df1e', ts: '#3178c6', vue: '#42b883', py: '#3776ab', md: '#083fa1', json: '#f59e0b', css: '#2965f1', html: '#e44d26' }
  return colors[ext] || '#9ca3af'
}

const getActionName = (action) => {
  const names = { upload_new: '新增上传', upload_update: '更新上传', download_new: '新增下载', download_update: '更新下载', delete_remote: '远端删除', delete_local: '本地删除' }
  return names[action] || action
}

const getActionType = (action) => {
  if (action?.includes('new')) return 'success'
  if (action?.includes('update')) return 'warning'
  if (action?.includes('delete')) return 'danger'
  return 'info'
}

const onTaskChange = () => { currentPage.value = 1; loadHistory() }

const loadHistory = async () => {
  loading.value = true
  try {
    let res
    if (selectedTask.value) { res = await historyApi.getTaskHistory(selectedTask.value, currentPage.value) }
    else { res = await historyApi.getAllHistory(currentPage.value) }
    history.value = res.history || []; total.value = res.total || 0
  } catch (e) { ElMessage.error('加载失败') } finally { loading.value = false }
}

const loadStats = async () => {
  try { stats.value = await historyApi.getStats() } catch (e) {}
}

const loadTasks = async () => {
  try { const res = await syncApi.list(); tasks.value = res.tasks || [] } catch (e) {}
}

onMounted(() => { loadHistory(); loadStats(); loadTasks() })
</script>

<style scoped>
.history-page { display: flex; flex-direction: column; gap: 16px; }

/* 统计条 */
.stats-bar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.stat-chip {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 18px;
  background: white;
  border-radius: 12px;
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-xs);
  min-width: 140px;
}

.chip-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-chip.total .chip-icon { background: rgba(107, 114, 128, 0.1); color: #6b7280; }
.stat-chip.success .chip-icon { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.stat-chip.failed .chip-icon { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
.stat-chip.rate .chip-icon { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }

.chip-num { font-size: 22px; font-weight: 700; color: var(--text-primary); line-height: 1; }
.chip-label { font-size: 12px; color: var(--text-tertiary); margin-top: 3px; font-weight: 500; }

/* 页头 */
.page-header { display: flex; justify-content: space-between; align-items: center; }
.header-left { display: flex; align-items: center; gap: 8px; }
.title-icon { color: var(--primary-500); font-size: 18px; }
.header-title { font-weight: 600; font-size: 15px; }
.header-right { display: flex; align-items: center; gap: 10px; }

/* 时间 */
.time-cell { line-height: 1.3; }
.time-main { font-size: 13px; font-weight: 500; color: var(--text-primary); font-family: var(--font-mono); }
.time-date { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }

/* 文件 */
.file-cell { display: flex; align-items: center; gap: 7px; }
.file-name { font-size: 13px; font-weight: 500; color: var(--text-secondary); }

.path-code-sm { font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary); background: var(--neutral-50); padding: 2px 5px; border-radius: 4px; }

/* 方向 */
.direction-cell {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.direction-cell.upload { background: rgba(59, 130, 246, 0.08); color: #2563eb; }
.direction-cell.download { background: rgba(16, 185, 129, 0.08); color: #059669; }

/* 结果 */
.result-cell {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  font-weight: 500;
}
.result-cell.success { color: var(--success); }
.result-cell.failed, .result-cell.error { color: var(--danger); }

.error-text { font-size: 12px; color: var(--danger); }
.no-error { color: var(--text-quaternary); }

/* 分页 */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-light);
}
.total-hint { font-size: 13px; color: var(--text-tertiary); }
</style>
