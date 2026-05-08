<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import type { DimensionScore } from '../types'

const props = defineProps<{
  dimensions: DimensionScore[]
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function renderChart() {
  if (!chartRef.value) return

  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  const indicators = props.dimensions.map((d) => ({
    name: d.name,
    max: 100,
  }))

  const values = props.dimensions.map((d) => d.score)

  chart.setOption({
    radar: {
      indicator: indicators,
      shape: 'polygon',
      center: ['50%', '50%'],
      radius: '70%',
    },
    series: [
      {
        type: 'radar',
        data: [{ value: values, name: 'Match Score' }],
        areaStyle: { opacity: 0.2 },
        lineStyle: { color: '#3b82f6' },
        itemStyle: { color: '#3b82f6' },
      },
    ],
  })
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})

function handleResize() {
  chart?.resize()
}

watch(() => props.dimensions, renderChart, { deep: true })
</script>

<template>
  <div ref="chartRef" class="w-full h-[320px]" />
</template>
