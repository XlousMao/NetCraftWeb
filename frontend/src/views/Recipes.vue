<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { recipeApi, itemApi } from '@/api'
import ItemChip from '@/components/ItemChip.vue'

const recipes = ref<any[]>([])
const items = ref<any[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const showInactive = ref(false)
const form = ref<any>({ name: '', recipe_type: 'ALCHEMY', expected_success_rate: 0.9, materials: [], outputs: [] })
const currentMat = ref({ item_id: null, quantity: 1 })
const currentOut = ref({ item_id: null, quantity: 1 })

const dialogTitle = computed(() => (editingId.value ? '编辑配方' : '新建配方'))
const typeLabel: Record<string, string> = { ALCHEMY: '炼金', CRAFT: '制造', SYNTHESIS: '合成' }
const filteredRecipes = computed(() => {
  if (showInactive.value) return recipes.value
  return recipes.value.filter(r => r.is_active)
})

async function fetch() {
  const { data } = await recipeApi.list(true)
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
  form.value.materials.push({ item_id: currentMat.value.item_id, quantity: currentMat.value.quantity })
  currentMat.value = { item_id: null, quantity: 1 }
}

function addOut() {
  if (!currentOut.value.item_id) return
  form.value.outputs.push({ item_id: currentOut.value.item_id, quantity: currentOut.value.quantity })
  currentOut.value = { item_id: null, quantity: 1 }
}

function resetForm() {
  editingId.value = null
  form.value = { name: '', recipe_type: 'ALCHEMY', expected_success_rate: 0.9, materials: [], outputs: [] }
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  form.value = {
    name: row.name,
    recipe_type: row.recipe_type || 'ALCHEMY',
    expected_success_rate: row.expected_success_rate,
    materials: (row.materials || []).map((m: any) => ({ item_id: m.item_id, quantity: m.quantity })),
    outputs: (row.outputs || []).map((o: any) => ({ item_id: o.item_id, quantity: o.quantity })),
  }
  dialogVisible.value = true
}

async function save() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入配方名称')
    return
  }
  if (editingId.value) {
    await recipeApi.update(editingId.value, form.value)
    ElMessage.success('配方已更新')
  } else {
    await recipeApi.create(form.value)
    ElMessage.success('配方已创建')
  }
  dialogVisible.value = false
  resetForm()
  fetch()
}

async function remove(row: any) {
  try {
    await ElMessageBox.confirm(`确定要删除配方「${row.name}」吗？`, '警告', { type: 'warning' })
    await recipeApi.remove(row.id)
    ElMessage.success('配方已删除')
    fetch()
  } catch {
    // 取消
  }
}
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 style="margin: 0">炼金 / 配方</h2>
      <div style="flex: 1"></div>
      <el-checkbox v-model="showInactive" style="margin-right: 16px">显示已停用</el-checkbox>
      <el-button type="primary" @click="openCreate">新建配方</el-button>
    </div>

    <el-table :data="filteredRecipes" style="margin-top: 16px">
      <el-table-column prop="name" label="配方" width="160" />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">{{ typeLabel[row.recipe_type] || row.recipe_type }}</template>
      </el-table-column>
      <el-table-column label="材料" min-width="200">
        <template #default="{ row }">
          <ItemChip v-for="m in row.materials" :key="m.id" :name="m.item_name || '#' + m.item_id" :quantity="m.quantity" :icon-url="m.icon_url" />
        </template>
      </el-table-column>
      <el-table-column label="产出" min-width="180">
        <template #default="{ row }">
          <ItemChip v-for="o in row.outputs" :key="o.id" :name="o.item_name || '#' + o.item_id" :quantity="o.quantity" :icon-url="o.icon_url" type="success" />
        </template>
      </el-table-column>
      <el-table-column label="理论成功率" width="110">
        <template #default="{ row }">{{ (row.expected_success_rate * 100).toFixed(0) }}%</template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.recipe_type" style="width: 100%">
            <el-option label="炼金 ALCHEMY" value="ALCHEMY" />
            <el-option label="制造 CRAFT" value="CRAFT" />
            <el-option label="合成 SYNTHESIS" value="SYNTHESIS" />
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
