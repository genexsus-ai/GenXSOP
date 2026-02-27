import api from './api'
import type { DemandPlan, CreateDemandPlanRequest, PaginatedResponse } from '@/types'

export interface DemandFilters {
  page?: number
  page_size?: number
  product_id?: number
  status?: string
  region?: string
  period_start?: string
  period_end?: string
}

export const demandService = {
  async getPlans(filters: DemandFilters = {}): Promise<PaginatedResponse<DemandPlan>> {
    const res = await api.get<PaginatedResponse<DemandPlan>>('/demand/plans', { params: filters })
    return res.data
  },

  async getPlan(id: number): Promise<DemandPlan> {
    const res = await api.get<DemandPlan>(`/demand/plans/${id}`)
    return res.data
  },

  async createPlan(data: CreateDemandPlanRequest): Promise<DemandPlan> {
    const res = await api.post<DemandPlan>('/demand/plans', data)
    return res.data
  },

  async updatePlan(id: number, data: Partial<CreateDemandPlanRequest>): Promise<DemandPlan> {
    const res = await api.put<DemandPlan>(`/demand/plans/${id}`, data)
    return res.data
  },

  async deletePlan(id: number): Promise<void> {
    await api.delete(`/demand/plans/${id}`)
  },

  async submitPlan(id: number): Promise<DemandPlan> {
    const res = await api.post<DemandPlan>(`/demand/plans/${id}/submit`)
    return res.data
  },

  async approvePlan(id: number): Promise<DemandPlan> {
    const res = await api.post<DemandPlan>(`/demand/plans/${id}/approve`)
    return res.data
  },

  async rejectPlan(id: number, reason?: string): Promise<DemandPlan> {
    const res = await api.post<DemandPlan>(`/demand/plans/${id}/reject`, { reason })
    return res.data
  },
}
