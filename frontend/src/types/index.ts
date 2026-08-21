export interface Item {
  id: number
  name: string
  display_name?: string
  category?: string
  subcategory?: string
  description?: string
  icon_url?: string
  rarity?: string
  level?: number
  stack_size?: number
  tags: string[]
  roles: string[]
  vendor_buy_price?: number
  market_price?: number
  manual_price?: number
  importance_score: number
  is_active: boolean
  created_at: string
  updated_at: string
  image_count: number
  relation_count: number
}

export interface Dungeon {
  id: number
  name: string
  description?: string
  is_active: boolean
}

export interface DungeonRun {
  id: number
  dungeon_id: number
  dungeon_name?: string
  started_at: string
  ended_at?: string
  travel_minutes: number
  combat_minutes: number
  death_count: number
  total_duration_minutes: number
  gross_value: number
  repair_cost: number
  consumable_cost: number
  other_cost: number
  total_cost: number
  net_profit: number
  profit_per_hour: number
  gross_value_fiat?: number
  net_profit_fiat?: number
  profit_per_hour_fiat?: number
  loots: any[]
  consumptions: any[]
}

export interface Recipe {
  id: number
  name: string
  category?: string
  expected_success_rate: number
  materials: any[]
  outputs: any[]
}

export interface Equipment {
  id: number
  name: string
  repair_requirements: any[]
}

export interface PeriodAnalysis {
  start: string
  end: string
  run_count: number
  total_gross: number
  total_repair: number
  total_consumable: number
  total_other: number
  total_cost: number
  net_profit: number
  total_duration_minutes: number
  profit_per_hour: number
  gross_value_fiat: number
  net_profit_fiat: number
  profit_per_hour_fiat: number
  cost_ratio: number
  cost_breakdown: { name: string; value: number }[]
  is_loss: boolean
}

export interface DashboardData {
  today: PeriodAnalysis
  week: PeriodAnalysis
  month: PeriodAnalysis
  top_dungeons: any[]
  top_recipes: any[]
  activities: any
  important_items: any[]
}
