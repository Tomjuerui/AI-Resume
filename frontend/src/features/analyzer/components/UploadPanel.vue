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
  <div class="space-y-5">
    <!-- Header -->
    <div class="bg-gradient-to-r from-blue-50 to-indigo-50 -mx-6 -mt-6 px-6 pt-5 pb-4 border-b border-blue-100">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <span class="text-2xl">📄</span>
          <h1 class="text-xl font-bold text-gray-800">AI 简历分析</h1>
        </div>
        <button
          v-if="result || partialResult"
          class="text-sm text-blue-600 hover:text-blue-800 transition-colors font-medium"
          @click="onReset"
        >
          + 新建分析
        </button>
      </div>
      <p class="text-xs text-gray-500 mt-1.5 ml-9">上传简历 PDF 并粘贴职位描述，智能匹配分析</p>
    </div>

    <!-- Step 1: JD Input -->
    <div>
      <div class="flex items-center gap-1.5 mb-2">
        <span class="flex-shrink-0 w-5 h-5 bg-blue-500 text-white text-xs rounded-full flex items-center justify-center font-medium">1</span>
        <label class="text-sm font-medium text-gray-700">职位描述 (JD)</label>
        <span class="text-xs text-gray-400">— 请输入要匹配的目标职位要求</span>
      </div>
      <div class="relative">
        <textarea
          v-model="jdText"
          rows="9"
          class="w-full border rounded-lg p-3 text-sm outline-none resize-none transition-colors"
          :class="jdTooShort ? 'border-orange-300 focus:ring-2 focus:ring-orange-500' : 'border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent'"
          placeholder="请粘贴职位描述内容..."
        />
        <span
          v-if="jdText.length > 0"
          class="absolute bottom-2 right-3 text-xs"
          :class="jdTooShort ? 'text-orange-400' : 'text-gray-400'"
        >
          已输入 {{ jdCharCount }} 字
        </span>
      </div>
      <p
        v-if="jdText.length > 0 && jdCharCount < 10"
        class="mt-1 text-xs text-orange-500"
      >
        职位描述过短 ({{ jdCharCount }}/最少10个字符)
      </p>
    </div>

    <!-- Step 2: File Upload -->
    <div>
      <div class="flex items-center gap-1.5 mb-2">
        <span class="flex-shrink-0 w-5 h-5 bg-blue-500 text-white text-xs rounded-full flex items-center justify-center font-medium">2</span>
        <label class="text-sm font-medium text-gray-700">上传简历 (PDF)</label>
        <span class="text-xs text-gray-400">— 支持 PDF 格式，最大 10MB</span>
      </div>
      <div
        class="flex flex-col items-center justify-center w-full h-36 border-2 border-dashed rounded-lg cursor-pointer transition-all"
        :class="isDragging ? 'border-blue-400 bg-blue-50 scale-[1.02]' : fileName ? 'border-green-300 bg-green-50/50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'"
        @dragenter="onDragEnter"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
        @click="fileInput?.click()"
      >
        <div v-if="fileName" class="text-center">
          <div class="text-3xl mb-1">📄</div>
          <div class="text-sm font-medium text-gray-700 flex items-center justify-center gap-1">
            <span class="text-green-500">✓</span>
            {{ fileName }}
          </div>
          <div class="text-xs text-gray-400 mt-1">{{ fileSize }}</div>
        </div>
        <div v-else class="text-center">
          <div class="text-3xl mb-1">📂</div>
          <div class="text-sm text-gray-500">拖拽 PDF 文件到此处</div>
          <div class="text-xs text-gray-400 mt-1">或点击浏览文件</div>
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
        class="bg-gradient-to-r from-blue-400 to-indigo-500 h-2 rounded-full transition-all duration-300"
        :style="{ width: uploadProgress + '%' }"
      />
    </div>

    <!-- Submit -->
    <button
      :disabled="!canSubmit"
      class="w-full py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-lg font-medium hover:from-blue-600 hover:to-indigo-700 disabled:from-gray-300 disabled:to-gray-300 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg disabled:shadow-none"
      @click="onSubmit"
    >
      <span v-if="loading && uploadProgress > 0">上传中 {{ uploadProgress }}%...</span>
      <span v-else-if="loading">
        <span class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2 align-text-bottom" />
        分析中...
      </span>
      <span v-else>开始分析</span>
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
