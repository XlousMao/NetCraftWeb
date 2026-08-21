import client from './client'

// ---- Items ----
export const itemApi = {
  list: (params: any) => client.get('/items', { params }),
  get: (id: number) => client.get(`/items/${id}`),
  create: (data: any) => client.post('/items', data),
  update: (id: number, data: any) => client.patch(`/items/${id}`, data),
  remove: (id: number) => client.delete(`/items/${id}`),
  categories: () => client.get('/items/categories'),
  uploadImage: (id: number, formData: FormData) =>
    client.post(`/items/${id}/images`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  pasteImage: (id: number, blob: Blob) =>
    client.post(`/items/${id}/images/paste`, blob, {
      headers: { 'Content-Type': 'application/octet-stream' },
    }),
  getPrices: (id: number) => client.get(`/items/${id}/prices`),
  recordPrice: (id: number, data: any) => client.post(`/items/${id}/prices`, data),
  relationGraph: (id: number, depth = 2) =>
    client.get(`/items/${id}/relation-graph`, { params: { depth } }),
}

// ---- Dungeons ----
export const dungeonApi = {
  list: (includeInactive = false) =>
    client.get('/dungeons', { params: { include_inactive: includeInactive } }),
  create: (data: any) => client.post('/dungeons', data),
  get: (id: number) => client.get(`/dungeons/${id}`),
  update: (id: number, data: any) => client.patch(`/dungeons/${id}`, data),
  remove: (id: number) => client.delete(`/dungeons/${id}`),
}

export const dungeonRunApi = {
  list: (params: any) => client.get('/dungeon-runs', { params }),
  create: (data: any) => client.post('/dungeon-runs', data),
  get: (id: number) => client.get(`/dungeon-runs/${id}`),
  update: (id: number, data: any) => client.put(`/dungeon-runs/${id}`, data),
  remove: (id: number) => client.delete(`/dungeon-runs/${id}`),
}

// ---- Equipments ----
export const equipmentApi = {
  list: (includeInactive = false) =>
    client.get('/equipments', { params: { include_inactive: includeInactive } }),
  create: (data: any) => client.post('/equipments', data),
  get: (id: number) => client.get(`/equipments/${id}`),
  update: (id: number, data: any) => client.patch(`/equipments/${id}`, data),
  remove: (id: number) => client.delete(`/equipments/${id}`),
}

// ---- Recipes ----
export const recipeApi = {
  list: (includeInactive = false) =>
    client.get('/recipes', { params: { include_inactive: includeInactive } }),
  create: (data: any) => client.post('/recipes', data),
  get: (id: number) => client.get(`/recipes/${id}`),
  update: (id: number, data: any) => client.put(`/recipes/${id}`, data),
  remove: (id: number) => client.delete(`/recipes/${id}`),
  analysis: (id: number) => client.get(`/recipes/${id}/analysis`),
}

export const productionApi = {
  list: (params: any) => client.get('/production-records', { params }),
  create: (data: any) => client.post('/production-records', data),
  update: (id: number, data: any) => client.put(`/production-records/${id}`, data),
  remove: (id: number) => client.delete(`/production-records/${id}`),
}

// ---- Activities ----
export const activityApi = {
  list: () => client.get('/activities'),
  records: (params: any) => client.get('/activities/records', { params }),
  createRecord: (data: any) => client.post('/activities/records', data),
  updateRecord: (id: number, data: any) => client.put(`/activities/records/${id}`, data),
  removeRecord: (id: number) => client.delete(`/activities/records/${id}`),
}

// ---- Analysis / Dashboard / AI ----
export const analysisApi = {
  period: (params: any) => client.get('/analysis/period', { params }),
  dungeonRankings: (params: any) => client.get('/analysis/dungeon-rankings', { params }),
  recipeRankings: () => client.get('/analysis/recipe-rankings'),
  activityEfficiency: (params: any) => client.get('/analysis/activity-efficiency', { params }),
  value: (data: any) => client.post('/analysis/value', data),
}

export const dashboardApi = {
  get: () => client.get('/dashboard'),
}

export const aiApi = {
  analyze: (question?: string) => client.post('/ai/analyze', { question }),
}

// ---- Currency / Fiat ----
export const currencyApi = {
  systems: () => client.get('/currency/systems'),
  summary: () => client.get('/currency/summary'),
  convert: (data: any) => client.post('/currency/convert', data),
  listFiat: () => client.get('/currency/fiat'),
  recordFiat: (data: any) => client.post('/currency/fiat', data),
}
