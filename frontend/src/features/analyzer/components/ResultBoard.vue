<script setup lang="ts">
import { useAnalyzer } from '../composables/useAnalyzer'
import RadarChart from './RadarChart.vue'

const { result, loading, error } = useAnalyzer()
</script>

<template>
  <div>
    <!-- Empty State -->
    <div
      v-if="!result && !loading"
      class="flex flex-col items-center justify-center h-full text-gray-400"
    >
      <div class="text-6xl mb-4">&#x1F4C4;</div>
      <p class="text-lg">Upload a resume and paste a JD to get started</p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center h-full">
      <p class="text-gray-500 text-lg animate-pulse">Analyzing resume...</p>
    </div>

    <!-- Results -->
    <div v-if="result && result.data" class="space-y-6">
      <!-- Overall Score -->
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">Overall Match Score</h2>
        <div class="flex items-center gap-4">
          <div class="text-5xl font-bold text-blue-600">
            {{ result.data.overall_score }}
          </div>
          <div class="text-sm text-gray-500">/ 100</div>
        </div>
      </div>

      <!-- Radar Chart -->
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">Dimension Analysis</h2>
        <RadarChart :dimensions="result.data.dimensions" />
      </div>

      <!-- Candidate Info -->
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">Candidate Info</h2>
        <dl class="space-y-2 text-sm">
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">Name:</dt>
            <dd class="text-gray-800">{{ result.data.candidate_info.name || '-' }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">Phone:</dt>
            <dd class="text-gray-800">{{ result.data.candidate_info.phone || '-' }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">Email:</dt>
            <dd class="text-gray-800">{{ result.data.candidate_info.email || '-' }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">Address:</dt>
            <dd class="text-gray-800">{{ result.data.candidate_info.address || '-' }}</dd>
          </div>
        </dl>
      </div>
    </div>
  </div>
</template>
