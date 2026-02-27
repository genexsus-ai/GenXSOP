import api from './api'
import type { SOPCycle, CreateSOPCycleRequest, PaginatedResponse } from '@/types'

export const sopService = {
  async getCycles(params?: { page?: number; page_size?: number; status?: string }): Promise<PaginatedResponse<SOPCycle>> {
    const res = await api.get<PaginatedResponse<SOPCycle>>('/sop-cycles', { params })
    return res.data
  },

  async getCycle(id: number): Promise<SOPCycle> {
    const res = await api.get<SOPCycle>(`/sop-cycles/${id}`)
    return res.data
  },

  async createCycle(data: CreateSOPCycleRequest): Promise<SOPCycle> {
    const res = await api.post<SOPCycle>('/sop-cycles', data)
    return res.data
  },

  async updateCycle(id: number, data: Partial<CreateSOPCycleRequest>): Promise<SOPCycle> {
    const res = await api.put<SOPCycle>(`/sop-cycles/${id}`, data)
    return res.data
  },

  async advanceCycle(id: number, notes?: string): Promise<SOPCycle> {
    const res = await api.post<SOPCycle>(`/sop-cycles/${id}/advance`, { notes })
    return res.data
  },

  async completeCycle(id: number, decisions?: string): Promise<SOPCycle> {
    const res = await api.post<SOPCycle>(`/sop-cycles/${id}/complete`, { decisions })
    return res.data
  },
}
