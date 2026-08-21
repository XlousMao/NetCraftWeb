<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { dungeonApi } from '@/api'

const dungeons = ref<any[]>([])
const dialogVisible = ref(false)
const form = ref({ name: '', description: '', is_active: true })
const editId = ref<number | null>(null)
const showInactive = ref(false)

const filteredDungeons = computed(() => {
  if (showInactive.value) return dungeons.value
  return dungeons.value.filter(d => d.is_active)
})

async function fetch() {
  // 管理页需要拿到全部副本（含停用），用「显示已停用」开关在前端过滤
  const { data } = await dungeonApi.list(true)
  dungeons.value = data.items
}

onMounted(fetch)

function openCreate() {
  editId.value = null
  form.value = { name: '', description: '', is_active: true }
  dialogVisible.value = true
}

function openEdit(row: any) {
  editId.value = row.id
  form.value = { name: row.name, description: row.description, is_active: row.is_active }
  dialogVisible.value = true
}

async function save() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入副本名称')
    return
  }
  if (editId.value) {
    await dungeonApi.update(editId.value, form.value)
    ElMessage.success('副本已更新')
  } else {
    await dungeonApi.create(form.value)
    ElMessage.success('副本已创建')
  }
  dialogVisible.value = false
  fetch()
}

import { ElMessageBox } from 'element-plus'
async function remove(row: any) {
  try {
    await ElMessageBox.confirm(`确定要删除副本 "${row.name}" 吗？`, '警告', { type: 'warning' })
    await dungeonApi.remove(row.id)
    ElMessage.success('副本已删除')
    fetch()
  } catch {
    // cancelled
  }
}
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 style="margin: 0">副本</h2>
      <div style="flex: 1"></div>
      <el-checkbox v-model="showInactive" style="margin-right: 16px">显示已停用</el-checkbox>
      <el-button type="primary" @click="openCreate">新建副本</el-button>
    </div>

    <el-table :data="filteredDungeons" style="margin-top: 16px">
      <el-table-column prop="name" label="名称" width="200" />
      <el-table-column prop="description" label="描述" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
          <el-button type="danger" link @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editId ? '编辑副本' : '新建副本'" width="480px">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="状态" v-if="editId">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
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
</style>
