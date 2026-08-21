<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import StatCard from '@/components/StatCard.vue'
import Chart from '@/components/Chart.vue'
import { dashboardApi, aiApi } from '@/api'
import type { DashboardData } from '@/types'

const data = ref<DashboardData | null>(null)
const loading = ref(true)
const aiContent = ref('')
const aiLoading = ref(false)

onMounted(async () => {
  try {
    const { data: d } = await dashboardApi.get()
    data.value = d
  } finally {
    loading.value = false
  }
  runAI()
})

async function runAI() {
  aiLoading.value = true
  try {
    const { data: r } = await aiApi.analyze()
    aiContent.value = r.content
  } finally {
    aiLoading.value = false
  }
}

const week = computed(() => data.value?.week)
const today = computed(() => data.value?.today)

const costChart = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [
    {
      type: 'pie',
      radius: ['45%', '70%'],
      data: week.value?.cost_breakdown || [],
      label: { formatter: '{b}: {c}' },
    },
  ],
}))

const dungeonChart = computed(() => {
  const tops = data.value?.top_dungeons || []
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['净利润', '每小时收益'] },
    xAxis: { type: 'category', data: tops.map((d) => d.dungeon_name) },
    yAxis: { type: 'value' },
    series: [
      { name: '净利润', type: 'bar', data: tops.map((d) => d.net_profit), itemStyle: { color: '#3b82f6' } },
      { name: '每小时收益', type: 'line', data: tops.map((d) => d.profit_per_hour), itemStyle: { color: '#e11d48' } },
    ],
  }
})
</script>

<template>
  <div class="page" v-loading="loading">
    <!-- 本周副本经济 -->
    <el-card shadow="never" style="margin-bottom: 16px">
      <template #header>
        <span style="font-weight: 600">本周副本经济</span>
        <el-tag v-if="week?.is_loss" type="danger" style="margin-left: 8px">本周副本处于亏损状态</el-tag>
      </template>
      <div class="week-grid">
        <StatCard label="掉落价值" :value="week?.total_gross.toLocaleString() ?? '—'" />
        <StatCard label="维修" :value="week?.total_repair.toLocaleString() ?? '—'" />
        <StatCard label="消耗" :value="week?.total_consumable.toLocaleString() ?? '—'" />
        <StatCard label="其他" :value="week?.total_other.toLocaleString() ?? '—'" />
        <StatCard label="本周净利润" :value="(week?.net_profit ?? 0).toLocaleString()" :value-class="(week?.net_profit ?? 0) >= 0 ? 'profit' : 'loss'" />
        <StatCard label="平均收益/小时" :value="week?.profit_per_hour.toLocaleString() ?? '—'" sub="净利润 / 有效时间" />
      </div>
    </el-card>

    <!-- 今日 + 排行 -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="8">
        <el-card shadow="never" header="今日">
          <div class="today-list">
            <div class="row"><span>副本次数</span><b>{{ today?.run_count ?? 0 }}</b></div>
            <div class="row"><span>总收益</span><b class="profit">{{ today?.total_gross.toLocaleString() ?? 0 }}</b></div>
            <div class="row"><span>净利润</span><b :class="(today?.net_profit ?? 0) >= 0 ? 'profit' : 'loss'">{{ today?.net_profit.toLocaleString() ?? 0 }}</b></div>
            <div class="row"><span>投入时间</span><b>{{ (today?.total_duration_minutes ?? 0).toFixed(1) }}h</b></div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card shadow="never" header="副本收益排行">
          <Chart :option="dungeonChart" height="240px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="12">
        <el-card shadow="never" header="成本构成">
          <Chart :option="costChart" height="240px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" header="最重要物品">
          <el-table :data="data?.important_items || []" size="small">
            <el-table-column prop="name" label="物品" />
            <el-table-column prop="category" label="分类" width="90" />
            <el-table-column prop="importance_score" label="重要性" width="100" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- AI 洞察 -->
    <el-card shadow="never">
      <template #header>
        <span style="font-weight: 600">AI 洞察</span>
        <el-button size="small" style="float: right" @click="runAI" :loading="aiLoading">重新分析</el-button>
      </template>
      <div v-loading="aiLoading" class="ai-content" v-html="aiContent.replace(/\n/g, '<br/>')"></div>
    </el-card>
  </div>
</template>

<style scoped>
.week-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}
.today-list .row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f5f6f7;
  font-size: 14px;
}
.ai-content {
  line-height: 1.8;
  font-size: 14px;
  min-height: 60px;
}
</style>
