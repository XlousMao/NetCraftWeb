<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  sub?: string
  valueClass?: string
}>()
</script>

<template>
  <div class="stat-card">
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value" :class="valueClass">{{ value }}</div>
    <div v-if="sub" class="stat-sub">{{ sub }}</div>
  </div>
</template>

<style scoped>
.stat-card {
  background: #fff;
  border-radius: 10px;
  padding: 18px;
  border: 1px solid #eef0f3;
}
.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.stat-sub {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
