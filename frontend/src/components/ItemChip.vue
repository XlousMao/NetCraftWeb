<script setup lang="ts">
defineProps<{
  name: string
  quantity?: number | string | null
  iconUrl?: string | null
  type?: string
}>()
</script>

<template>
  <div class="item-chip" :class="type">
    <div class="chip-img">
      <img v-if="iconUrl" :src="iconUrl" :alt="name" />
      <span v-else class="chip-ph">{{ (name || '?').slice(0, 1) }}</span>
    </div>
    <span class="chip-name">{{ name }}</span>
    <span v-if="quantity != null && quantity !== ''" class="chip-qty">×{{ quantity }}</span>
  </div>
</template>

<style scoped>
.item-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px 3px 3px;
  border: 1px solid #eef0f3;
  border-radius: 18px;
  background: #fafbfc;
  margin: 2px;
  font-size: 12px;
}
.chip-img {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border-radius: 50%;
  overflow: hidden;
  background: #f2f3f5;
  display: flex;
  align-items: center;
  justify-content: center;
}
.chip-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.chip-ph {
  color: #c0c4cc;
  font-weight: 600;
  font-size: 12px;
}
.chip-name {
  color: #303133;
}
.chip-qty {
  color: #909399;
  font-weight: 600;
}
.item-chip.success {
  background: #f0f9eb;
  border-color: #e1f3d8;
}
.item-chip.success .chip-name {
  color: #67c23a;
}
</style>
