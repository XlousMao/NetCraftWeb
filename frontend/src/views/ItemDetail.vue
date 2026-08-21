<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { itemApi } from '@/api'
import ImageUpload from '@/components/ImageUpload.vue'
import RelationGraph from '@/components/RelationGraph.vue'
import Chart from '@/components/Chart.vue'

const route = useRoute()
const itemId = Number(route.params.id)
const item = ref<any>(null)
const graph = ref<any>(null)
const activeTab = ref('overview')

const priceForm = ref({ price_type: 'vendor', price: null as number | null, source: '' })

onMounted(async () => {
  await fetchItem()
  await fetchGraph()
})

async function fetchItem() {
  const { data } = await itemApi.get(itemId)
  item.value = data
}

async function fetchGraph() {
  const { data } = await itemApi.relationGraph(itemId, 2)
  graph.value = data
}

const stars = computed(() => {
  const score = item.value?.importance_score ?? 0
  return '★'.repeat(Math.min(5, Math.max(1, Math.round(score / 20 * 5))))
})

const priceChart = computed(() => {
  const hist = item.value?.price_history || []
  const vendor = hist.filter((p: any) => p.price_type === 'vendor').map((p: any) => [p.observed_at, p.price])
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'time' },
    yAxis: { type: 'value', name: '价格' },
    series: [
      { name: '商人价', type: 'line', data: vendor, showSymbol: true, itemStyle: { color: '#e6a23c' } },
    ],
  }
})

async function recordPrice() {
  if (!priceForm.value.price) {
    ElMessage.warning('请输入价格')
    return
  }
  await itemApi.recordPrice(itemId, priceForm.value)
  ElMessage.success('价格已记录')
  priceForm.value.price = null
  fetchItem()
}

function primaryImage() {
  return item.value?.images?.find((i: any) => i.is_primary) || item.value?.images?.[0]
}

function priceTypeLabel(type: string): string {
  const map: Record<string, string> = { vendor: '商人', market: '市场', manual: '手动' }
  return map[type] || type
}
</script>

