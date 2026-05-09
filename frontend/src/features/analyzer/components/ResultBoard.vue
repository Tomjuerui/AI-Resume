<script setup lang="ts">
import { useAnalyzer } from '../composables/useAnalyzer'
import RadarChart from './RadarChart.vue'

const { result, loading, asyncStatus, partialResult, error } = useAnalyzer()

function scoreColor(s: number) {
  if (s >= 80) return 'text-green-600'
  if (s >= 60) return 'text-blue-600'
  return 'text-orange-500'
}

function scoreLabel(s: number) {
  if (s >= 80) return 'Excellent Match'
  if (s >= 60) return 'Good Match'
  return 'Needs Review'
}
</script>

<template>
  <div>
    <!-- Empty State -->
    <div
      v-if="asyncStatus === 'idle'"
      class="flex flex-col items-center justify-center h-full text-gray-400"
    >
      <div class="text-6xl mb-4">&#x1F4C4;</div>
      <p class="text-lg">Upload a resume and paste a JD to get started</p>
    </div>

    <!-- Loading Skeleton -->
    <div v-if="loading" class="space-y-6 animate-pulse">
      <div class="bg-blue-50 rounded-xl p-6 shadow-sm border border-blue-200">
        <div class="h-5 bg-blue-200 rounded w-1/3 mb-3" />
        <div class="h-4 bg-blue-100 rounded w-full mb-2" />
        <div class="h-4 bg-blue-100 rounded w-3/4" />
      </div>
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <div class="h-5 bg-gray-200 rounded w-1/4 mb-4" />
        <div class="flex items-center gap-6">
          <div class="w-28 h-28 rounded-full bg-gray-200" />
          <div class="space-y-2">
            <div class="h-4 bg-gray-200 rounded w-24" />
            <div class="h-6 bg-gray-200 rounded w-32" />
          </div>
        </div>
      </div>
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <div class="h-5 bg-gray-200 rounded w-1/3 mb-4" />
        <div class="h-80 bg-gray-100 rounded" />
      </div>
    </div>

    <!-- Polling: Phase 1 results visible, Phase 2 in progress -->
    <div v-if="asyncStatus === 'polling' && partialResult" class="space-y-6">

      <!-- Phase 1 Summary Banner -->
      <div class="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl p-6 shadow-sm text-white">
        <h2 class="text-lg font-semibold mb-2">AI Analysis Summary</h2>
        <p class="text-sm text-blue-100 leading-relaxed">{{ partialResult.summary }}</p>
      </div>

      <!-- Phase 1 Overall Score (Rule-based) -->
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-800">Overall Match Score</h2>
          <span class="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded-full">Initial</span>
        </div>
        <div class="flex items-center gap-6">
          <svg viewBox="0 0 120 120" class="w-28 h-28 flex-shrink-0">
            <circle cx="60" cy="60" r="50" fill="none" stroke="#e5e7eb" stroke-width="10" />
            <circle
              cx="60" cy="60" r="50"
              fill="none"
              :stroke="partialResult.overall_score >= 60 ? '#3b82f6' : '#f97316'"
              stroke-width="10"
              :stroke-dasharray="2 * Math.PI * 50"
              :stroke-dashoffset="2 * Math.PI * 50 * (1 - partialResult.overall_score / 100)"
              stroke-linecap="round"
              transform="rotate(-90 60 60)"
            />
            <text
              x="60" y="65" text-anchor="middle"
              class="text-2xl font-bold"
              :fill="partialResult.overall_score >= 60 ? '#2563eb' : '#ea580c'"
            >
              {{ partialResult.overall_score }}
            </text>
          </svg>
          <div>
            <div class="text-sm text-gray-500 mb-1">Rule-based Rating</div>
            <div class="text-lg font-semibold" :class="scoreColor(partialResult.overall_score)">
              {{ scoreLabel(partialResult.overall_score) }}
            </div>
            <div class="text-xs text-gray-400 mt-1">
              {{ partialResult.candidate_info.name || 'Candidate' }}
            </div>
          </div>
        </div>
      </div>

      <!-- Phase 1 Dimensions -->
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">Dimension Analysis (Initial)</h2>
        <RadarChart :dimensions="partialResult.dimensions" />
        <div class="mt-4 space-y-3">
          <div
            v-for="dim in partialResult.dimensions"
            :key="dim.name"
            class="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
          >
            <div class="flex-shrink-0 w-12 text-center">
              <div class="text-lg font-bold" :class="scoreColor(dim.score)">
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

      <!-- AI Deep Analysis Progress -->
      <div class="bg-white rounded-xl p-6 shadow-sm border border-blue-200">
        <div class="flex items-center gap-3">
          <div class="flex-shrink-0 relative w-8 h-8">
            <div class="absolute inset-0 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <div class="absolute inset-1 border border-blue-300 rounded-full opacity-50" />
          </div>
          <div class="flex-1">
            <h3 class="text-sm font-medium text-blue-700">AI Deep Analysis in progress...</h3>
            <p class="text-xs text-blue-400 mt-0.5">Semantic scoring and profile extraction running in background</p>
          </div>
        </div>
        <div class="mt-4 w-full bg-blue-100 rounded-full h-1 overflow-hidden">
          <div class="bg-blue-500 h-full rounded-full animate-pulse" style="width: 60%" />
        </div>
      </div>

      <!-- Phase 1 Missing Skills -->
      <div
        v-if="partialResult.missing_skills && partialResult.missing_skills.length > 0"
        class="bg-white rounded-xl p-6 shadow-sm border border-orange-200"
      >
        <h2 class="text-lg font-semibold text-orange-700 mb-3">Missing Skills (Initial)</h2>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="skill in partialResult.missing_skills"
            :key="skill"
            class="px-3 py-1 bg-orange-50 text-orange-700 text-sm rounded-full border border-orange-200"
          >
            {{ skill }}
          </span>
        </div>
      </div>

      <!-- Phase 1 Risk Tips -->
      <div
        v-if="partialResult.risk_tips && partialResult.risk_tips.length > 0"
        class="bg-white rounded-xl p-6 shadow-sm border border-red-200"
      >
        <h2 class="text-lg font-semibold text-red-700 mb-3">Risk Alerts (Initial)</h2>
        <ul class="space-y-2">
          <li
            v-for="(tip, idx) in partialResult.risk_tips"
            :key="idx"
            class="flex items-start gap-2 text-sm text-red-600"
          >
            <span class="flex-shrink-0 mt-0.5">&#x26A0;</span>
            <span>{{ tip }}</span>
          </li>
        </ul>
      </div>

      <!-- Candidate Info (Phase 1) -->
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">Candidate Info</h2>
        <dl class="grid grid-cols-2 gap-3 text-sm">
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">Name:</dt>
            <dd class="text-gray-800">{{ partialResult.candidate_info.name || '-' }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">Phone:</dt>
            <dd class="text-gray-800">{{ partialResult.candidate_info.phone || '-' }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">Email:</dt>
            <dd class="text-gray-800">{{ partialResult.candidate_info.email || '-' }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">Address:</dt>
            <dd class="text-gray-800">{{ partialResult.candidate_info.address || '-' }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">Education:</dt>
            <dd class="text-gray-800">
              {{ partialResult.candidate_info.highest_degree || '-' }}
              {{ partialResult.candidate_info.major }}
            </dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">School:</dt>
            <dd class="text-gray-800">{{ partialResult.candidate_info.school || '-' }}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-gray-500 w-20">Experience:</dt>
            <dd class="text-gray-800">{{ partialResult.candidate_info.years_of_experience || '-' }}</dd>
          </div>
        </dl>
      </div>
    </div>

    <!-- Async Failed: Phase 1 results still visible with error banner -->
    <div v-if="asyncStatus === 'failed' && partialResult" class="space-y-6">
      <div class="bg-yellow-50 rounded-xl p-4 border border-yellow-200">
        <p class="text-sm text-yellow-700">
          AI deep analysis was not completed. Showing rule-based results below.
          <span v-if="error" class="block mt-1 text-yellow-600">{{ error }}</span>
        </p>
      </div>

      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">Overall Match Score</h2>
        <div class="flex items-center gap-6">
          <svg viewBox="0 0 120 120" class="w-28 h-28 flex-shrink-0">
            <circle cx="60" cy="60" r="50" fill="none" stroke="#e5e7eb" stroke-width="10" />
            <circle
              cx="60" cy="60" r="50" fill="none"
              :stroke="partialResult.overall_score >= 60 ? '#3b82f6' : '#f97316'"
              stroke-width="10"
              :stroke-dasharray="2 * Math.PI * 50"
              :stroke-dashoffset="2 * Math.PI * 50 * (1 - partialResult.overall_score / 100)"
              stroke-linecap="round" transform="rotate(-90 60 60)"
            />
            <text x="60" y="65" text-anchor="middle" class="text-2xl font-bold"
              :fill="partialResult.overall_score >= 60 ? '#2563eb' : '#ea580c'">
              {{ partialResult.overall_score }}
            </text>
          </svg>
          <div>
            <div class="text-sm text-gray-500 mb-1">Rule-based Rating</div>
            <div class="text-lg font-semibold" :class="scoreColor(partialResult.overall_score)">
              {{ scoreLabel(partialResult.overall_score) }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="partialResult.dimensions.length > 0" class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h2 class="text-lg font-semibold text-gray-800 mb-4">Dimension Analysis</h2>
        <RadarChart :dimensions="partialResult.dimensions" />
        <div class="mt-4 space-y-3">
          <div v-for="dim in partialResult.dimensions" :key="dim.name"
            class="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            <div class="flex-shrink-0 w-12 text-center">
              <div class="text-lg font-bold" :class="scoreColor(dim.score)">{{ dim.score }}</div>
              <div class="text-xs text-gray-400">/100</div>
            </div>
            <div class="min-w-0">
              <div class="text-sm font-medium text-gray-700">{{ dim.name }}</div>
              <div class="text-xs text-gray-500 mt-1">{{ dim.reason }}</div>
            </div>
          </div>
        </div>
      </div>
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
        <div class="flex items-center gap-6">
          <!-- Circular Progress -->
          <svg viewBox="0 0 120 120" class="w-28 h-28 flex-shrink-0">
            <circle cx="60" cy="60" r="50" fill="none" stroke="#e5e7eb" stroke-width="10" />
            <circle
              cx="60" cy="60" r="50"
              fill="none"
              :stroke="result.data.overall_score >= 60 ? '#3b82f6' : '#f97316'"
              stroke-width="10"
              :stroke-dasharray="2 * Math.PI * 50"
              :stroke-dashoffset="2 * Math.PI * 50 * (1 - result.data.overall_score / 100)"
              stroke-linecap="round"
              transform="rotate(-90 60 60)"
              class="transition-all duration-1000 ease-out"
            />
            <text
              x="60" y="65" text-anchor="middle"
              class="text-2xl font-bold"
              :fill="result.data.overall_score >= 60 ? '#2563eb' : '#ea580c'"
            >
              {{ result.data.overall_score }}
            </text>
          </svg>
          <div>
            <div class="text-sm text-gray-500 mb-1">Match Rating</div>
            <div
              class="text-lg font-semibold"
              :class="result.data.overall_score >= 80 ? 'text-green-600' : result.data.overall_score >= 60 ? 'text-blue-600' : 'text-orange-500'"
            >
              {{ result.data.overall_score >= 80 ? 'Excellent Match' : result.data.overall_score >= 60 ? 'Good Match' : 'Needs Review' }}
            </div>
            <div class="text-xs text-gray-400 mt-1">
              {{ result.data.candidate_info.name || 'Candidate' }}
            </div>
          </div>
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

      <!-- Raw JSON Accordion -->
      <details
        v-if="result.data.raw_json && Object.keys(result.data.raw_json).length > 0"
        class="bg-gray-50 rounded-xl border border-gray-200 group"
      >
        <summary class="cursor-pointer px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700 select-none">
          Raw JSON (AI Extraction Output)
        </summary>
        <pre class="px-6 pb-4 text-xs text-gray-600 overflow-x-auto leading-relaxed">{{ JSON.stringify(result.data.raw_json, null, 2) }}</pre>
      </details>

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
