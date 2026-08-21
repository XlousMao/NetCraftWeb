<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { recipeApi, itemApi } from '@/api'

const recipes = ref<any[]>([])
const items = ref<any[]>([])
const dialogVisible = ref(false)
const form = ref<any>({ name: '', category: '炼金', expected_success_rate: 0.9, materials: [], outputs: [] })
const currentMat = ref({ item_id: null, quantity: 1 })
const currentOut = ref({ item_id: null, quantity: 1 })

async function fetch() {
  const { data } = await recipeApi.list()
  recipes.value = data.items
}

onMounted(async () => {
  fetch()
  const { data } = await itemApi.list({ page_size: 100 })
  items.value = data.items
})

function itemName(id: number) {
  return items.value.find((i) => i.id === id)?.name || `#${id}`
}

function addMat() {
  if (!currentMat.value.item_id) return
  form.value.materials.push({ ...currentMat.value })
  currentMat.value = { item_id: null, quantity: 1 }
}

function addOut() {
  if (!currentOut.value.item_id) return
  form.value.outputs.push({ ...currentOut.value })
  currentOut.value = { item_id: null, quantity: 1 }
}

async function create() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入配方名称')
    return
  }
  await recipeApi.create(form.value)
  ElMessage.success('配方已创建')
  dialogVisible.value = false
  form.value = { name: '', category: '炼金', expected_success_rate: 0.9, materials: [], outputs: [] }
  fetch()
}
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 style="margin: 0">炼金 / 配方</h2>
      <div style="flex: 1"></div>
      <el-button type="primary" @click="dialogVisible = true">新建配方</el-button>
    </div>

    <el-table :data="recipes" style="margin-top: 16px">
      <el-table-column prop="name" label="配方" width="180" />
      <el-table-column prop="category" label="分类" width="100" />
      <el-table-column label="材料">
        <template #default="{ row }">
          <el-tag v-for="m in row.materials" :key="m.id" size="small" style="margin: 2px">{{ m.item_name }} ×{{ m.quantity }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="产出">
        <template #default="{ row }">
          <el-tag v-for="o in row.outputs" :key="o.id" size="small" type="success" style="margin: 2px">{{ o.item_name }} ×{{ o.quantity }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="理论成功率" width="110">
        <template #default="{ row }">{{ (row.expected_success_rate * 100).toFixed(0) }}%</template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="新建配方" width="600px">
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option label="炼金" value="炼金" />
            <el-option label="制造" value="制造" />
          </el-select>
        </el-form-item>
        <el-form-item label="理论成功率">
          <el-slider v-model="form.expected_success_rate" :min="0" :max="1" :step="0.01" :format-tooltip="(v: number) => (v * 100).toFixed(0) + '%'" />
        </el-form-item>
        <el-divider content-position="left">材料</el-divider>
        <div class="add-row">
          <el-select v-model="currentMat.item_id" filterable placeholder="搜索材料" style="flex: 1">
            <el-option v-for="i in items" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
          <el-input-number v-model="currentMat.quantity" :min="1" />
          <el-button type="primary" @click="addMat">添加</el-button>
        </div>
        <el-tag v-for="(m, idx) in form.materials" :key="idx" closable @close="form.materials.splice(idx, 1)" style="margin: 4px">{{ itemName(m.item_id) }} ×{{ m.quantity }}</el-tag>
        <el-divider content-position="left">产出</el-divider>
        <div class="add-row">
          <el-select v-model="currentOut.item_id" filterable placeholder="搜索产出物" style="flex: 1">
            <el-option v-for="i in items" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
          <el-input-number v-model="currentOut.quantity" :min="1" />
          <el-button type="primary" @click="addOut">添加</el-button>
        </div>
        <el-tag v-for="(o, idx) in form.outputs" :key="idx" closable type="success" @close="form.outputs.splice(idx, 1)" style="margin: 4px">{{ itemName(o.item_id) }} ×{{ o.quantity }}</el-tag>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
}
.add-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
</style>
