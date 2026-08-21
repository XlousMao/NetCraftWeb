<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { dungeonApi } from '@/api'

const dungeons = ref<any[]>([])
const dialogVisible = ref(false)
const form = ref({ name: '', description: '' })

async function fetch() {
  const { data } = await dungeonApi.list()
  dungeons.value = data.items
}

onMounted(fetch)

async function create() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入副本名称')
    return
  }
  await dungeonApi.create(form.value)
  ElMessage.success('副本已创建')
  dialogVisible.value = false
  form.value = { name: '', description: '' }
  fetch()
}
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 style="margin: 0">副本</h2>
      <div style="flex: 1"></div>
      <el-button type="primary" @click="dialogVisible = true">新建副本</el-button>
    </div>

    <el-table :data="dungeons" style="margin-top: 16px">
      <el-table-column prop="name" label="名称" width="200" />
      <el-table-column prop="description" label="描述" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="新建副本" width="480px">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
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
</style>
