<script setup lang="ts">
import { useAnalyzer } from '../composables/useAnalyzer'
import RadarChart from './RadarChart.vue'

const { result, loading } = useAnalyzer()
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

      <!-- Summary -->
      <div
        v-if="result.data.summary"
        class="bg-blue-50 rounded-xl p-6 shadow-sm border border-blue-200"
      >
        <h2 class="text-lg font-semibold text-blue-800 mb-2">AI Analysis Summary</h2>
        <p class="text-sm text-blue-700 leading-relaxed">{{ result.data.summary }}</p>
      </div>

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

      <!-- Radar Chart + Dimension Details -->
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">Dimension Analysis</h2>
        <RadarChart :dimensions="result.data.dimensions" />
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

      <!-- Missing Skills -->
      <div
        v-if="result.data.missing_skills && result.data.missing_skills.length > 0"
        class="bg-white rounded-xl p-6 shadow-sm border border-orange-200"
      >
        <h2 class="text-lg font-semibold text-orange-700 mb-3">Missing Skills</h2>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="skill in result.data.missing_skills"
            :key="skill"
            class="px-3 py-1 bg-orange-50 text-orange-700 text-sm rounded-full border border-orange-200"
          >
            {{ skill }}
          </span>
        </div>
      </div>

      <!-- Risk Tips -->
      <div
        v-if="result.data.risk_tips && result.data.risk_tips.length > 0"
        class="bg-white rounded-xl p-6 shadow-sm border border-red-200"
      >
        <h2 class="text-lg font-semibold text-red-700 mb-3">Risk Alerts</h2>
        <ul class="space-y-2">
          <li
            v-for="(tip, idx) in result.data.risk_tips"
            :key="idx"
            class="flex items-start gap-2 text-sm text-red-600"
          >
            <span class="flex-shrink-0 mt-0.5">&#x26A0;</span>
            <span>{{ tip }}</span>
          </li>
        </ul>
      </div>

      <!-- Deep Extraction -->
      <div
        v-if="result.data.deep_extraction"
        class="bg-white rounded-xl p-6 shadow-sm border border-gray-100"
      >
        <h2 class="text-lg font-semibold text-gray-800 mb-4">Deep Profile Extraction</h2>

        <!-- Skills -->
        <div v-if="result.data.deep_extraction.skills.length > 0" class="mb-4">
          <h3 class="text-sm font-medium text-gray-600 mb-2">Skills</h3>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="skill in result.data.deep_extraction.skills"
              :key="skill.name"
              class="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded border border-blue-200"
            >
              {{ skill.name }}
              <span class="text-blue-400">({{ skill.level }})</span>
            </span>
          </div>
        </div>

        <!-- Work Experience -->
        <div v-if="result.data.deep_extraction.work_experience.length > 0" class="mb-4">
          <h3 class="text-sm font-medium text-gray-600 mb-2">Work Experience</h3>
          <div class="space-y-3">
            <div
              v-for="(exp, idx) in result.data.deep_extraction.work_experience"
              :key="idx"
              class="p-3 bg-gray-50 rounded-lg"
            >
              <div class="flex justify-between items-start">
                <div>
                  <span class="text-sm font-medium text-gray-800">{{ exp.role }}</span>
                  <span class="text-sm text-gray-500 ml-2">@ {{ exp.company }}</span>
                </div>
                <span class="text-xs text-gray-400">{{ exp.duration }}</span>
              </div>
              <ul v-if="exp.highlights.length > 0" class="mt-2 space-y-1">
                <li
                  v-for="(h, i) in exp.highlights"
                  :key="i"
                  class="text-xs text-gray-600 flex items-start gap-1"
                >
                  <span class="text-gray-400 mt-0.5">-</span>
                  <span>{{ h }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Projects -->
        <div v-if="result.data.deep_extraction.projects.length > 0" class="mb-4">
          <h3 class="text-sm font-medium text-gray-600 mb-2">Projects</h3>
          <div class="space-y-2">
            <div
              v-for="(proj, idx) in result.data.deep_extraction.projects"
              :key="idx"
              class="p-3 bg-gray-50 rounded-lg"
            >
              <div class="text-sm font-medium text-gray-800">{{ proj.name }}</div>
              <div class="text-xs text-gray-500 mt-1">{{ proj.description }}</div>
              <div v-if="proj.tech_stack.length > 0" class="flex flex-wrap gap-1 mt-2">
                <span
                  v-for="tech in proj.tech_stack"
                  :key="tech"
                  class="px-2 py-0.5 bg-gray-200 text-gray-600 text-xs rounded"
                >
                  {{ tech }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Education Summary -->
        <div v-if="result.data.deep_extraction.school || result.data.deep_extraction.highest_degree" class="mb-4">
          <h3 class="text-sm font-medium text-gray-600 mb-2">Education</h3>
          <div class="text-sm text-gray-700">
            {{ result.data.deep_extraction.highest_degree }}
            {{ result.data.deep_extraction.major }}
            <span v-if="result.data.deep_extraction.school">@ {{ result.data.deep_extraction.school }}</span>
          </div>
        </div>

        <!-- Certificates & Languages -->
        <div class="flex gap-6">
          <div v-if="result.data.deep_extraction.certificates.length > 0">
            <h3 class="text-sm font-medium text-gray-600 mb-2">Certificates</h3>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="cert in result.data.deep_extraction.certificates"
                :key="cert"
                class="px-2 py-0.5 bg-green-50 text-green-700 text-xs rounded border border-green-200"
              >
                {{ cert }}
              </span>
            </div>
          </div>
          <div v-if="result.data.deep_extraction.languages.length > 0">
            <h3 class="text-sm font-medium text-gray-600 mb-2">Languages</h3>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="lang in result.data.deep_extraction.languages"
                :key="lang"
                class="px-2 py-0.5 bg-purple-50 text-purple-700 text-xs rounded border border-purple-200"
              >
                {{ lang }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Candidate Basic Info -->
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">Candidate Info</h2>
        <dl class="grid grid-cols-2 gap-3 text-sm">
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
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">Education:</dt>
            <dd class="text-gray-800">
              {{ result.data.candidate_info.highest_degree || '-' }}
              {{ result.data.candidate_info.major }}
            </dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">School:</dt>
            <dd class="text-gray-800">{{ result.data.candidate_info.school || '-' }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">Experience:</dt>
            <dd class="text-gray-800">{{ result.data.candidate_info.years_of_experience || '-' }}</dd>
          </div>
        </dl>
      </div>
    </div>
  </div>
</template>
