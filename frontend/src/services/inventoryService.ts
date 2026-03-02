import api from './api'
import type {
  Inventory,
  UpdateInventoryRequest,
  PaginatedResponse,
  InventoryOptimizationRunRequest,
  InventoryOptimizationRunResponse,
  InventoryException,
  InventoryPolicyOverrideRequest,
  InventoryExceptionUpdateRequest,
  InventoryRecommendationGenerateRequest,
  InventoryPolicyRecommendation,
  InventoryRecommendationDecisionRequest,
  InventoryRebalanceRecommendation,
  InventoryAutoApplyRequest,
  InventoryAutoApplyResponse,
  InventoryControlTowerSummary,
} from '@/types'

/**
 * Backend uses Decimal for numeric fields which may serialize as strings.
 * Normalize to numbers so UI formatting (toFixed, arithmetic) never crashes.
 */
function toNumber(v: unknown): number | undefined {
  if (v === null || v === undefined) return undefined
  if (typeof v === 'number') return Number.isFinite(v) ? v : undefined
  if (typeof v === 'string' && v.trim() !== '') {
    const n = Number(v)
    return Number.isFinite(n) ? n : undefined
  }
  return undefined
}

function normalizeInventory(raw: any): Inventory {
  return {
    ...raw,
    on_hand_qty: toNumber(raw?.on_hand_qty) ?? 0,
    allocated_qty: toNumber(raw?.allocated_qty) ?? 0,
    in_transit_qty: toNumber(raw?.in_transit_qty) ?? 0,
    safety_stock: toNumber(raw?.safety_stock) ?? 0,
    reorder_point: toNumber(raw?.reorder_point) ?? 0,
    max_stock: toNumber(raw?.max_stock),
    days_of_supply: toNumber(raw?.days_of_supply),
    valuation: toNumber(raw?.valuation),
  } as Inventory
}

function normalizePaginated(data: PaginatedResponse<any>): PaginatedResponse<Inventory> {
  return {
    ...data,
    items: Array.isArray((data as any).items) ? (data as any).items.map(normalizeInventory) : [],
  }
}

function normalizeRecommendation(raw: any): InventoryPolicyRecommendation {
  return {
    ...raw,
    recommended_safety_stock: toNumber(raw?.recommended_safety_stock) ?? 0,
    recommended_reorder_point: toNumber(raw?.recommended_reorder_point) ?? 0,
    recommended_max_stock: toNumber(raw?.recommended_max_stock),
    confidence_score: toNumber(raw?.confidence_score) ?? 0,
  } as InventoryPolicyRecommendation
}

function normalizeRebalance(raw: any): InventoryRebalanceRecommendation {
  return {
    ...raw,
    transfer_qty: toNumber(raw?.transfer_qty) ?? 0,
    estimated_service_uplift_pct: toNumber(raw?.estimated_service_uplift_pct) ?? 0,
  } as InventoryRebalanceRecommendation
}

export const inventoryService = {
  async getInventory(params?: { page?: number; page_size?: number; status?: string; product_id?: number }): Promise<PaginatedResponse<Inventory>> {
    const res = await api.get<PaginatedResponse<Inventory> | Inventory[]>('/inventory', { params })
    const data = res.data as any

    // Normalize for safety: historically some endpoints may return list directly.
    if (Array.isArray(data)) {
      return {
        items: data.map(normalizeInventory),
        total: data.length,
        page: params?.page ?? 1,
        page_size: params?.page_size ?? data.length,
        total_pages: 1,
      }
    }

    return normalizePaginated(data)
  },

  async getByProduct(productId: number): Promise<Inventory> {
    const res = await api.get<Inventory>(`/inventory/${productId}`)
    return normalizeInventory(res.data)
  },

  async updateInventory(id: number, data: UpdateInventoryRequest): Promise<Inventory> {
    const res = await api.put<Inventory>(`/inventory/${id}`, data)
    return normalizeInventory(res.data)
  },

  async runOptimization(payload: InventoryOptimizationRunRequest): Promise<InventoryOptimizationRunResponse> {
    const res = await api.post<InventoryOptimizationRunResponse>('/inventory/optimization/runs', payload)
    return res.data
  },

  async getExceptions(params?: { product_id?: number; location?: string; status?: string; owner_user_id?: number }): Promise<InventoryException[]> {
    const res = await api.get<InventoryException[]>('/inventory/exceptions', { params })
    return res.data
  },

  async updateException(id: number, payload: InventoryExceptionUpdateRequest): Promise<InventoryException> {
    const res = await api.patch<InventoryException>(`/inventory/exceptions/${id}`, payload)
    return res.data
  },

  async generateRecommendations(payload: InventoryRecommendationGenerateRequest): Promise<InventoryPolicyRecommendation[]> {
    const res = await api.post<InventoryPolicyRecommendation[]>('/inventory/recommendations/generate', payload)
    return (res.data || []).map(normalizeRecommendation)
  },

  async getRecommendations(params?: { status?: string; inventory_id?: number; product_id?: number; location?: string }): Promise<InventoryPolicyRecommendation[]> {
    const res = await api.get<InventoryPolicyRecommendation[]>('/inventory/recommendations', { params })
    return (res.data || []).map(normalizeRecommendation)
  },

  async decideRecommendation(id: number, payload: InventoryRecommendationDecisionRequest): Promise<InventoryPolicyRecommendation> {
    const res = await api.post<InventoryPolicyRecommendation>(`/inventory/recommendations/${id}/decision`, payload)
    return normalizeRecommendation(res.data)
  },

  async getRebalanceRecommendations(params?: { product_id?: number; min_transfer_qty?: number }): Promise<InventoryRebalanceRecommendation[]> {
    const res = await api.get<InventoryRebalanceRecommendation[]>('/inventory/rebalance/recommendations', { params })
    return (res.data || []).map(normalizeRebalance)
  },

  async autoApplyRecommendations(payload: InventoryAutoApplyRequest): Promise<InventoryAutoApplyResponse> {
    const res = await api.post<InventoryAutoApplyResponse>('/inventory/recommendations/auto-apply', payload)
    return res.data
  },

  async getControlTowerSummary(): Promise<InventoryControlTowerSummary> {
    const res = await api.get<InventoryControlTowerSummary>('/inventory/control-tower/summary')
    return res.data
  },

  async overridePolicy(id: number, payload: InventoryPolicyOverrideRequest): Promise<Inventory> {
    const res = await api.put<Inventory>(`/inventory/policies/${id}/override`, payload)
    return normalizeInventory(res.data)
  },

  async getHealth() {
    const res = await api.get('/inventory/health')
    return res.data
  },

  async getAlerts() {
    const res = await api.get('/inventory/alerts')
    return res.data
  },
}