<template>
  <div class="page" v-if="item">
    <el-card shadow="never">
      <div class="header">
        <div class="thumb">
          <img v-if="primaryImage()" :src="'/storage/' + primaryImage().file_path" :alt="item.name" />
          <span v-else class="thumb-placeholder">{{ item.name.slice(0, 1) }}</span>
        </div>
        <div class="info">
          <h2>{{ item.name }}</h2>
          <div class="tags">
            <el-tag size="small">{{ item.category || '未分类' }}</el-tag>
            <el-tag v-for="r in item.roles || []" :key="r" size="small" type="info" effect="plain">{{ r }}</el-tag>
            <span class="stars" style="color: #f59e0b">{{ stars }}</span>
            <span class="text-muted">重要性 {{ item.importance_score }}</span>
          </div>
          <div class="prices">
            <span>商人价 <b>{{ item.vendor_buy_price ?? '—' }}</b></span>
            <span>市场价 <b>{{ item.market_price ?? '—' }}</b></span>
            <span>手动估值 <b>{{ item.manual_price ?? '—' }}</b></span>
          </div>
          <div v-if="item.current_value" class="current-value">
            当前估值：<b>{{ item.current_value.base_currency_value }} 钻石</b>
            <span v-if="item.current_value.fiat_value != null" class="text-muted">≈ {{ item.current_value.fiat_value.toFixed(3) }} RMB</span>
          </div>
        </div>
      </div>
    </el-card>

    <el-card shadow="never" style="margin-top: 16px">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="概览" name="overview">
          <p>{{ item.description || '暂无描述' }}</p>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="关联数量">{{ item.relations?.length ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="图片数量">{{ item.images?.length ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ new Date(item.created_at).toLocaleString() }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <el-tab-pane label="图片" name="images">
          <ImageUpload :item-id="itemId" @uploaded="fetchItem" />
          <div class="image-list">
            <div v-for="img in item.images" :key="img.id" class="img-item">
              <img :src="'/storage/' + img.file_path" :alt="img.image_type" />
              <el-tag v-if="img.is_primary" size="small" type="success">主图</el-tag>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="价格" name="price">
          <div class="price-form">
            <el-select v-model="priceForm.price_type" style="width: 120px">
              <el-option label="商人价" value="vendor" />
              <el-option label="市场价" value="market" />
              <el-option label="手动估值" value="manual" />
            </el-select>
            <el-input-number v-model="priceForm.price" :min="0" />
            <el-input v-model="priceForm.source" placeholder="来源（可选）" style="width: 160px" />
            <el-button type="primary" @click="recordPrice">记录价格</el-button>
          </div>
          <Chart v-if="item.price_history?.length" :option="priceChart" height="280px" />
          <el-empty v-else description="暂无价格历史" />
        </el-tab-pane>

        <el-tab-pane label="副本来源" name="dungeons">
          <el-table :data="item.relations?.filter((r: any) => r.relation_type === 'DROPS') || []" size="small">
            <el-table-column prop="source_id" label="副本ID" width="90" />
            <el-table-column prop="quantity" label="掉落数量" />
          </el-table>
          <el-empty v-if="!item.relations?.some((r: any) => r.relation_type === 'DROPS')" description="暂未被副本产出" />
        </el-tab-pane>

        <el-tab-pane label="配方" name="recipes">
          <el-table :data="item.relations?.filter((r: any) => ['CONSUMES', 'PRODUCES'].includes(r.relation_type)) || []" size="small">
            <el-table-column prop="relation_type" label="关系" width="110" />
            <el-table-column prop="source_id" label="配方ID" width="90" />
            <el-table-column prop="quantity" label="数量" />
          </el-table>
          <el-empty v-if="!item.relations?.some((r: any) => ['CONSUMES', 'PRODUCES'].includes(r.relation_type))" description="暂未被配方引用" />
        </el-tab-pane>

        <el-tab-pane label="维修消耗" name="repair">
          <el-table :data="item.relations?.filter((r: any) => r.relation_type === 'REQUIRES_REPAIR') || []" size="small">
            <el-table-column prop="source_id" label="装备ID" width="90" />
            <el-table-column prop="quantity" label="所需数量" />
          </el-table>
          <el-empty v-if="!item.relations?.some((r: any) => r.relation_type === 'REQUIRES_REPAIR')" description="暂未被装备维修消耗" />
        </el-tab-pane>

        <el-tab-pane label="历史记录" name="history">
          <el-table :data="item.price_history || []" size="small">
            <el-table-column label="类型" width="100">
              <template #default="{ row }">{{ priceTypeLabel(row.price_type) }}</template>
            </el-table-column>
            <el-table-column prop="price" label="价格" width="120" />
            <el-table-column prop="source" label="来源" />
            <el-table-column label="时间" width="200">
              <template #default="{ row }">{{ new Date(row.observed_at).toLocaleString() }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="关系图" name="graph">
          <RelationGraph v-if="graph" :nodes="graph.nodes" :edges="graph.edges" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style scoped>
.header {
  display: flex;
  gap: 24px;
  align-items: center;
}
.thumb {
  width: 120px;
  height: 120px;
  background: #f7f8fa;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.thumb img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.thumb-placeholder {
  font-size: 40px;
  color: #c0c4cc;
}
.info h2 {
  margin: 0 0 8px;
}
.tags {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}
.prices {
  display: flex;
  gap: 20px;
  font-size: 14px;
}
.prices b {
  color: #e6a23c;
}
.image-list {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.img-item {
  width: 100px;
  text-align: center;
}
.img-item img {
  width: 100%;
  height: 80px;
  object-fit: contain;
  border: 1px solid #eef0f3;
  border-radius: 6px;
}
.price-form {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
</style>
