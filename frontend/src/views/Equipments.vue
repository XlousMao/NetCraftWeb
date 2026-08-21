<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { equipmentApi, itemApi } from '@/api'
import ItemChip from '@/components/ItemChip.vue'

const equipments = ref<any[]>([])
const items = ref<any[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const showInactive = ref(false)
const form = ref<any>({ name: '', description: '', repair_requirements: [] })
const currentReq = ref({ item_id: null, quantity: 1 })

const dialogTitle = computed(() => (editingId.value ? '编辑装备' : '新建装备'))
const filteredEquipments = computed(() => {
  if (showInactive.value) return equipments.value
  return equipments.value.filter(e => e.is_active)
})

async function fetch() {
  const { data } = await equipmentApi.list(true)
  equipments.value = data.items
}

onMounted(async () => {
  fetch()
  const { data } = await itemApi.list({ page_size: 100 })
  items.value = data.items
})

function addReq() {
  if (!currentReq.value.item_id) return
  form.value.repair_requirements.push({ item_id: currentReq.value.item_id, quantity: currentReq.value.quantity })
  currentReq.value = { item_id: null, quantity: 1 }
}

function itemName(id: number) {
  return items.value.find((i) => i.id === id)?.name || `#${id}`
}

function resetForm() {
  editingId.value = null
  form.value = { name: '', description: '', repair_requirements: [] }
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  form.value = {
    name: row.name,
    description: row.description,
    repair_requirements: (row.repair_requirements || []).map((r: any) => ({ item_id: r.item_id, quantity: r.quantity })),
  }
  dialogVisible.value = true
}

async function save() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入装备名称')
    return
  }
  if (editingId.value) {
    await equipmentApi.update(editingId.value, form.value)
    ElMessage.success('装备已更新')
  } else {
    await equipmentApi.create(form.value)
    ElMessage.success('装备已创建')
  }
  dialogVisible.value = false
  resetForm()
  fetch()
}

async function remove(row: any) {
  try {
    await ElMessageBox.confirm(`确定要删除装备「${row.name}」吗？`, '警告', { type: 'warning' })
    await equipmentApi.remove(row.id)
    ElMessage.success('装备已删除')
    fetch()
  } catch {
    // 取消
  }
}
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 style="margin: 0">装备</h2>
      <div style="flex: 1"></div>
      <el-checkbox v-model="showInactive" style="margin-right: 16px">显示已停用</el-checkbox>
      <el-button type="primary" @click="openCreate">新建装备</el-button>
    </div>

    <el-table :data="filteredEquipments" style="margin-top: 16px">
      <el-table-column prop="name" label="名称" width="180" />
      <el-table-column label="维修材料">
        <template #default="{ row }">
          <ItemChip v-for="r in row.repair_requirements" :key="r.id" :name="r.item_name || '#' + r.item_id" :quantity="r.quantity" :icon-url="r.icon_url" />
          <span v-if="!row.repair_requirements || row.repair_requirements.length === 0" class="text-muted">无</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="560px">
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
        <el-button type="primary" @click="save">保存</el-button>
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
