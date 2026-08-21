<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
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
const form = ref({ name: '', category: '材料', vendor_buy_price: null as number | null, market_price: null as number | null, description: '' })
const selectedFile = ref<File | null>(null)

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
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0]
  } else {
    selectedFile.value = null
  }
}

async function createItem() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入物品名称')
    return
  }
  const { data: item } = await itemApi.create(form.value)
  
  if (selectedFile.value) {
    try {
      const formData = new FormData()
      formData.append('file', selectedFile.value)
      await itemApi.uploadImage(item.id, formData)
      ElMessage.success('物品创建并上传图片成功')
    } catch (e) {
      ElMessage.warning('物品已创建，但图片上传失败')
    }
  } else {
    ElMessage.success('物品已创建，可前往详情上传图片')
  }

  dialogVisible.value = false
  form.value = { name: '', category: '材料', vendor_buy_price: null, market_price: null, description: '' }
  selectedFile.value = null
  fetch()
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
      <el-button type="primary" @click="dialogVisible = true">快速录入物品</el-button>
    </div>

    <div class="card-grid" v-loading="loading" style="margin-top: 16px">
      <ItemCard v-for="item in items" :key="item.id" :item="item" />
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

    <!-- 快速录入 -->
    <el-dialog v-model="dialogVisible" title="新建物品" width="480px">
      <el-form label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="如：精钢锭" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in ['材料', '装备', '消耗品', '货币', '其他']" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="商人收购价">
          <el-input-number v-model="form.vendor_buy_price" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="市场价格">
          <el-input-number v-model="form.market_price" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="图片(可选)">
          <input type="file" accept="image/*" @change="handleFileChange" style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createItem">保存物品</el-button>
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
