<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { equipmentApi, itemApi } from '@/api'

const equipments = ref<any[]>([])
const items = ref<any[]>([])
const dialogVisible = ref(false)
const form = ref<any>({ name: '', description: '', repair_requirements: [] })
const currentReq = ref({ item_id: null, quantity: 1 })

async function fetch() {
  const { data } = await equipmentApi.list()
  equipments.value = data.items
}

onMounted(async () => {
  fetch()
  const { data } = await itemApi.list({ page_size: 100 })
  items.value = data.items
})

function addReq() {
  if (!currentReq.value.item_id) return
  form.value.repair_requirements.push({ ...currentReq.value, currency_cost: 0 })
  currentReq.value = { item_id: null, quantity: 1 }
}

function itemName(id: number) {
  return items.value.find((i) => i.id === id)?.name || `#${id}`
}

async function create() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入装备名称')
    return
  }
  await equipmentApi.create(form.value)
  ElMessage.success('装备已创建')
  dialogVisible.value = false
  form.value = { name: '', description: '', repair_requirements: [] }
  fetch()
}
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 style="margin: 0">装备</h2>
      <div style="flex: 1"></div>
      <el-button type="primary" @click="dialogVisible = true">新建装备</el-button>
    </div>

    <el-table :data="equipments" style="margin-top: 16px">
      <el-table-column prop="name" label="名称" width="200" />
      <el-table-column label="维修材料">
        <template #default="{ row }">
          <el-tag v-for="r in row.repair_requirements" :key="r.id" size="small" style="margin: 2px">
            {{ r.item_name }} ×{{ r.quantity }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="新建装备" width="560px">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-divider content-position="left">维修需求</el-divider>
        <div class="add-row">
          <el-select v-model="currentReq.item_id" filterable placeholder="搜索材料" style="flex: 1">
            <el-option v-for="i in items" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
          <el-input-number v-model="currentReq.quantity" :min="1" />
          <el-button type="primary" @click="addReq">添加</el-button>
        </div>
        <el-tag v-for="(r, idx) in form.repair_requirements" :key="idx" closable @close="form.repair_requirements.splice(idx, 1)" style="margin: 4px">
          {{ itemName(r.item_id) }} ×{{ r.quantity }}
        </el-tag>
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
