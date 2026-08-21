<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { itemApi, analysisApi } from '@/api'
import ImageUpload from '@/components/ImageUpload.vue'
import RelationGraph from '@/components/RelationGraph.vue'
import Chart from '@/components/Chart.vue'

const route = useRoute()
const itemId = Number(route.params.id)
const item = ref<any>(null)
const graph = ref<any>(null)
const activeTab = ref('overview')
const craftDecision = ref<any>(null)

const marketForm = ref({
  observation_type: 'SELL_OFFER',
  price_quantity: null as number | null,
  quantity: 1,
  seller_name: '',
  source: '',
})

const OBS_TYPE_LABEL: Record<string, string> = {
  SELL_OFFER: '出售挂单',
  BUY_ORDER: '收购订单',
  NPC_PRICE: '商人定价',
  MANUAL_ESTIMATE: '手动估值',
}

onMounted(async () => {
  await fetchItem()
  await fetchGraph()
  await fetchDecision()
})

async function fetchItem() {
  const { data } = await itemApi.get(itemId)
  item.value = data
}

async function fetchGraph() {
  const { data } = await itemApi.relationGraph(itemId, 2)
  graph.value = data
}

async function fetchDecision() {
  const { data } = await analysisApi.craftVsBuy(itemId)
  craftDecision.value = data
}

const stars = computed(() => {
  const score = item.value?.importance_score ?? 0
  return '★'.repeat(Math.min(5, Math.max(1, Math.round(score / 20 * 5))))
})

const marketChart = computed(() => {
  const hist = item.value?.price_history || []
  const byType: Record<string, any[]> = {}
  for (const p of hist) {
    ;(byType[p.observation_type] = byType[p.observation_type] || []).push([p.observed_at, p.unit_price])
  }
  const colors: Record<string, string> = {
    NPC_PRICE: '#e6a23c', SELL_OFFER: '#3b82f6', BUY_ORDER: '#67c23a', MANUAL_ESTIMATE: '#909399',
  }
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: Object.keys(byType).map((t) => OBS_TYPE_LABEL[t] || t) },
    xAxis: { type: 'time' },
    yAxis: { type: 'value', name: '价格(钻石)' },
    series: Object.keys(byType).map((t) => ({
      name: OBS_TYPE_LABEL[t] || t,
      type: 'line',
      data: byType[t],
      showSymbol: true,
      itemStyle: { color: colors[t] || '#409eff' },
    })),
  }
})

async function recordMarket() {
  if (!marketForm.value.price_quantity) {
    ElMessage.warning('请输入价格')
    return
  }
  await itemApi.recordMarket(itemId, marketForm.value)
  ElMessage.success('市场观察已记录')
  marketForm.value.price_quantity = null
  marketForm.value.seller_name = ''
  marketForm.value.source = ''
  fetchItem()
  fetchDecision()
}

function primaryImage() {
  return item.value?.images?.find((i: any) => i.is_primary) || item.value?.images?.[0]
}

function summary() {
  return item.value?.market_summary || {}
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
          </div>
          <div v-if="item.current_value" class="current-value">
            当前估值：<b>{{ item.current_value.base_currency_value }} 钻石</b>
            <span v-if="item.current_value.fiat_value != null" class="text-muted">≈ {{ item.current_value.fiat_value.toFixed(3) }} RMB</span>
          </div>
          <div class="market-summary">
            <span>价格区间 <b>{{ summary().min ?? '—' }} ~ {{ summary().max ?? '—' }}</b></span>
            <span>最高收购 <b class="buy">{{ summary().highest_buy_order ?? '—' }}</b></span>
            <span>最低出售 <b class="sell">{{ summary().lowest_sell_offer ?? '—' }}</b></span>
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

        <el-tab-pane label="市场观察" name="market">
          <div class="market-form">
            <el-select v-model="marketForm.observation_type" style="width: 130px">
              <el-option label="出售挂单" value="SELL_OFFER" />
              <el-option label="收购订单" value="BUY_ORDER" />
              <el-option label="商人定价" value="NPC_PRICE" />
              <el-option label="手动估值" value="MANUAL_ESTIMATE" />
            </el-select>
            <el-input-number v-model="marketForm.price_quantity" :min="0" placeholder="价格(钻石)" />
            <span>换</span>
            <el-input-number v-model="marketForm.quantity" :min="1" />
            <span>个</span>
            <el-input v-model="marketForm.seller_name" placeholder="卖家/地点（可选）" style="width: 150px" />
            <el-button type="primary" @click="recordMarket">记录</el-button>
          </div>
          <Chart v-if="item.price_history?.length" :option="marketChart" height="280px" />
          <el-empty v-else description="暂无价格历史" />
          <el-table :data="item.market_observations || []" size="small" style="margin-top: 8px">
            <el-table-column label="类型" width="110">
              <template #default="{ row }">{{ OBS_TYPE_LABEL[row.observation_type] || row.observation_type }}</template>
            </el-table-column>
            <el-table-column label="单价" width="100">
              <template #default="{ row }">{{ row.price_quantity }} / {{ row.quantity }}</template>
            </el-table-column>
            <el-table-column prop="seller_name" label="卖家/地点" width="120" />
            <el-table-column prop="source" label="来源" />
            <el-table-column label="时间" width="180">
              <template #default="{ row }">{{ new Date(row.observed_at).toLocaleString() }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="决策分析" name="decision">
          <div v-if="craftDecision && !craftDecision.error">
            <el-alert
              :type="craftDecision.recommendation === 'craft' ? 'success' : 'info'"
              :closable="false"
              :title="craftDecision.recommendation_text"
              style="margin-bottom: 16px"
            />
            <el-descriptions :column="2" border>
              <el-descriptions-item label="直接购买价">{{ craftDecision.buy_price }} 钻石</el-descriptions-item>
              <el-descriptions-item label="购买 RMB">{{ craftDecision.buy_fiat != null ? craftDecision.buy_fiat.toFixed(3) + ' RMB' : '—' }}</el-descriptions-item>
            </el-descriptions>
            <el-table :data="craftDecision.craft_options || []" size="small" style="margin-top: 16px">
              <el-table-column prop="recipe_name" label="配方" />
              <el-table-column prop="material_cost" label="材料成本" width="110" />
              <el-table-column prop="per_unit_cost" label="单件成本" width="110" />
              <el-table-column label="成功率" width="100">
                <template #default="{ row }">{{ (row.success_rate * 100).toFixed(0) }}%</template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-else description="暂无制作配方，只能直接购买" />
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
.current-value b {
  color: #3b82f6;
  font-size: 18px;
}
.market-summary {
  display: flex;
  gap: 20px;
  font-size: 13px;
  margin-top: 10px;
}
.market-summary b {
  color: #e6a23c;
}
.market-summary .buy {
  color: #67c23a;
}
.market-summary .sell {
  color: #f56c6c;
}
.market-form {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
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
</style>
