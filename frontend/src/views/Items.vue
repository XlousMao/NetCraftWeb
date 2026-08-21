<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { itemApi } from '@/api'
import ItemCard from '@/components/ItemCard.vue'
import type { Item } from '@/types'

const items = ref<Item[]>([])
const total = ref(0)
const loading = ref(false)
const query = ref('')
const category = ref('')
const categories = ref<string[]>([])
const sort = ref('name')
const order = ref('asc')
const page = ref(1)
const pageSize = 20

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = ref({
  name: '',
  category: '材料',
  vendor_buy_price: null as number | null,
  market_price: null as number | null,
  manual_price: null as number | null,
  roles: [] as string[],
  description: '',
})
const selectedFile = ref<File | null>(null)

const dialogTitle = computed(() => (editingId.value ? '编辑物品' : '新建物品'))

const roleOptions = [
  { value: 'MATERIAL', label: '材料' },
  { value: 'EQUIPMENT', label: '装备' },
  { value: 'CONSUMABLE', label: '消耗品' },
  { value: 'CURRENCY', label: '货币' },
  { value: 'TRADEABLE', label: '可交易' },
  { value: 'DUNGEON_DROP', label: '副本掉落' },
  { value: 'REPAIR_MATERIAL', label: '维修材料' },
  { value: 'RECIPE_MATERIAL', label: '配方材料' },
  { value: 'RECIPE_OUTPUT', label: '配方产出' },
]

async function fetch() {
  loading.value = true
  try {
    const { data } = await itemApi.list({
      q: query.value || undefined,
      category: category.value || undefined,
      sort: sort.value,
      order: order.value,
      page: page.value,
      page_size: pageSize,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function fetchCategories() {
  const { data } = await itemApi.categories()
  categories.value = data
}

function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  selectedFile.value = target.files && target.files.length > 0 ? target.files[0] : null
}

function resetForm() {
  editingId.value = null
  form.value = { name: '', category: '材料', vendor_buy_price: null, market_price: null, manual_price: null, roles: [], description: '' }
  selectedFile.value = null
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(item: Item) {
  editingId.value = item.id
  form.value = {
    name: item.name,
    category: item.category || '材料',
    vendor_buy_price: item.vendor_buy_price ?? null,
    market_price: item.market_price ?? null,
    manual_price: item.manual_price ?? null,
    roles: item.roles || [],
    description: item.description || '',
  }
  selectedFile.value = null
  dialogVisible.value = true
}

async function saveItem() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入物品名称')
    return
  }
  if (editingId.value) {
    await itemApi.update(editingId.value, form.value)
    ElMessage.success('物品已更新')
  } else {
    const { data: item } = await itemApi.create(form.value)
    if (selectedFile.value) {
      try {
        const fd = new FormData()
        fd.append('file', selectedFile.value)
        await itemApi.uploadImage(item.id, fd)
        ElMessage.success('物品创建并上传图片成功')
      } catch {
        ElMessage.warning('物品已创建，但图片上传失败')
      }
    } else {
      ElMessage.success('物品已创建')
    }
  }
  dialogVisible.value = false
  resetForm()
  fetch()
}

async function removeItem(item: Item) {
  try {
    await ElMessageBox.confirm(`确定要删除物品「${item.name}」吗？（历史记录会保留）`, '警告', { type: 'warning' })
    await itemApi.remove(item.id)
    ElMessage.success('物品已删除')
    fetch()
  } catch {
    // 取消
  }
}

function onSearch() {
  page.value = 1
  fetch()
}

onMounted(() => {
  fetch()
  fetchCategories()
})
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <el-input v-model="query" placeholder="按名称搜索" clearable style="width: 220px" @keyup.enter="onSearch" @clear="onSearch" />
      <el-select v-model="category" placeholder="分类" clearable style="width: 140px" @change="onSearch">
        <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
      </el-select>
      <el-select v-model="sort" style="width: 120px" @change="onSearch">
        <el-option label="名称" value="name" />
        <el-option label="价值" value="value" />
        <el-option label="重要性" value="importance" />
        <el-option label="创建时间" value="created" />
      </el-select>
      <el-select v-model="order" style="width: 100px" @change="onSearch">
        <el-option label="升序" value="asc" />
        <el-option label="降序" value="desc" />
      </el-select>
      <el-button type="primary" @click="onSearch">搜索</el-button>
      <div style="flex: 1"></div>
      <el-button type="primary" @click="openCreate">快速录入物品</el-button>
    </div>

    <div class="card-grid" v-loading="loading" style="margin-top: 16px">
      <ItemCard v-for="item in items" :key="item.id" :item="item" @edit="openEdit" @remove="removeItem" />
    </div>
    <el-empty v-if="!loading && items.length === 0" description="暂无物品，点击右上角快速录入" />

    <el-pagination
      v-if="total > pageSize"
      style="margin-top: 16px; justify-content: flex-end"
      layout="prev, pager, next, total"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      @current-change="(p: number) => { page = p; fetch() }"
    />

    <!-- 新建 / 编辑 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="520px">
      <el-form label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：精钢锭" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in ['材料', '装备', '消耗品', '货币', '其他']" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.roles" multiple collapse-tags style="width: 100%" placeholder="可多选">
            <el-option v-for="r in roleOptions" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="商人收购价">
          <el-input-number v-model="form.vendor_buy_price" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="市场价格">
          <el-input-number v-model="form.market_price" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="手动估值">
          <el-input-number v-model="form.manual_price" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item v-if="!editingId" label="图片(可选)">
          <input type="file" accept="image/*" @change="handleFileChange" style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveItem">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
