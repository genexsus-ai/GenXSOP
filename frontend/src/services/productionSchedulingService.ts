import api from './api'
import type {
  AgenticScheduleEventRequest,
  AgenticScheduleRecommendationResponse,
  AgenticScheduleRecommendationView,
  GenerateProductionScheduleRequest,
  ProductionCapacitySummary,
  ProductionSchedule,
  ProductionScheduleStatus,
} from '@/types'

export const productionSchedulingService = {
  recommendationStreamUrl(params?: {
    status?: 'pending_approval' | 'approved' | 'rejected'
    supply_plan_id?: number
    product_id?: number
  }): string {
    const token = localStorage.getItem('access_token')
    const basePath = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/$/, '')
    const absoluteBase = basePath.startsWith('http') ? basePath : `${window.location.origin}${basePath}`
    const url = new URL(`${absoluteBase}/production-scheduling/recommendations-stream`)
    if (params?.status) url.searchParams.set('status', params.status)
    if (params?.supply_plan_id) url.searchParams.set('supply_plan_id', String(params.supply_plan_id))
    if (params?.product_id) url.searchParams.set('product_id', String(params.product_id))
    if (token) url.searchParams.set('access_token', token)
    return url.toString()
  },

  async listSchedules(params?: {
    product_id?: number
    period?: string
    supply_plan_id?: number
    workcenter?: string
    line?: string
    shift?: string
    status?: string
  }): Promise<ProductionSchedule[]> {
    const res = await api.get<ProductionSchedule[]>('/production-scheduling/schedules', { params })
    return res.data
  },

  async generateSchedule(payload: GenerateProductionScheduleRequest): Promise<ProductionSchedule[]> {
    const res = await api.post<ProductionSchedule[]>('/production-scheduling/generate', payload)
    return res.data
  },

  async updateScheduleStatus(id: number, status: ProductionScheduleStatus): Promise<ProductionSchedule> {
    const res = await api.patch<ProductionSchedule>(`/production-scheduling/schedules/${id}/status`, { status })
    return res.data
  },

  async getCapacitySummary(supplyPlanId: number): Promise<ProductionCapacitySummary> {
    const res = await api.get<ProductionCapacitySummary>('/production-scheduling/capacity-summary', {
      params: { supply_plan_id: supplyPlanId },
    })
    return res.data
  },

  async resequenceSchedule(id: number, direction: 'up' | 'down'): Promise<ProductionSchedule[]> {
    const res = await api.post<ProductionSchedule[]>(`/production-scheduling/schedules/${id}/resequence`, { direction })
    return res.data
  },

  async getEventRecommendation(payload: AgenticScheduleEventRequest): Promise<AgenticScheduleRecommendationResponse> {
    const res = await api.post<AgenticScheduleRecommendationResponse>('/production-scheduling/events/recommendation', payload)
    return res.data
  },

  async listRecommendations(params?: {
    status?: 'pending_approval' | 'approved' | 'rejected'
    supply_plan_id?: number
    product_id?: number
  }): Promise<AgenticScheduleRecommendationView[]> {
    const res = await api.get<AgenticScheduleRecommendationView[]>('/production-scheduling/recommendations', { params })
    return res.data
  },

  async approveRecommendation(
    recommendationId: string,
    note?: string,
  ): Promise<AgenticScheduleRecommendationView> {
    const res = await api.post<AgenticScheduleRecommendationView>(
      `/production-scheduling/recommendations/${recommendationId}/approve`,
      { note },
    )
    return res.data
  },

  async rejectRecommendation(
    recommendationId: string,
    note?: string,
  ): Promise<AgenticScheduleRecommendationView> {
    const res = await api.post<AgenticScheduleRecommendationView>(
      `/production-scheduling/recommendations/${recommendationId}/reject`,
      { note },
    )
    return res.data
  },
}
