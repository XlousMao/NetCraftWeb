<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ option: any; height?: string }>()
const container = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
let observer: ResizeObserver | null = null

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
  // ResizeObserver 监听容器尺寸变化：tab 从隐藏到显示、窗口缩放、侧栏折叠等
  // 都能正确触发 resize，避免隐藏容器初始化时宽度为 0 导致图表被压扁。
  if (container.value && typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => resize())
    observer.observe(container.value)
  } else {
    window.addEventListener('resize', resize)
  }
})
onBeforeUnmount(() => {
  observer?.disconnect()
  window.removeEventListener('resize', resize)
  chart?.dispose()
})

watch(() => props.option, render, { deep: true })
</script>

<template>
  <div ref="container" :style="{ width: '100%', height: height || '300px' }"></div>
</template>
