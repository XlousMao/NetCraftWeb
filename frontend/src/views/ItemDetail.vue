<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { itemApi, analysisApi, currencyApi } from '@/api'
import ImageUpload from '@/components/ImageUpload.vue'
import RelationGraph from '@/components/RelationGraph.vue'
import Chart from '@/components/Chart.vue'

const route = useRoute()
const itemId = Number(route.params.id)
const item = ref<any>(null)
const graph = ref<any>(null)
const activeTab = ref('overview')
const craftDecision = ref<any>(null)
const craftingPlan = ref<any>(null)
const targetQuantity = ref(99)

const currency = ref<any>(null)

const marketForm = ref({
  observation_type: 'SELL_OFFER',
  quantity: 99,
  price_parts: {} as Record<string, number>,
  seller_name: '',
  location: '',
  source: '',
})

// 正在编辑的观察记录 id（null = 新增模式）
const editingObsId = ref<number | null>(null)

// 数量快捷预设（奶块常见「一组 99」「半组 33」）
const PRICE_PRESETS = [1, 33, 99]

const OBS_TYPE_LABEL: Record<string, string> = {
  SELL_OFFER: '出售挂单',
  BUY_ORDER: '收购订单',
  NPC_PRICE: '商人定价',
  MANUAL_ESTIMATE: '手动估值',
}

const RECIPE_TYPE_LABEL: Record<string, string> = {
  ALCHEMY: '炼金',
  CRAFT: '制造',
  SYNTHESIS: '合成',
}

function typeLabel(t: string) {
  return RECIPE_TYPE_LABEL[t] || t
}

