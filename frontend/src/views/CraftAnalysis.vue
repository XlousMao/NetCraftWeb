<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { itemApi, analysisApi, recipeApi } from '@/api'

const items = ref<any[]>([])
const recipes = ref<any[]>([])
const selectedItemId = ref<number | null>(null)
const craftDecision = ref<any>(null)
const recipeDecisions = ref<any[]>([])

onMounted(async () => {
  const [i, r] = await Promise.all([
    itemApi.list({ page_size: 100 }),
    recipeApi.list(),
  ])
  items.value = i.data.items
  recipes.value = r.data.items
})

async function onSelectItem() {
  if (!selectedItemId.value) return
  const { data } = await analysisApi.craftVsBuy(selectedItemId.value)
  craftDecision.value = data
}

async function analyzeAllRecipes() {
  const results = []
  for (const r of recipes.value) {
    try {
      const { data } = await analysisApi.recipeDecision(r.id)
      results.push(data)
    } catch {
      // 跳过
    }
  }
  results.sort((a, b) => b.profit - a.profit)
  recipeDecisions.value = results
}

function itemName(id: number) {
  return items.value.find((i) => i.id === id)?.name || `#${id}`
}

const typeLabel: Record<string, string> = { ALCHEMY: '炼金', CRAFT: '制造', SYNTHESIS: '合成' }
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 style="margin: 0">制作分析</h2>
    </div>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header><span style="font-weight: 600">买 vs 做</span></template>
      <div class="select-row">
        <el-select v-model="selectedItemId" filterable placeholder="选择目标物品" style="width: 320px" @change="onSelectItem">
          <el-option v-for="i in items" :key="i.id" :label="i.name" :value="i.id" />
        </el-select>
      </div>

      <div v-if="craftDecision && !craftDecision.error" style="margin-top: 12px">
        <el-alert
          :type="craftDecision.recommendation === 'craft' ? 'success' : 'info'"
          :closable="false"
          :title="craftDecision.recommendation_text"
        />
        <el-descriptions :column="2" border style="margin-top: 12px">
          <el-descriptions-item label="直接购买价">{{ craftDecision.buy_price }} 钻石</el-descriptions-item>
          <el-descriptions-item label="购买 RMB">{{ craftDecision.buy_fiat != null ? craftDecision.buy_fiat.toFixed(3) + ' RMB' : '—' }}</el-descriptions-item>
        </el-descriptions>
        <el-table :data="craftDecision.craft_options || []" size="small" style="margin-top: 12px">
          <el-table-column prop="recipe_name" label="配方" />
          <el-table-column prop="material_cost" label="材料成本" width="110" />
          <el-table-column prop="per_unit_cost" label="单件成本" width="110" />
          <el-table-column label="成功率" width="100">
            <template #default="{ row }">{{ (row.success_rate * 100).toFixed(0) }}%</template>
          </el-table-column>
        </el-table>
      </div>
      <el-empty v-else description="请选择一个物品查看制作 vs 购买分析" />
    </el-card>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <span style="font-weight: 600">配方利润（卖材料 vs 合成）</span>
        <el-button size="small" style="float: right" @click="analyzeAllRecipes">分析全部配方</el-button>
      </template>
      <el-table :data="recipeDecisions" size="small">
        <el-table-column prop="recipe_name" label="配方" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">{{ typeLabel[row.recipe_type] || row.recipe_type }}</template>
        </el-table-column>
        <el-table-column prop="material_value" label="材料价值" width="110" />
        <el-table-column prop="expected_output_value" label="期望产出" width="110" />
        <el-table-column label="利润" width="110">
          <template #default="{ row }">
            <span :class="row.profit >= 0 ? 'profit' : 'loss'">{{ row.profit.toLocaleString() }}</span>
          </template>
        </el-table-column>
        <el-table-column label="ROI" width="90">
          <template #default="{ row }">{{ (row.roi * 100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column label="推荐" width="140">
          <template #default="{ row }">
            <el-tag :type="row.recommendation === 'craft' ? 'success' : 'warning'" size="small">{{ row.recommendation_text }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!recipeDecisions.length" description="点击右上角分析全部配方" />
    </el-card>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
}
.select-row {
  display: flex;
  gap: 10px;
}
</style>
