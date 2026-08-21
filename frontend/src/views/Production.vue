<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { productionApi, recipeApi } from '@/api'

const records = ref<any[]>([])
const recipes = ref<any[]>([])
const dialogVisible = ref(false)
const form = ref<any>({ recipe_id: null, started_at: new Date(), attempted_count: 100, success_count: 0 })

async function fetch() {
  const { data } = await productionApi.list({ page_size: 50 })
  records.value = data.items
}

onMounted(async () => {
  fetch()
  const { data } = await recipeApi.list()
  recipes.value = data.items
})

async function submit() {
  if (!form.value.recipe_id) {
    ElMessage.warning('请选择配方')
    return
  }
  const { data } = await productionApi.create({
    ...form.value,
    started_at: new Date(form.value.started_at).toISOString(),
  })
  ElMessage.success(`实际成功率 ${(data.actual_success_rate * 100).toFixed(1)}%，ROI ${(data.roi * 100).toFixed(1)}%`)
  dialogVisible.value = false
  form.value = { recipe_id: null, started_at: new Date(), attempted_count: 100, success_count: 0 }
  fetch()
}
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 style="margin: 0">生产记录</h2>
      <div style="flex: 1"></div>
      <el-button type="primary" @click="dialogVisible = true">新增生产记录</el-button>
    </div>

    <el-table :data="records" style="margin-top: 16px">
      <el-table-column prop="recipe_name" label="配方" />
      <el-table-column prop="attempted_count" label="投入次数" width="100" />
      <el-table-column prop="success_count" label="成功" width="90" />
      <el-table-column prop="fail_count" label="失败" width="90" />
      <el-table-column label="成功率" width="100">
        <template #default="{ row }">{{ (row.actual_success_rate * 100).toFixed(1) }}%</template>
      </el-table-column>
      <el-table-column prop="material_cost" label="材料成本" width="110" />
      <el-table-column prop="actual_unit_cost" label="实际单位成本" width="120" />
      <el-table-column prop="revenue" label="收入" width="100" />
      <el-table-column label="毛利" width="100">
        <template #default="{ row }">
          <span :class="row.gross_profit >= 0 ? 'profit' : 'loss'">{{ row.gross_profit.toLocaleString() }}</span>
        </template>
      </el-table-column>
      <el-table-column label="ROI" width="100">
        <template #default="{ row }">
          <span :class="row.roi >= 0 ? 'profit' : 'loss'">{{ (row.roi * 100).toFixed(1) }}%</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="新增生产记录" width="480px">
      <el-form label-width="90px">
        <el-form-item label="配方" required>
          <el-select v-model="form.recipe_id" style="width: 100%">
            <el-option v-for="r in recipes" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="form.started_at" type="datetime" style="width: 100%" />
        </el-form-item>
        <el-form-item label="投入次数">
          <el-input-number v-model="form.attempted_count" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="成功次数">
          <el-input-number v-model="form.success_count" :min="0" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存并计算</el-button>
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
