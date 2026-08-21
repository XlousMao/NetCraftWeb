<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { Item } from '@/types'

const props = defineProps<{ item: Item }>()
const emit = defineEmits<{ edit: [item: Item]; remove: [item: Item] }>()
const router = useRouter()

const importance = computed(() => Math.round((props.item.importance_score / 20) * 5))
const stars = computed(() => '★'.repeat(Math.min(5, Math.max(1, importance.value))))

function goDetail() {
  router.push(`/items/${props.item.id}`)
}

function onEdit(e: Event) {
  e.stopPropagation()
  emit('edit', props.item)
}

function onRemove(e: Event) {
  e.stopPropagation()
  emit('remove', props.item)
}
</script>

<template>
  <div class="item-card" @click="goDetail">
    <div class="thumb">
      <span v-if="!item.icon_url" class="thumb-placeholder">{{ item.name.slice(0, 1) }}</span>
      <img v-else :src="item.icon_url" :alt="item.name" />
      <div class="actions">
        <el-button size="small" circle @click="onEdit">✎</el-button>
        <el-button size="small" circle type="danger" @click="onRemove">×</el-button>
      </div>
    </div>
    <div class="body">
      <div class="name">{{ item.name }}</div>
      <div class="category">{{ item.category || '未分类' }}</div>
      <div class="prices">
        <span class="vendor">商人 {{ item.vendor_buy_price ?? '—' }}</span>
        <span class="market">市场 {{ item.market_price ?? '—' }}</span>
      </div>
      <div class="meta">
        <span>关联 {{ item.relation_count }}</span>
        <span class="stars">{{ stars }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.item-card {
  position: relative;
  background: #fff;
  border: 1px solid #eef0f3;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.item-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}
.thumb {
  position: relative;
  height: 120px;
  background: #f7f8fa;
  display: flex;
  align-items: center;
  justify-content: center;
}
.thumb img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.thumb-placeholder {
  font-size: 40px;
  color: #c0c4cc;
  font-weight: 700;
}
.actions {
  position: absolute;
  top: 6px;
  right: 6px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}
.item-card:hover .actions {
  opacity: 1;
}
.body {
  padding: 12px;
}
.name {
  font-weight: 600;
  font-size: 15px;
}
.category {
  font-size: 12px;
  color: #909399;
  margin: 4px 0;
}
.prices {
  display: flex;
  gap: 10px;
  font-size: 12px;
  margin: 4px 0;
}
.vendor {
  color: #e6a23c;
}
.market {
  color: #3b82f6;
}
.meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}
.stars {
  color: #f59e0b;
}
</style>
