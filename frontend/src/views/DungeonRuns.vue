<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { dungeonRunApi, dungeonApi, itemApi, equipmentApi } from '@/api'

const runs = ref<any[]>([])
const dungeons = ref<any[]>([])
const activeDungeons = computed(() => dungeons.value.filter(d => d.is_active))
const items = ref<any[]>([])
const equipments = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = ref<any>({
  dungeon_id: null,
  started_at: new Date(),
  travel_minutes: 0,
  combat_minutes: 0,
  death_count: 0,
  other_cost: 0,
  loots: [],
  consumptions: [],
  repairs: [],
})

const currentLoot = ref({ item_id: null, quantity: 1 })
const currentConsumption = ref({ item_id: null, quantity: 1 })
const currentRepair = ref({ equipment_id: null })

const dialogTitle = computed(() => (editingId.value ? '编辑副本记录' : '新增副本记录'))
// 编辑时需能选中当前记录所属副本（可能已停用），故显示全部；新建时只显示启用副本
const dungeonOptions = computed(() => (editingId.value ? dungeons.value : activeDungeons.value))

async function fetch() {
  loading.value = true
  try {
    const { data } = await dungeonRunApi.list({ page: page.value, page_size: 20 })
    runs.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  fetch()
  const [d, i, e] = await Promise.all([
    dungeonApi.list(true),
    itemApi.list({ page_size: 100 }),
    equipmentApi.list(),
  ])
  dungeons.value = d.data.items
  items.value = i.data.items
  equipments.value = e.data.items
})

function addLoot() {
  if (!currentLoot.value.item_id) return
  form.value.loots.push({ ...currentLoot.value })
  currentLoot.value = { item_id: null, quantity: 1 }
}

function addConsumption() {
  if (!currentConsumption.value.item_id) return
  form.value.consumptions.push({ ...currentConsumption.value })
  currentConsumption.value = { item_id: null, quantity: 1 }
}

function addRepair() {
  if (!currentRepair.value.equipment_id) return
  form.value.repairs.push({ equipment_id: currentRepair.value.equipment_id })
  currentRepair.value = { equipment_id: null }
}

function itemName(id: number) {
  return items.value.find((i) => i.id === id)?.name || `#${id}`
}

function resetForm() {
  editingId.value = null
  form.value = {
    dungeon_id: null,
    started_at: new Date(),
    travel_minutes: 0,
    combat_minutes: 0,
    death_count: 0,
    other_cost: 0,
    loots: [],
    consumptions: [],
    repairs: [],
  }
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  form.value = {
    dungeon_id: row.dungeon_id,
    started_at: new Date(row.started_at),
    travel_minutes: row.travel_minutes,
    combat_minutes: row.combat_minutes,
    death_count: row.death_count,
    other_cost: row.other_cost,
    loots: (row.loots || []).map((l: any) => ({ item_id: l.item_id, quantity: l.quantity })),
    consumptions: (row.consumptions || []).map((c: any) => ({ item_id: c.item_id, quantity: c.quantity })),
    repairs: (row.repairs || []).map((r: any) => ({ item_id: r.item_id, quantity: r.quantity })),
  }
  dialogVisible.value = true
}

async function submit() {
  if (!form.value.dungeon_id) {
    ElMessage.warning('请选择副本')
    return
  }
  const payload = {
    ...form.value,
    started_at: new Date(form.value.started_at).toISOString(),
  }
  if (editingId.value) {
    const { data } = await dungeonRunApi.update(editingId.value, payload)
    ElMessage.success(`已更新，净利润 ${data.net_profit.toLocaleString()} 钻石`)
  } else {
    const { data } = await dungeonRunApi.create(payload)
    ElMessage.success(`本次净利润 ${data.net_profit.toLocaleString()} 钻石`)
  }
  dialogVisible.value = false
  resetForm()
  fetch()
}

