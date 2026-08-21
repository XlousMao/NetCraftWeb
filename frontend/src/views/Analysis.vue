<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { analysisApi } from '@/api'
import StatCard from '@/components/StatCard.vue'
import Chart from '@/components/Chart.vue'

const range = ref<[Date, Date] | null>(null)
const period = ref<any>(null)
const rankings = ref<any[]>([])

async function fetch() {
  const params: any = {}
  if (range.value) {
    params.start = range.value[0].toISOString()
    params.end = range.value[1].toISOString()
  }
  const [p, d] = await Promise.all([
    analysisApi.period(params),
    analysisApi.dungeonRankings(params),
  ])
  period.value = p.data
  rankings.value = d.data
}

const costChart = computed(() => ({
  tooltip: { trigger: 'item' },
  series: [
    {
      type: 'pie',
      radius: '60%',
      data: period.value?.cost_breakdown || [],
    },
  ],
}))

const rankChart = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: rankings.value.map((d) => d.dungeon_name) },
  yAxis: { type: 'value' },
  series: [
    { name: '净利润', type: 'bar', data: rankings.value.map((d) => d.net_profit), itemStyle: { color: '#3b82f6' } },
  ],
}))

onMounted(fetch)
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <el-date-picker
        v-model="range"
        type="daterange"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
      />
      <el-button type="primary" @click="fetch">查询</el-button>
    </div>

    <template v-if="period">
      <div class="stat-grid">
        <StatCard label="总掉落价值" :value="period.total_gross.toLocaleString()" />
        <StatCard label="总维修成本" :value="period.total_repair.toLocaleString()" />
        <StatCard label="总消耗品成本" :value="period.total_consumable.toLocaleString()" />
        <StatCard label="总投入时间" :value="period.total_duration_minutes.toFixed(1) + ' 分钟'" />
        <StatCard label="净利润" :value="period.net_profit.toLocaleString()" :value-class="period.net_profit >= 0 ? 'profit' : 'loss'" />
        <StatCard label="平均利润/小时" :value="period.profit_per_hour.toLocaleString()" />
      </div>

      <el-alert
        v-if="period.is_loss"
        type="error"
        :closable="false"
        title="该周期副本处于亏损状态"
        style="margin: 16px 0"
      />

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :span="12">
          <el-card shadow="never" header="成本构成">
            <Chart :option="costChart" height="280px" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never" header="副本净利润排行">
            <Chart :option="rankChart" height="280px" />
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}
</style>
