import { ref } from 'vue'
import type { AnalysisResult, UploadResult } from '../types'
import type { ApiError } from '@/services/api'
import api from '@/services/api'

// Module-level reactive state shared across all consumers
const loading = ref(false)
const result = ref<AnalysisResult | null>(null)
const error = ref<string | null>(null)
const uploadProgress = ref(0)

export function useAnalyzer() {

  async function analyze(file: File, jdText: string) {
    loading.value = true
    error.value = null
    result.value = null
    uploadProgress.value = 0

    const formData = new FormData()
    formData.append('file', file)
    formData.append('jd_text', jdText)

    try {
      const { data } = await api.post<AnalysisResult>('/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) {
            uploadProgress.value = Math.round((e.loaded / e.total) * 100)
          }
        },
      })
      result.value = data
    } catch (e: any) {
      // e is now ApiError with a userMessage field
      error.value = (e as ApiError).userMessage ?? e?.message ?? 'Unknown error'
    } finally {
      loading.value = false
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
        headers: { 'Content-Type': 'multipart/form-data' },
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
    loading.value = false
    result.value = null
    error.value = null
    uploadProgress.value = 0
  }

  return { loading, result, error, uploadProgress, analyze, upload, reset }
}
