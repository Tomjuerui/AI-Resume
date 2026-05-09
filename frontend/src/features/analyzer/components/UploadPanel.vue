<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAnalyzer } from '../composables/useAnalyzer'
import { bytesToMB } from '@/utils/formatters'

const {
  loading, result, error, uploadProgress,
  partialResult, asyncStatus,
  analyze, reset,
} = useAnalyzer()

const fileInput = ref<HTMLInputElement | null>(null)
const jdText = ref('')
const file = ref<File | null>(null)
const fileName = ref('')
const fileSize = ref('')
const clientError = ref<string | null>(null)
const isDragging = ref(false)

const jdCharCount = computed(() => jdText.value.length)
const jdTooShort = computed(() => jdText.value.length > 0 && jdText.value.trim().length < 10)
const canSubmit = computed(() =>
  file.value && jdText.value.trim().length >= 10 && !loading.value && asyncStatus.value !== 'polling',
)

// ── File validation ──
function validateFile(f: File): string | null {
  if (!f.name.toLowerCase().endsWith('.pdf')) {
    return `不支持 "${f.name.split('.').pop()}" 格式，请上传 PDF 文件`
  }
  if (f.size > 10 * 1024 * 1024) {
    return `文件大小 ${bytesToMB(f.size)} 超过 10MB 限制`
  }
  return null
}

function onFileChange(e: Event) {
  clientError.value = null
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) {
    const f = input.files[0]
    const err = validateFile(f)
    if (err) {
      clientError.value = err
      input.value = ''
      return
    }
    setFile(f)
  }
}

function setFile(f: File) {
  file.value = f
  fileName.value = f.name
  fileSize.value = bytesToMB(f.size)
}

// ── Drag & Drop ──
function onDragEnter(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}
function onDragOver(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}
function onDragLeave(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
}
function onDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
  clientError.value = null
  const f = e.dataTransfer?.files?.[0]
  if (!f) return
  const err = validateFile(f)
  if (err) {
    clientError.value = err
    return
  }
  setFile(f)
}

// ── Submit ──
async function onSubmit() {
  if (!file.value || jdText.value.trim().length < 10) return
  clientError.value = null
  await analyze(file.value, jdText.value.trim())
}

// ── Reset ──
function onReset() {
  reset()
  jdText.value = ''
  file.value = null
  fileName.value = ''
  fileSize.value = ''
  clientError.value = null
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-800">AI Resume Analyzer</h1>
      <button
        v-if="result || partialResult"
        class="text-sm text-blue-600 hover:text-blue-800 transition-colors"
        @click="onReset"
      >
        + New Analysis
      </button>
    </div>

    <!-- JD Input -->
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-2">
        Job Description (JD)
      </label>
      <textarea
        v-model="jdText"
        rows="10"
        class="w-full border rounded-lg p-3 text-sm outline-none resize-none transition-colors"
        :class="jdTooShort ? 'border-orange-300 focus:ring-2 focus:ring-orange-500' : 'border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent'"
        placeholder="Paste the job description here..."
      />
      <p
        v-if="jdText.length > 0 && jdCharCount < 10"
        class="mt-1 text-xs text-orange-500"
      >
        JD text too short ({{ jdCharCount }}/10 characters minimum)
      </p>
    </div>

    <!-- File Upload -->
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-2">
        Upload Resume (PDF)
      </label>
      <div
        class="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer transition-colors"
        :class="isDragging ? 'border-blue-400 bg-blue-50' : fileName ? 'border-green-300 bg-green-50' : 'border-gray-300 hover:border-blue-400'"
        @dragenter="onDragEnter"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
        @click="fileInput?.click()"
      >
        <div v-if="fileName" class="text-center">
          <div class="text-sm font-medium text-gray-700">{{ fileName }}</div>
          <div class="text-xs text-gray-400 mt-1">{{ fileSize }}</div>
        </div>
        <div v-else class="text-sm text-gray-500 text-center">
          <div>Drag & drop PDF here</div>
          <div class="text-xs text-gray-400 mt-1">or click to browse</div>
        </div>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept=".pdf"
        class="hidden"
        @change="onFileChange"
      />
    </div>

    <!-- Upload Progress -->
    <div
      v-if="loading && uploadProgress > 0"
      class="w-full bg-gray-200 rounded-full h-2 overflow-hidden"
    >
      <div
        class="bg-blue-500 h-2 rounded-full transition-all duration-300"
        :style="{ width: uploadProgress + '%' }"
      />
    </div>

    <!-- Submit -->
    <button
      :disabled="!canSubmit"
      class="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
      @click="onSubmit"
    >
      <span v-if="loading && uploadProgress > 0">Uploading {{ uploadProgress }}%...</span>
      <span v-else-if="loading">Analyzing...</span>
      <span v-else>Analyze Resume</span>
    </button>

    <!-- Client-side Error -->
    <div v-if="clientError" class="p-3 bg-yellow-50 text-yellow-700 rounded-lg text-sm border border-yellow-200">
      {{ clientError }}
    </div>

    <!-- API Error -->
    <div v-if="error" class="p-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-200">
      {{ error }}
    </div>
  </div>
</template>
