import axios from 'axios'

export interface ApiError {
  type: 'file' | 'scanned' | 'parse' | 'server' | 'network' | 'unknown'
  userMessage: string
  detail: string
}

function classifyError(error: any): ApiError {
  // Network error (no response from server)
  if (!error.response) {
    return {
      type: 'network',
      userMessage: '网络连接失败，请检查网络后重试',
      detail: error.message ?? 'Network error',
    }
  }

  const status = error.response.status
  const data = error.response.data

  // Try to extract backend message
  const backendMsg: string = data?.message ?? ''
  const detail: string = data?.detail ?? backendMsg

  // 400 — File validation errors
  if (status === 400) {
    if (backendMsg.includes('格式')) {
      return { type: 'file', userMessage: backendMsg, detail }
    }
    if (backendMsg.includes('大小') || backendMsg.includes('超过')) {
      return { type: 'file', userMessage: backendMsg, detail }
    }
    if (backendMsg.includes('过短') || backendMsg.includes('字符')) {
      return { type: 'file', userMessage: backendMsg, detail }
    }
    return { type: 'file', userMessage: backendMsg || '文件不符合要求，请检查后重试', detail }
  }

  // 422 — PDF parse / scanned PDF
  if (status === 422) {
    if (backendMsg.includes('扫描件')) {
      return { type: 'scanned', userMessage: backendMsg, detail }
    }
    return { type: 'parse', userMessage: backendMsg || 'PDF 解析失败，请确认文件完好', detail }
  }

  // 500 — Server errors
  if (status === 500) {
    return { type: 'server', userMessage: backendMsg || '服务器处理异常，请稍后重试', detail }
  }

  return {
    type: 'unknown',
    userMessage: backendMsg || `请求失败 (${status})`,
    detail,
  }
}

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error)
    const apiError = classifyError(error)
    return Promise.reject(apiError)
  },
)

export default api
