<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const menuItems = [
  { path: '/', title: 'Dashboard', icon: 'DataLine' },
  { path: '/items', title: '物品库', icon: 'Box' },
  { path: '/dungeons', title: '副本', icon: 'MagicStick' },
  { path: '/dungeon-runs', title: '副本记录', icon: 'Tickets' },
  { path: '/equipments', title: '装备', icon: 'Sword' },
  { path: '/recipes', title: '炼金/配方', icon: 'Potion' },
  { path: '/production', title: '生产记录', icon: 'Cpu' },
  { path: '/activities', title: '活动', icon: 'Calendar' },
  { path: '/analysis', title: '周期分析', icon: 'TrendCharts' },
  { path: '/currency', title: '货币体系', icon: 'Coin' },
  { path: '/craft-analysis', title: '制作分析', icon: 'Aim' },
]

const activePath = ref(route.path)
function navigate(path: string) {
  activePath.value = path
  router.push(path)
}
</script>

<template>
  <el-container style="height: 100%">
    <el-aside width="220px" class="sidebar">
      <div class="brand">
        <div class="brand-logo">G</div>
        <div class="brand-text">
          <div class="brand-name">GEAP</div>
          <div class="brand-sub">游戏经济分析平台</div>
        </div>
      </div>
      <el-menu :default-active="activePath" class="menu" @select="navigate">
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-main style="padding: 0; overflow-y: auto">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.sidebar {
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 20px 16px;
  border-bottom: 1px solid #f0f1f3;
}
.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #3b82f6;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
}
.brand-name {
  font-weight: 700;
  font-size: 16px;
}
.brand-sub {
  font-size: 11px;
  color: #909399;
}
.menu {
  border-right: none;
  flex: 1;
}
</style>
