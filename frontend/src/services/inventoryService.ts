import api from './api'
import type { Inventory, UpdateInventoryRequest, PaginatedResponse } from '@/types'

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

  async getHealth() {
    const res = await api.get('/inventory/health')
    return res.data
  },

  async getAlerts() {
    const res = await api.get('/inventory/alerts')
    return res.data
  },
}
