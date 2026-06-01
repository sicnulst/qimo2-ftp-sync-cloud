import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error.response?.data || error)
  }
)

// 认证API
export const authApi = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  profile: () => api.get('/auth/profile')
}

// FTP服务器API
export const ftpApi = {
  list: () => api.get('/ftp/servers'),
  add: (data) => api.post('/ftp/servers', data),
  delete: (id) => api.delete(`/ftp/servers/${id}`),
  test: (id) => api.post(`/ftp/servers/${id}/test`),
  files: (id, path = '/') => api.get(`/ftp/servers/${id}/files?path=${encodeURIComponent(path)}`),
  builtinStatus: () => api.get('/ftp/builtin/status'),
  builtinStart: () => api.post('/ftp/builtin/start'),
  builtinStop: () => api.post('/ftp/builtin/stop'),
  builtinRestart: () => api.post('/ftp/builtin/restart')
}

// 同步任务API
export const syncApi = {
  list: () => api.get('/sync/tasks'),
  add: (data) => api.post('/sync/tasks', data),
  update: (id, data) => api.put(`/sync/tasks/${id}`, data),
  delete: (id) => api.delete(`/sync/tasks/${id}`),
  start: (id) => api.post(`/sync/tasks/${id}/start`),
  stop: (id) => api.post(`/sync/tasks/${id}/stop`),
  pause: (id) => api.post(`/sync/tasks/${id}/pause`),
  manualSync: (id) => api.post(`/sync/tasks/${id}/sync`),
  getIgnoreRules: (taskId) => api.get(`/sync/tasks/${taskId}/ignore`),
  addIgnoreRule: (taskId, data) => api.post(`/sync/tasks/${taskId}/ignore`, data),
  deleteIgnoreRule: (taskId, ruleId) => api.delete(`/sync/tasks/${taskId}/ignore/${ruleId}`),
  watcherStatus: () => api.get('/sync/watcher/status'),
  schedulerStatus: () => api.get('/sync/scheduler/status')
}

// 历史记录API
export const historyApi = {
  getTaskHistory: (taskId, page = 1) => api.get(`/history/${taskId}?page=${page}`),
  getAllHistory: (page = 1) => api.get(`/history/all?page=${page}`),
  getStats: () => api.get('/history/stats')
}

// 文件浏览 + 差异对比 + 远端下载 + 文件管理API
export const filesApi = {
  local: (path, subpath = '/') => api.get('/files/local', { params: { path, subpath } }),
  diff: (data) => api.post('/files/diff', data),
  downloadRemote: (ftpHost, ftpPort, ftpUsername, ftpPassword, remotePath) =>
    api.get('/files/remote/download', {
      params: {
        ftp_host: ftpHost,
        ftp_port: ftpPort,
        ftp_username: ftpUsername,
        ftp_password: ftpPassword,
        path: remotePath
      },
      responseType: 'blob'
    }),
  // 本地文件管理
  localMkdir: (path, subpath, folder_name) =>
    api.post('/files/local/mkdir', { path, subpath, folder_name }),
  localUpload: (formData) =>
    api.post('/files/local/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  localDelete: (path, file_path) =>
    api.post('/files/local/delete', { path, file_path }),
  // 远端文件管理
  remoteUpload: (formData) =>
    api.post('/files/remote/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  remoteMkdir: (ftpHost, ftpPort, ftpUsername, ftpPassword, remotePath, folder_name) =>
    api.post('/files/remote/mkdir', {
      ftp_host: ftpHost, ftp_port: ftpPort,
      ftp_username: ftpUsername, ftp_password: ftpPassword,
      remote_path: remotePath, folder_name
    }),
  remoteDelete: (ftpHost, ftpPort, ftpUsername, ftpPassword, filePath, isDir) =>
    api.post('/files/remote/delete', {
      ftp_host: ftpHost, ftp_port: ftpPort,
      ftp_username: ftpUsername, ftp_password: ftpPassword,
      file_path: filePath, is_dir: isDir
    })
}

export default api
