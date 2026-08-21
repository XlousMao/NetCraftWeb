<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { currencyApi } from '@/api'

const summary = ref<any>(null)
const fiatList = ref<any[]>([])
const convertForm = ref({ amount: 1, from_item_id: null as number | null, to_item_id: null as number | null })
const convertResult = ref<number | null>(null)

const fiatForm = ref({
  currency_item_id: null as number | null,
  quantity: 99,
  fiat_amount: 27.1,
  source: '',
})

async function fetch() {
  const [s, f] = await Promise.all([currencyApi.summary(), currencyApi.listFiat()])
  summary.value = s.data
  fiatList.value = f.data
}

onMounted(fetch)

async function doConvert() {
  if (!convertForm.value.from_item_id || !convertForm.value.to_item_id) {
    ElMessage.warning('请选择面额')
    return
  }
  const { data } = await currencyApi.convert(convertForm.value)
  convertResult.value = data.amount
}

async function recordFiat() {
  if (!fiatForm.value.currency_item_id) {
    ElMessage.warning('请选择货币物品')
    return
  }
  await currencyApi.recordFiat({
    ...fiatForm.value,
    fiat_currency: 'CNY',
  })
  ElMessage.success('RMB 观察已记录')
  fiatForm.value = { currency_item_id: null, quantity: 99, fiat_amount: 27.1, source: '' }
  fetch()
}
</script>

<template>
  <div class="page">
    <h2 style="margin-top: 0">货币体系</h2>

    <el-card shadow="never" style="margin-bottom: 16px" v-if="summary">
      <template #header>
        <span style="font-weight: 600">{{ summary.system?.name }}</span>
        <el-tag style="margin-left: 8px" type="success">基础货币：{{ summary.base_currency }}</el-tag>
        <el-tag style="margin-left: 8px" type="info">1 钻石 ≈ {{ summary.rmb_rate?.toFixed(5) }} RMB</el-tag>
      </template>

      <h4>货币面额</h4>
      <el-table :data="summary.denominations" size="small" border>
        <el-table-column prop="item_name" label="面额" />
        <el-table-column prop="base_value" label="钻石价值" />
        <el-table-column label="是否基础" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_base" type="success" size="small">是</el-tag>
            <span v-else>否</span>
          </template>
        </el-table-column>
      </el-table>

      <h4>换算规则</h4>
      <el-table :data="summary.rules" size="small" border>
        <el-table-column prop="from_item_name" label="从" />
        <el-table-column prop="to_item_name" label="到" />
        <el-table-column prop="factor" label="倍率" />
      </el-table>
    </el-card>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" header="货币换算">
          <div class="form-row">
            <el-input-number v-model="convertForm.amount" :min="0.0001" style="width: 110px" />
            <el-select v-model="convertForm.from_item_id" placeholder="从面额" style="flex: 1">
              <el-option v-for="d in summary?.denominations || []" :key="d.item_id" :label="d.item_name" :value="d.item_id" />
            </el-select>
            <el-select v-model="convertForm.to_item_id" placeholder="到面额" style="flex: 1">
              <el-option v-for="d in summary?.denominations || []" :key="d.item_id" :label="d.item_name" :value="d.item_id" />
            </el-select>
            <el-button type="primary" @click="doConvert">换算</el-button>
          </div>
          <div v-if="convertResult !== null" class="convert-result">
            结果：<b>{{ convertResult }}</b>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="never" header="记录 RMB 观察">
          <div class="form-row">
            <el-select v-model="fiatForm.currency_item_id" placeholder="货币物品" style="flex: 1">
              <el-option v-for="d in summary?.denominations || []" :key="d.item_id" :label="d.item_name" :value="d.item_id" />
            </el-select>
            <el-input-number v-model="fiatForm.quantity" :min="1" />
            <span>个 =</span>
            <el-input-number v-model="fiatForm.fiat_amount" :min="0.01" :precision="2" />
            <span>RMB</span>
            <el-button type="primary" @click="recordFiat">记录</el-button>
          </div>
          <div class="text-muted">例：99 钻石块 = 27.10 RMB</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-top: 16px" header="RMB 历史观察">
      <el-table :data="fiatList" size="small">
        <el-table-column prop="currency_item_name" label="货币物品" width="120" />
        <el-table-column label="观察" width="220">
          <template #default="{ row }">{{ row.quantity }} {{ row.currency_item_name }} = {{ row.fiat_amount }} {{ row.fiat_currency }}</template>
        </el-table-column>
        <el-table-column label="时间" width="200">
          <template #default="{ row }">{{ new Date(row.observed_at).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column prop="source" label="来源" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.form-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}
.convert-result {
  font-size: 16px;
  margin-top: 8px;
}
</style>
