import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: '', name: 'dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: 'Dashboard' } },
        { path: 'items', name: 'items', component: () => import('@/views/Items.vue'), meta: { title: '物品库' } },
        { path: 'items/:id', name: 'item-detail', component: () => import('@/views/ItemDetail.vue'), meta: { title: '物品详情' } },
        { path: 'dungeons', name: 'dungeons', component: () => import('@/views/Dungeons.vue'), meta: { title: '副本' } },
        { path: 'dungeon-runs', name: 'dungeon-runs', component: () => import('@/views/DungeonRuns.vue'), meta: { title: '副本记录' } },
        { path: 'equipments', name: 'equipments', component: () => import('@/views/Equipments.vue'), meta: { title: '装备' } },
        { path: 'recipes', name: 'recipes', component: () => import('@/views/Recipes.vue'), meta: { title: '炼金/配方' } },
        { path: 'production', name: 'production', component: () => import('@/views/Production.vue'), meta: { title: '生产记录' } },
        { path: 'activities', name: 'activities', component: () => import('@/views/Activities.vue'), meta: { title: '活动' } },
        { path: 'analysis', name: 'analysis', component: () => import('@/views/Analysis.vue'), meta: { title: '周期分析' } },
        { path: 'currency', name: 'currency', component: () => import('@/views/Currency.vue'), meta: { title: '货币体系' } },
      ],
    },
  ],
})

router.afterEach((to) => {
  const title = to.meta?.title
  document.title = title ? `${title} · GEAP` : 'GEAP · 游戏经济分析平台'
})

export default router
