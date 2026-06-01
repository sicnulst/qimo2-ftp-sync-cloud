<template>
  <div class="servers-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <div class="header-left">
            <div class="page-title">
              <el-icon class="title-icon"><Connection /></el-icon>
              <span>FTP 服务器</span>
              <el-tag type="info" size="small" class="count-tag">{{ servers.length }}</el-tag>
            </div>
            <transition name="fade">
              <el-button v-if="selectedServers.length > 0" type="danger" size="small" @click="batchDelete">
                <el-icon><Delete /></el-icon>
                删除选中 ({{ selectedServers.length }})
              </el-button>
            </transition>
          </div>
          <el-button type="primary" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            添加服务器
          </el-button>
        </div>
      </template>

      <!-- 空状态 -->
      <div v-if="servers.length === 0 && !loading" class="empty-page">
        <div class="empty-illustration">
          <el-icon :size="56" color="#d1d5db"><Connection /></el-icon>
        </div>
        <h3>暂无 FTP 服务器</h3>
        <p>添加一个 FTP 服务器开始使用</p>
        <el-button type="primary" @click="showAddDialog">
          <el-icon><Plus /></el-icon>
          添加第一个服务器
        </el-button>
      </div>

      <!-- 服务器表格 -->
      <el-table
        v-else
        :data="servers"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        style="width: 100%"
        fit
        stripe
        class="enhanced-table"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="name" label="服务器名称" min-width="140">
          <template #default="{ row }">
            <div class="server-name-cell">
              <div class="server-avatar">
                {{ row.name.charAt(0).toUpperCase() }}
              </div>
              <div>
                <div class="cell-main">{{ row.name }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="主机地址" min-width="160">
          <template #default="{ row }">
            <code class="code-cell">{{ row.host }}:{{ row.port }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户名" min-width="100">
          <template #default="{ row }">
            <span class="text-secondary">{{ row.username || '匿名' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <div class="status-cell">
              <span class="status-dot" :class="row.is_active ? 'success' : 'error'"></span>
              <span class="status-text">{{ row.is_active ? '启用' : '禁用' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-cell">
              <el-button type="primary" link size="small" @click="testConnection(row)" :loading="row.testing">
                <el-icon><Connection /></el-icon>
                测试
              </el-button>
              <el-button type="info" link size="small" @click="viewFiles(row)">
                <el-icon><FolderOpened /></el-icon>
                浏览
              </el-button>
              <el-button type="danger" link size="small" @click="deleteServer(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加服务器对话框 -->
    <el-dialog v-model="dialogVisible" title="添加 FTP 服务器" width="480px" align-center>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px" label-position="left">
        <el-form-item label="服务器名称" prop="name">
          <el-input v-model="form.name" placeholder="如：我的云盘" />
        </el-form-item>
        <el-form-item label="主机地址" prop="host">
          <el-input v-model="form.host" placeholder="127.0.0.1" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="可选，匿名访问留空" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="可选" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addServer" :loading="submitting">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ftpApi } from '../api'

const router = useRouter()
const servers = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref()
const selectedServers = ref([])

const form = reactive({ name: '', host: '127.0.0.1', port: 2121, username: 'admin', password: 'admin123' })
const rules = {
  name: [{ required: true, message: '请输入服务器名称', trigger: 'blur' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }]
}

const handleSelectionChange = (val) => { selectedServers.value = val }

const loadServers = async () => {
  loading.value = true
  try {
    const res = await ftpApi.list()
    servers.value = (res.servers || []).map(s => ({ ...s, testing: false }))
  } catch (e) { ElMessage.error('加载失败') } finally { loading.value = false }
}

const showAddDialog = () => {
  form.name = ''; form.host = '127.0.0.1'; form.port = 2121
  form.username = 'admin'; form.password = 'admin123'
  dialogVisible.value = true
}

const addServer = async () => {
  try {
    await formRef.value.validate()
    submitting.value = true
    await ftpApi.add(form)
    ElMessage({ message: '服务器添加成功', type: 'success' })
    dialogVisible.value = false
    loadServers()
  } catch (e) { if (e?.error) ElMessage.error(e.error) }
  finally { submitting.value = false }
}

const testConnection = async (server) => {
  server.testing = true
  try {
    const res = await ftpApi.test(server.id)
    if (res.status === 'success') {
      ElMessage({ message: `连接成功！发现 ${res.files_count} 个文件`, type: 'success' })
    } else {
      ElMessage.error(res.message)
    }
  } catch (e) { ElMessage.error(e?.message || '连接失败') }
  finally { server.testing = false }
}

const viewFiles = (server) => { router.push(`/files?server_id=${server.id}`) }

const deleteServer = async (server) => {
  try {
    await ElMessageBox.confirm(
      `确定删除服务器「${server.name}」？相关同步任务也会被删除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' }
    )
    await ftpApi.delete(server.id)
    ElMessage.success('删除成功')
    loadServers()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedServers.value.length} 个服务器？`,
      '批量删除',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' }
    )
    for (const s of selectedServers.value) { await ftpApi.delete(s.id) }
    ElMessage.success(`已删除 ${selectedServers.value.length} 个服务器`)
    selectedServers.value = []
    loadServers()
  } catch (e) { if (e !== 'cancel') ElMessage.error('批量删除失败') }
}

onMounted(loadServers)
</script>

<style scoped>
.servers-page { height: 100%; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
}

.title-icon {
  color: var(--primary-500);
  font-size: 18px;
}

.count-tag {
  font-size: 12px !important;
}

/* 空状态 */
.empty-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  gap: 12px;
}

.empty-illustration {
  width: 96px;
  height: 96px;
  border-radius: 24px;
  background: var(--neutral-100);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.empty-page h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.empty-page p {
  font-size: 14px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}

/* 服务器名称单元格 */
.server-name-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.server-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: white;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.cell-main {
  font-size: 13.5px;
  font-weight: 500;
  color: var(--text-primary);
}

.code-cell {
  font-family: var(--font-mono);
  font-size: 12px;
  background: var(--neutral-100);
  padding: 3px 8px;
  border-radius: 6px;
  color: var(--text-secondary);
}

.text-secondary { color: var(--text-tertiary); font-size: 13px; }

/* 状态 */
.status-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.success { background: var(--success); }
.status-dot.error { background: var(--danger); }

.status-text {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* 操作 */
.action-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 防止表头换行 */
.enhanced-table :deep(.el-table__header-wrapper th .cell) {
  white-space: nowrap;
}

/* 防止表单标签换行 */
.servers-page :deep(.el-form-item__label) {
  white-space: nowrap;
}

/* 过渡 */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s, transform 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: scale(0.95); }
</style>