async function remove(row: any) {
  await dungeonRunApi.remove(row.id)
  ElMessage.success('副本记录已删除')
  fetch()
}
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 style="margin: 0">副本记录</h2>
      <div style="flex: 1"></div>
      <el-button type="primary" @click="openCreate">新增副本记录</el-button>
    </div>

    <el-table :data="runs" v-loading="loading" style="margin-top: 16px">
      <el-table-column prop="dungeon_name" label="副本" width="120" />
      <el-table-column label="掉落物" min-width="200">
        <template #default="{ row }">
          <div class="loot-imgs">
            <el-tooltip v-for="l in (row.loots || []).slice(0, 5)" :key="l.id" :content="`${l.item_name} ×${l.quantity}`" placement="top">
              <div class="loot-img-wrap">
                <img v-if="l.icon_url" :src="l.icon_url" class="loot-img" />
                <span v-else class="loot-ph">{{ (l.item_name || '?').slice(0, 1) }}</span>
                <span class="loot-qty">×{{ l.quantity }}</span>
              </div>
            </el-tooltip>
            <el-tag v-if="(row.loots || []).length > 5" size="small" type="info">+{{ row.loots.length - 5 }}</el-tag>
            <span v-if="!row.loots || row.loots.length === 0" class="text-muted">无</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="160">
        <template #default="{ row }">{{ new Date(row.started_at).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column prop="gross_value" label="掉落价值(钻石)" width="120" />
      <el-table-column prop="repair_cost" label="维修" width="90" />
      <el-table-column prop="consumable_cost" label="消耗" width="90" />
      <el-table-column prop="total_cost" label="总成本" width="100" />
      <el-table-column label="净利润" width="130">
        <template #default="{ row }">
          <span :class="row.net_profit >= 0 ? 'profit' : 'loss'">{{ row.net_profit.toLocaleString() }}</span>
          <div v-if="row.net_profit_fiat != null" class="text-muted">≈ {{ row.net_profit_fiat.toFixed(2) }} RMB</div>
        </template>
      </el-table-column>
      <el-table-column prop="profit_per_hour" label="钻石/小时" width="110" />
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > 20"
      style="margin-top: 16px; justify-content: flex-end"
      layout="prev, pager, next, total"
      :total="total"
      :page-size="20"
      :current-page="page"
      @current-change="(p: number) => { page = p; fetch() }"
    />

    <!-- 新增 / 编辑副本记录 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="720px" top="4vh">
      <el-form label-width="90px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="副本" required>
              <el-select v-model="form.dungeon_id" style="width: 100%">
                <el-option v-for="d in dungeonOptions" :key="d.id" :label="d.name" :value="d.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="开始时间">
              <el-date-picker v-model="form.started_at" type="datetime" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="赶路(分)">
              <el-input-number v-model="form.travel_minutes" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="战斗(分)">
              <el-input-number v-model="form.combat_minutes" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="死亡次数">
              <el-input-number v-model="form.death_count" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">掉落</el-divider>
        <div class="add-row">
          <el-select v-model="currentLoot.item_id" filterable placeholder="搜索物品" style="flex: 1">
            <el-option v-for="i in items" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
          <el-input-number v-model="currentLoot.quantity" :min="1" />
          <el-button type="primary" @click="addLoot">添加</el-button>
        </div>
        <el-tag v-for="(l, idx) in form.loots" :key="idx" closable @close="form.loots.splice(idx, 1)" style="margin: 4px">
          {{ itemName(l.item_id) }} ×{{ l.quantity }}
        </el-tag>

        <el-divider content-position="left">消耗品</el-divider>
        <div class="add-row">
          <el-select v-model="currentConsumption.item_id" filterable placeholder="搜索物品" style="flex: 1">
            <el-option v-for="i in items" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
          <el-input-number v-model="currentConsumption.quantity" :min="1" />
          <el-button type="primary" @click="addConsumption">添加</el-button>
        </div>
        <el-tag v-for="(c, idx) in form.consumptions" :key="idx" closable @close="form.consumptions.splice(idx, 1)" style="margin: 4px">
          {{ itemName(c.item_id) }} ×{{ c.quantity }}
        </el-tag>

        <el-divider content-position="left">维修</el-divider>
        <div class="add-row">
          <el-select v-model="currentRepair.equipment_id" filterable placeholder="选择装备（按模板自动计算材料）" style="flex: 1">
            <el-option v-for="e in equipments" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
          <el-button type="primary" @click="addRepair">添加</el-button>
        </div>
        <el-tag v-for="(r, idx) in form.repairs" :key="idx" closable @close="form.repairs.splice(idx, 1)" style="margin: 4px">
          维修：{{ r.equipment_id ? (equipments.find((e) => e.id === r.equipment_id)?.name) : itemName(r.item_id) + ' ×' + r.quantity }}
        </el-tag>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存并计算收益</el-button>
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
.loot-imgs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.loot-img-wrap {
  position: relative;
  width: 40px;
  height: 40px;
}
.loot-img {
  width: 40px;
  height: 40px;
  object-fit: contain;
  border: 1px solid #eef0f3;
  border-radius: 6px;
  background: #f7f8fa;
}
.loot-ph {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #eef0f3;
  border-radius: 6px;
  background: #f7f8fa;
  color: #c0c4cc;
  font-weight: 600;
}
.loot-qty {
  position: absolute;
  right: -4px;
  bottom: -4px;
  font-size: 10px;
  background: #3b82f6;
  color: #fff;
  border-radius: 8px;
  padding: 0 4px;
  line-height: 14px;
}
</style>
