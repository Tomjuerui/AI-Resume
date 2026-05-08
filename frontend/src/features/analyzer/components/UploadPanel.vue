<script setup lang="ts">
import { ref } from 'vue'
import { useAnalyzer } from '../composables/useAnalyzer'

const { loading, result, error, analyze } = useAnalyzer()

const jdText = ref('')
const file = ref<File | null>(null)
const fileName = ref('')

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) {
    file.value = input.files[0]
    fileName.value = input.files[0].name
  }
}

async function onSubmit() {
  if (!file.value || !jdText.value.trim()) return
  await analyze(file.value, jdText.value.trim())
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-gray-800">AI Resume Analyzer</h1>

    <!-- JD Input -->
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-2">
        Job Description (JD)
      </label>
      <textarea
        v-model="jdText"
        rows="10"
        class="w-full border border-gray-300 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
        placeholder="Paste the job description here..."
      />
    </div>

    <!-- File Upload -->
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-2">
        Upload Resume (PDF)
      </label>
      <label
        class="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-400 transition-colors"
      >
        <div class="text-sm text-gray-500">
          <template v-if="fileName">
            {{ fileName }}
          </template>
          <template v-else>
            Click or drag to upload PDF
          </template>
        </div>
        <input
          type="file"
          accept=".pdf"
          class="hidden"
          @change="onFileChange"
        />
      </label>
    </div>

    <!-- Submit -->
    <button
      :disabled="!file || !jdText.trim() || loading"
      class="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
      @click="onSubmit"
    >
      {{ loading ? 'Analyzing...' : 'Analyze Resume' }}
    </button>

    <!-- Error -->
    <div v-if="error" class="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
      {{ error }}
    </div>
  </div>
</template>
