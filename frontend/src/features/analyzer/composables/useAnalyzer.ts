import { ref } from 'vue'
import type { AnalysisResult } from '../types'
import api from '@/services/api'

export function useAnalyzer() {
  const loading = ref(false)
  const result = ref<AnalysisResult | null>(null)
  const error = ref<string | null>(null)

  async function analyze(file: File, jdText: string) {
    loading.value = true
    error.value = null
    result.value = null

    const formData = new FormData()
    formData.append('file', file)
    formData.append('jd_text', jdText)

    try {
      const { data } = await api.post<AnalysisResult>('/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      result.value = data
    } catch (e: any) {
      error.value = e?.message ?? 'Unknown error'
    } finally {
      loading.value = false
    }
  }

  function reset() {
    loading.value = false
    result.value = null
    error.value = null
  }

  return { loading, result, error, analyze, reset }
}
