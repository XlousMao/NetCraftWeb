<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { activityApi, analysisApi } from '@/api'
import Chart from '@/components/Chart.vue'

const records = ref<any[]>([])
const efficiency = ref<any>(null)
const dialogVisible = ref(false)
const form = ref<any>({ activity_type: 'GATHERING', label: '', started_at: new Date(), gross_value: 0, total_cost: 0 })

const typeLabel: Record<string, string> = {
  DUNGEON: '副本',
  ALCHEMY: '炼金',
  GATHERING: '采集',
  CRAFTING: '制造',
  TRADING: '交易',
  OTHER: '其他',
}

async function fetch() {
  const [r, e] = await Promise.all([
    activityApi.records({ page_size: 50 }),
    analysisApi.activityEfficiency({}),
  ])
  records.value = r.data.items
  efficiency.value = e.data
}

onMounted(fetch)

const effChart = computed(() => {
  const acts = efficiency.value?.activities || []
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: acts.map((a: any) => typeLabel[a.activity_type] || a.activity_type) },
    yAxis: { type: 'value' },
    series: [
      {
        name: '每小时收益',
        type: 'bar',
        data: acts.map((a: any) => a.profit_per_hour),
        itemStyle: { color: '#3b82f6' },
      },
    ],
  }
})

async function submit() {
  if (!form.value.label.trim()) {
    ElMessage.warning('请输入活动名称')
    return
  }
  await activityApi.createRecord({
    ...form.value,
    started_at: new Date(form.value.started_at).toISOString(),
  })
  ElMessage.success('活动记录已添加')
  dialogVisible.value = false
  form.value = { activity_type: 'GATHERING', label: '', started_at: new Date(), gross_value: 0, total_cost: 0 }
  fetch()
}
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 style="margin: 0">活动</h2>
      <div style="flex: 1"></div>
      <el-button type="primary" @click="dialogVisible = true">记录活动</el-button>
    </div>

    <el-card v-if="efficiency" shadow="never" style="margin-top: 16px">
      <template #header>
        <span style="font-weight: 600">活动效率（每小时收益）</span>
        <span class="text-muted" style="margin-left: 12px">
          最优活动：{{ efficiency.best_activity ? typeLabel[efficiency.best_activity] : '—' }}
        </span>
      </template>
      <Chart :option="effChart" height="260px" />
    </el-card>

    <el-table :data="records" style="margin-top: 16px">
      <el-table-column label="类型" width="100">
        <template #default="{ row }">{{ typeLabel[row.activity_type] }}</template>
      </el-table-column>
      <el-table-column prop="label" label="名称" />
      <el-table-column label="时间" width="180">
        <template #default="{ row }">{{ new Date(row.started_at).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column prop="gross_value" label="收益" width="110" />
      <el-table-column prop="total_cost" label="成本" width="110" />
      <el-table-column label="净利润" width="110">
        <template #default="{ row }">
          <span :class="row.net_profit >= 0 ? 'profit' : 'loss'">{{ row.net_profit.toLocaleString() }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="profit_per_hour" label="金币/小时" width="110" />
    </el-table>

    <el-dialog v-model="dialogVisible" title="记录活动" width="480px">
      <el-form label-width="90px">
        <el-form-item label="类型">
          <el-select v-model="form.activity_type" style="width: 100%">
            <el-option label="采集" value="GATHERING" />
            <el-option label="制造" value="CRAFTING" />
            <el-option label="交易" value="TRADING" />
            <el-option label="其他" value="OTHER" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="form.label" />
        </el-form-item>
        <el-form-item label="时间">
          <el-date-picker v-model="form.started_at" type="datetime" style="width: 100%" />
        </el-form-item>
        <el-form-item label="收益">
          <el-input-number v-model="form.gross_value" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="成本">
          <el-input-number v-model="form.total_cost" :min="0" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
}
</style>
