import { ref, onUnmounted } from 'vue'
import type { AnalysisResult, QuickAnalysisData, TaskStatusResult, UploadResult } from '../types'
import type { ApiError } from '@/services/api'
import api from '@/services/api'

// Module-level reactive state shared across all consumers
const loading = ref(false)
const result = ref<AnalysisResult | null>(null)
const error = ref<string | null>(null)
const uploadProgress = ref(0)

// Async polling state
const asyncStatus = ref<'idle' | 'loading' | 'polling' | 'done' | 'failed'>('idle')
const partialResult = ref<QuickAnalysisData | null>(null)
const taskId = ref<string | null>(null)

let pollTimer: ReturnType<typeof setInterval> | null = null
let pollTimeout: ReturnType<typeof setTimeout> | null = null
let activeTaskId: string | null = null

const POLL = {
  initialDelay: 800,
  fastInterval: 1000,
  maxDuration: 90000,
}

export function useAnalyzer() {

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    if (pollTimeout) {
      clearTimeout(pollTimeout)
      pollTimeout = null
    }
    activeTaskId = null
  }

  async function pollTask(id: string) {
    if (activeTaskId !== id) return
    try {
      const { data } = await api.get<TaskStatusResult>(`/analyze/tasks/${id}`)
      if (activeTaskId !== id) return
      if (!data.data) return

      if (data.data.status === 'succeeded' && data.data.result) {
        stopPolling()
        asyncStatus.value = 'done'
        result.value = { code: 200, message: '解析成功', data: data.data.result }
      } else if (data.data.status === 'failed' || data.data.status === 'expired') {
        stopPolling()
        asyncStatus.value = 'failed'
        if (data.data.error) {
          error.value = data.data.error
        }
      }
    } catch {
      // polling errors are non-fatal; keep trying
    }
  }

  function startPolling(id: string) {
    stopPolling()
    activeTaskId = id
    const startTime = Date.now()

    pollTimeout = setTimeout(() => {
      if (activeTaskId !== id) return
      pollTask(id)
      pollTimer = setInterval(() => {
        if (activeTaskId !== id) return
        const elapsed = Date.now() - startTime
        if (elapsed > POLL.maxDuration) {
          stopPolling()
          asyncStatus.value = 'failed'
          error.value = '深度分析超时，请重新提交'
          return
        }
        pollTask(id)
      }, POLL.fastInterval)
    }, POLL.initialDelay)
  }

  async function analyze(file: File, jdText: string) {
    stopPolling()
    loading.value = true
    asyncStatus.value = 'loading'
    error.value = null
    result.value = null
    partialResult.value = null
    taskId.value = null
    uploadProgress.value = 0

    const formData = new FormData()
    formData.append('file', file)
    formData.append('jd_text', jdText)

    try {
      const { data } = await api.post<AnalysisResult>('/analyze', formData, {
        headers: {
          'Content-Type': undefined,
        },
        onUploadProgress: (e) => {
          if (e.total) {
            uploadProgress.value = Math.round((e.loaded / e.total) * 100)
          }
        },
      })

      const responseData = data.data as QuickAnalysisData | null
      if (responseData && 'task_id' in responseData && responseData.status === 'running') {
        partialResult.value = responseData
        taskId.value = responseData.task_id
        loading.value = false
        asyncStatus.value = 'polling'
        startPolling(responseData.task_id)
      } else {
        result.value = data
        loading.value = false
        asyncStatus.value = 'done'
      }
    } catch (e: any) {
      loading.value = false
      asyncStatus.value = 'failed'
      error.value = (e as ApiError).userMessage ?? e?.message ?? 'Unknown error'
    }
  }

  async function upload(file: File) {
    loading.value = true
    error.value = null
    result.value = null
    uploadProgress.value = 0

    const formData = new FormData()
    formData.append('file', file)

    try {
      const { data } = await api.post<UploadResult>('/upload', formData, {
        onUploadProgress: (e) => {
          if (e.total) {
            uploadProgress.value = Math.round((e.loaded / e.total) * 100)
          }
        },
      })
      return data
    } catch (e: any) {
      error.value = (e as ApiError).userMessage ?? e?.message ?? 'Unknown error'
      return null
    } finally {
      loading.value = false
    }
  }

  function reset() {
    stopPolling()
    loading.value = false
    result.value = null
    error.value = null
    uploadProgress.value = 0
    asyncStatus.value = 'idle'
    partialResult.value = null
    taskId.value = null
  }

  onUnmounted(() => {
    stopPolling()
  })

  return {
    loading, result, error, uploadProgress,
    asyncStatus, partialResult, taskId,
    analyze, upload, reset, stopPolling,
  }
}