<script setup lang="ts">
import UploadPanel from '@/features/analyzer/components/UploadPanel.vue'
import ResultBoard from '@/features/analyzer/components/ResultBoard.vue'
</script>

<template>
  <div class="flex h-screen">
    <!-- Left: Upload & JD Input -->
    <aside class="w-[420px] flex-shrink-0 border-r border-gray-200 bg-white p-6 overflow-y-auto">
      <UploadPanel />
    </aside>

    <!-- Right: Analysis Results -->
    <main class="flex-1 p-6 overflow-y-auto bg-gray-50">
      <ResultBoard />
    </main>
  </div>
</template>
