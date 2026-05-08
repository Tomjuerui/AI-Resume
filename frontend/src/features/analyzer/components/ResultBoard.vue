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
        <!-- Dimension details -->
        <div class="mt-4 space-y-3">
          <div
            v-for="dim in result.data.dimensions"
            :key="dim.name"
            class="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
          >
            <div class="flex-shrink-0 w-12 text-center">
              <div class="text-lg font-bold" :class="dim.score >= 60 ? 'text-green-600' : 'text-orange-500'">
                {{ dim.score }}
              </div>
              <div class="text-xs text-gray-400">/100</div>
            </div>
            <div class="min-w-0">
              <div class="text-sm font-medium text-gray-700">{{ dim.name }}</div>
              <div class="text-xs text-gray-500 mt-1">{{ dim.reason }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Risk Tips -->
      <div
        v-if="result.data.risk_tips && result.data.risk_tips.length > 0"
        class="bg-white rounded-xl p-6 shadow-sm border border-orange-200"
      >
        <h2 class="text-lg font-semibold text-orange-700 mb-3">Risk Alerts</h2>
        <ul class="space-y-2">
          <li
            v-for="(tip, idx) in result.data.risk_tips"
            :key="idx"
            class="flex items-start gap-2 text-sm text-orange-600"
          >
            <span class="flex-shrink-0 mt-0.5">&#x26A0;</span>
            <span>{{ tip }}</span>
          </li>
        </ul>
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