onMounted(async () => {
  await fetchItem()
  await fetchGraph()
  await fetchDecision()
  await fetchCurrency()
  await fetchCraftingPlan()
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

async function fetchCraftingPlan() {
  const { data } = await analysisApi.craftingPlan(itemId, targetQuantity.value)
  craftingPlan.value = data
}

function onCraftingQuantityChange() {
  fetchCraftingPlan()
}

async function fetchCurrency() {
  try {
    const { data } = await currencyApi.summary()
    currency.value = data
    const parts: Record<string, number> = {}
    for (const d of data.denominations || []) {
      parts[d.item_id] = 0
    }
    marketForm.value.price_parts = parts
  } catch {
    /* 货币体系未配置时降级为单一钻石 */
  }
}

// 货币面额（按基础价值升序：钻石 → 钻石块 → 钻石结晶）
const denominations = computed(() => {
  const ds = currency.value?.denominations || []
  if (ds.length === 0) {
    return [{ item_id: 0, item_name: '钻石', base_value: 1, is_base: true }]
  }
  return [...ds].sort((a: any, b: any) => a.base_value - b.base_value)
})

// 换算后的总价（钻石）
const totalDiamond = computed(() => {
  let t = 0
  for (const d of denominations.value) {
    t += (marketForm.value.price_parts[d.item_id] || 0) * d.base_value
  }
  return Math.round(t * 10000) / 10000
})

// 总价对应的 RMB 估值（基于当前基础货币汇率）
const totalRmb = computed(() => {
  const rate = currency.value?.rmb_rate
  if (rate == null) return null
  return totalDiamond.value * rate
})

// 自制最低单件成本（各配方中 per_unit_cost 最小值）
const minCraftCost = computed(() => {
  const opts = craftDecision.value?.craft_options || []
  if (!opts.length) return null
  return Math.min(...opts.map((o: any) => o.per_unit_cost))
})

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

// 把总钻石数贪心分解回各面额（编辑回填用）
function splitToDenominations(total: number): Record<string, number> {
  const parts: Record<string, number> = {}
  const sorted = [...denominations.value].sort((a: any, b: any) => b.base_value - a.base_value)
  let remaining = total
  for (const d of sorted) {
    if (d.base_value <= 0) continue
    const count = Math.floor(remaining / d.base_value + 1e-9)
    parts[d.item_id] = count
    remaining = Math.round((remaining - count * d.base_value) * 10000) / 10000
  }
  if (remaining > 0) {
    const min = sorted[sorted.length - 1]
    parts[min.item_id] = (parts[min.item_id] || 0) + remaining / min.base_value
  }
  return parts
}

function resetMarketForm() {
  editingObsId.value = null
  marketForm.value.observation_type = 'SELL_OFFER'
  marketForm.value.quantity = 99
  marketForm.value.seller_name = ''
  marketForm.value.location = ''
  marketForm.value.source = ''
  const parts: Record<string, number> = {}
  for (const d of denominations.value) parts[d.item_id] = 0
  marketForm.value.price_parts = parts
}

function openEditObs(row: any) {
  editingObsId.value = row.id
  marketForm.value.observation_type = row.observation_type
  marketForm.value.quantity = row.quantity
  marketForm.value.seller_name = row.seller_name || ''
  marketForm.value.location = row.location || ''
  marketForm.value.source = row.source || ''
  marketForm.value.price_parts = splitToDenominations(row.price_quantity)
}

function cancelEdit() {
  resetMarketForm()
}

async function removeObs(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定删除这条「${OBS_TYPE_LABEL[row.observation_type] || row.observation_type}」记录吗？`,
      '删除确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  await itemApi.removeMarket(itemId, row.id)
  ElMessage.success('已删除')
  if (editingObsId.value === row.id) resetMarketForm()
  fetchItem()
  fetchDecision()
}

async function saveMarket() {
  if (!marketForm.value.quantity || marketForm.value.quantity <= 0) {
    ElMessage.warning('请输入数量')
    return
  }
  if (totalDiamond.value <= 0) {
    ElMessage.warning('请填写价格（钻石 / 钻石块 / 钻石结晶至少一项 > 0）')
    return
  }
  const baseId = currency.value?.system?.base_currency_item_id ?? null
  const payload = {
    observation_type: marketForm.value.observation_type,
    quantity: marketForm.value.quantity,
    price_item_id: baseId,
    price_quantity: totalDiamond.value,
    seller_name: marketForm.value.seller_name,
    location: marketForm.value.location,
    source: marketForm.value.source,
  }
  if (editingObsId.value) {
    await itemApi.updateMarket(itemId, editingObsId.value, payload)
    ElMessage.success('市场观察已更新')
  } else {
    await itemApi.recordMarket(itemId, payload)
    ElMessage.success('市场观察已记录')
  }
  resetMarketForm()
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
          <div v-if="craftDecision && !craftDecision.error && craftDecision.craft_options?.length" class="craft-compare">
            <span class="cc-label">自制 vs 购买</span>
            <span>直接购买 <b>{{ craftDecision.buy_price }} 钻石</b></span>
            <span>自制最低 <b>{{ minCraftCost != null ? minCraftCost.toLocaleString() : '—' }} 钻石</b></span>
            <el-tag :type="craftDecision.recommendation === 'craft' ? 'success' : 'warning'" size="small">{{ craftDecision.recommendation_text }}</el-tag>
            <el-button size="small" text type="primary" @click="activeTab = 'decision'">查看详情</el-button>
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
            <el-radio-group v-model="marketForm.observation_type">
              <el-radio-button value="SELL_OFFER">出售挂单</el-radio-button>
              <el-radio-button value="BUY_ORDER">收购订单</el-radio-button>
              <el-radio-button value="NPC_PRICE">商人定价</el-radio-button>
              <el-radio-button value="MANUAL_ESTIMATE">手动估值</el-radio-button>
            </el-radio-group>
          </div>
          <div class="market-form">
            <span class="lbl">数量</span>
            <el-input-number v-model="marketForm.quantity" :min="1" :step="1" controls-position="right" />
            <el-tag
              v-for="p in PRICE_PRESETS"
              :key="p"
              class="preset"
              :type="marketForm.quantity === p ? 'primary' : 'info'"
              effect="plain"
              @click="marketForm.quantity = p"
            >{{ p }}</el-tag>
            <span class="lbl">个</span>
          </div>
          <div class="market-form">
            <span class="lbl">价格</span>
            <template v-for="d in denominations" :key="d.item_id">
              <el-input-number
                v-model="marketForm.price_parts[d.item_id]"
                :min="0"
                :step="1"
                controls-position="right"
                style="width: 110px"
              />
              <span class="unit">{{ d.item_name }}</span>
            </template>
            <span class="total">= {{ totalDiamond }} 钻石</span>
            <span v-if="totalRmb != null" class="rmb">≈ {{ totalRmb.toFixed(3) }} RMB</span>
          </div>
          <div class="market-form">
            <el-input v-model="marketForm.seller_name" placeholder="卖家（可选）" style="width: 150px" />
            <el-input v-model="marketForm.location" placeholder="地点（可选）" style="width: 150px" />
            <el-input v-model="marketForm.source" placeholder="来源（可选）" style="width: 140px" />
            <el-tag v-if="editingObsId" type="warning" effect="plain">正在编辑记录 #{{ editingObsId }}</el-tag>
            <el-button type="primary" @click="saveMarket">{{ editingObsId ? '保存修改' : '记录' }}</el-button>
            <el-button v-if="editingObsId" @click="cancelEdit">取消</el-button>
          </div>
          <Chart v-if="item.price_history?.length" :option="marketChart" height="280px" />
          <el-empty v-else description="暂无价格历史" />
          <el-table :data="item.market_observations || []" size="small" style="margin-top: 8px">
            <el-table-column label="类型" width="110">
              <template #default="{ row }">{{ OBS_TYPE_LABEL[row.observation_type] || row.observation_type }}</template>
            </el-table-column>
            <el-table-column label="总价(钻石)" width="110">
              <template #default="{ row }">{{ row.price_quantity }}</template>
            </el-table-column>
            <el-table-column label="RMB(当时)" width="110">
              <template #default="{ row }">{{ row.fiat_value != null ? '≈ ' + row.fiat_value.toFixed(3) : '—' }}</template>
            </el-table-column>
            <el-table-column label="单价(钻石/个)" width="120">
              <template #default="{ row }">{{ (row.price_quantity / row.quantity).toFixed(4) }}</template>
            </el-table-column>
            <el-table-column prop="seller_name" label="卖家" width="100" />
            <el-table-column prop="location" label="地点" width="110" />
            <el-table-column prop="source" label="来源" />
            <el-table-column label="时间" width="180">
              <template #default="{ row }">{{ new Date(row.observed_at).toLocaleString() }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text type="primary" @click="openEditObs(row)">编辑</el-button>
                <el-button size="small" text type="danger" @click="removeObs(row)">删除</el-button>
              </template>
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

        <el-tab-pane label="合成表" name="crafting">
          <div v-if="craftingPlan && !craftingPlan.error">
            <div class="crafting-toolbar">
              <span class="lbl">制作数量</span>
              <el-input-number v-model="targetQuantity" :min="1" :max="100000" @change="onCraftingQuantityChange" />
              <el-tag
                v-for="p in PRICE_PRESETS"
                :key="p"
                class="preset"
                :type="targetQuantity === p ? 'primary' : 'info'"
                effect="plain"
                @click="targetQuantity = p; fetchCraftingPlan()"
              >{{ p }}</el-tag>
              <span class="lbl">个</span>
            </div>
            <el-alert
              :type="craftingPlan.recommendation === 'craft' ? 'success' : 'info'"
              :closable="false"
              :title="craftingPlan.recommendation_text"
              style="margin: 12px 0"
            />
            <el-descriptions :column="2" border>
              <el-descriptions-item label="直接购买">
                {{ craftingPlan.buy_price }} 钻石/个
                <span v-if="craftingPlan.buy_location" class="text-muted">@{{ craftingPlan.buy_location }}</span>
                · 共 <b>{{ craftingPlan.buy_total }}</b> 钻石
              </el-descriptions-item>
              <el-descriptions-item label="自制最低成本">
                {{ craftingPlan.recipes?.length ? craftingPlan.recipes[0].total_material_cost : '—' }} 钻石
              </el-descriptions-item>
            </el-descriptions>

            <div v-for="r in craftingPlan.recipes" :key="r.recipe_id" class="craft-recipe">
              <div class="cr-head">
                <b>{{ r.recipe_name }}</b>
                <el-tag size="small" type="info" effect="plain">{{ typeLabel(r.recipe_type) }}</el-tag>
                <span class="text-muted">产出 {{ r.output_quantity }}/次</span>
                <span v-if="r.success_rate < 1" class="text-muted">成功率 {{ (r.success_rate * 100).toFixed(0) }}%</span>
                <span class="text-muted">需合成 {{ r.craft_times }} 次</span>
                <b class="cr-cost">{{ r.total_material_cost }} 钻石</b>
              </div>
              <el-table :data="r.materials" size="small" style="margin-top: 8px">
                <el-table-column label="材料" min-width="160">
                  <template #default="{ row }">
                    <div class="mat-name">
                      <img v-if="row.icon_url" :src="row.icon_url" class="mat-icon" />
                      <span v-else class="mat-ph">{{ (row.item_name || '?').slice(0, 1) }}</span>
                      <span>{{ row.item_name }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="per_craft" label="单次" width="70" />
                <el-table-column prop="total_required" label="总需求" width="80" />
                <el-table-column label="最低价" width="110">
                  <template #default="{ row }">{{ row.best_price }} 钻石</template>
                </el-table-column>
                <el-table-column label="购买地点" width="180">
                  <template #default="{ row }">
                    <el-tooltip v-if="row.locations?.length" placement="top">
                      <template #content>
                        <div v-for="loc in row.locations" :key="loc.location">
                          {{ loc.location }}：{{ loc.price }} 钻石（{{ new Date(loc.observed_at).toLocaleDateString() }}）
                        </div>
                      </template>
                      <span class="loc-best">📍 {{ row.best_location }}</span>
                    </el-tooltip>
                    <span v-else class="text-muted">无出售挂单</span>
                  </template>
                </el-table-column>
                <el-table-column label="总成本" width="110">
                  <template #default="{ row }">{{ row.total_cost }} 钻石</template>
                </el-table-column>
              </el-table>
            </div>
          </div>
          <el-empty v-else description="该物品暂无可制作配方" />
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
.craft-compare {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 8px;
  font-size: 13px;
}
.craft-compare .cc-label {
  font-weight: 600;
  color: #303133;
}
.craft-compare b {
  color: #3b82f6;
}
.market-form {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.market-form .lbl {
  color: #606266;
  font-size: 13px;
}
.market-form .unit {
  color: #909399;
  font-size: 13px;
  margin-right: 6px;
}
.market-form .total {
  color: #e6a23c;
  font-weight: 600;
  font-size: 14px;
  margin-left: 4px;
}
.market-form .rmb {
  color: #67c23a;
  font-size: 13px;
}
.market-form .preset {
  cursor: pointer;
  user-select: none;
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
.crafting-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}
.crafting-toolbar .preset {
  cursor: pointer;
  user-select: none;
}
.craft-recipe {
  margin-top: 20px;
  padding: 12px;
  border: 1px solid #eef0f3;
  border-radius: 8px;
}
.cr-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.cr-cost {
  margin-left: auto;
  color: #e6a23c;
}
.mat-name {
  display: flex;
  align-items: center;
  gap: 6px;
}
.mat-icon {
  width: 22px;
  height: 22px;
  object-fit: contain;
  border-radius: 4px;
  background: #f5f6f7;
}
.mat-ph {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  background: #f5f6f7;
  color: #c0c4cc;
  font-size: 12px;
  font-weight: 600;
}
.loc-best {
  color: #67c23a;
  font-weight: 600;
  cursor: pointer;
}
</style>
