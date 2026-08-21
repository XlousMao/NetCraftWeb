<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ option: any; height?: string }>()
const container = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function render() {
  if (!container.value) return
  if (!chart) chart = echarts.init(container.value)
  chart.setOption(props.option, true)
}

function resize() {
  chart?.resize()
}

onMounted(() => {
  render()
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
})

watch(() => props.option, render, { deep: true })
</script>

<template>
  <div ref="container" :style="{ width: '100%', height: height || '300px' }"></div>
</template>
