import api from './api'
import type { SupplyPlan, CreateSupplyPlanRequest, PaginatedResponse } from '@/types'

export interface SupplyFilters {
  page?: number
  page_size?: number
  product_id?: number
  status?: string
  location?: string
  period_start?: string
  period_end?: string
}

export const supplyService = {
  async getPlans(filters: SupplyFilters = {}): Promise<PaginatedResponse<SupplyPlan>> {
    const res = await api.get<PaginatedResponse<SupplyPlan>>('/supply/plans', { params: filters })
    return res.data
  },

  async getPlan(id: number): Promise<SupplyPlan> {
    const res = await api.get<SupplyPlan>(`/supply/plans/${id}`)
    return res.data
  },

  async createPlan(data: CreateSupplyPlanRequest): Promise<SupplyPlan> {
    const res = await api.post<SupplyPlan>('/supply/plans', data)
    return res.data
  },

  async updatePlan(id: number, data: Partial<CreateSupplyPlanRequest>): Promise<SupplyPlan> {
    const res = await api.put<SupplyPlan>(`/supply/plans/${id}`, data)
    return res.data
  },

  async deletePlan(id: number): Promise<void> {
    await api.delete(`/supply/plans/${id}`)
  },

  async submitPlan(id: number): Promise<SupplyPlan> {
    const res = await api.post<SupplyPlan>(`/supply/plans/${id}/submit`)
    return res.data
  },

  async approvePlan(id: number): Promise<SupplyPlan> {
    const res = await api.post<SupplyPlan>(`/supply/plans/${id}/approve`)
    return res.data
  },

  async rejectPlan(id: number, reason?: string): Promise<SupplyPlan> {
    const res = await api.post<SupplyPlan>(`/supply/plans/${id}/reject`, { reason })
    return res.data
  },

  async getGapAnalysis(params?: { period_start?: string; period_end?: string }) {
    const res = await api.get('/supply/gap-analysis', { params })
    return res.data
  },
}
