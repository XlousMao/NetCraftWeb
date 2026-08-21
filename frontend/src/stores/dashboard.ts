import { defineStore } from 'pinia'
import { dashboardApi } from '@/api'
import type { DashboardData } from '@/types'

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    data: null as DashboardData | null,
    loading: false,
  }),
  actions: {
    async fetch() {
      this.loading = true
      try {
        const { data } = await dashboardApi.get()
        this.data = data
      } finally {
        this.loading = false
      }
    },
  },
})
