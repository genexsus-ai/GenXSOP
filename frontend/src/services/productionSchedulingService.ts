import api from './api'
import type {
  GenerateProductionScheduleRequest,
  ProductionCapacitySummary,
  ProductionSchedule,
  ProductionScheduleStatus,
} from '@/types'

export const productionSchedulingService = {
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
}
