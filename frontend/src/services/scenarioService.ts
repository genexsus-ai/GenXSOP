import api from './api'
import type { Scenario, CreateScenarioRequest, PaginatedResponse, ScenarioTradeoffSummary } from '@/types'

export const scenarioService = {
  async getScenarios(params?: { page?: number; page_size?: number; status?: string }): Promise<PaginatedResponse<Scenario>> {
    const res = await api.get<PaginatedResponse<Scenario>>('/scenarios', { params })
    return res.data
  },

  async getScenario(id: number): Promise<Scenario> {
    const res = await api.get<Scenario>(`/scenarios/${id}`)
    return res.data
  },

  async createScenario(data: CreateScenarioRequest): Promise<Scenario> {
    const res = await api.post<Scenario>('/scenarios', data)
    return res.data
  },

  async updateScenario(id: number, data: Partial<CreateScenarioRequest>): Promise<Scenario> {
    const res = await api.put<Scenario>(`/scenarios/${id}`, data)
    return res.data
  },

  async deleteScenario(id: number): Promise<void> {
    await api.delete(`/scenarios/${id}`)
  },

  async runScenario(id: number): Promise<Scenario> {
    const res = await api.post<Scenario>(`/scenarios/${id}/run`)
    return res.data
  },

  async submitScenario(id: number): Promise<Scenario> {
    const res = await api.post<Scenario>(`/scenarios/${id}/submit`)
    return res.data
  },

  async approveScenario(id: number): Promise<Scenario> {
    const res = await api.post<Scenario>(`/scenarios/${id}/approve`)
    return res.data
  },

  async rejectScenario(id: number, reason?: string): Promise<Scenario> {
    const res = await api.post<Scenario>(`/scenarios/${id}/reject`, { reason })
    return res.data
  },

  async compareScenarios(ids: number[]) {
    const res = await api.post('/scenarios/compare', { scenario_ids: ids })
    return res.data
  },

  async getTradeoffSummary(id: number): Promise<ScenarioTradeoffSummary> {
    const res = await api.get<ScenarioTradeoffSummary>(`/scenarios/${id}/tradeoff-summary`)
    return res.data
  },
}
