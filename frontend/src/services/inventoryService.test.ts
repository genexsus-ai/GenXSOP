import { describe, expect, it, vi, beforeEach } from 'vitest'

// Mock the shared axios instance used by services
vi.mock('./api', () => {
  return {
    default: {
      get: vi.fn(),
      put: vi.fn(),
    },
  }
})

import api from './api'
import { inventoryService } from './inventoryService'

describe('inventoryService (normalization)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getInventory coerces Decimal-like string fields to numbers (paginated response)', async () => {
    (api.get as any).mockResolvedValue({
      data: {
        items: [
          {
            id: 1,
            product_id: 10,
            location: 'Main',
            on_hand_qty: '100.5',
            allocated_qty: '2',
            in_transit_qty: '0',
            safety_stock: '10',
            reorder_point: '5',
            max_stock: '200',
            days_of_supply: '12.3',
            valuation: '999.99',
            status: 'normal',
            updated_at: '2026-01-01T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
    })

    const res = await inventoryService.getInventory()
    expect(res.items).toHaveLength(1)
    expect(typeof res.items[0].days_of_supply).toBe('number')
    expect(res.items[0].days_of_supply).toBeCloseTo(12.3)
    expect(res.items[0].on_hand_qty).toBeCloseTo(100.5)
    expect(res.items[0].valuation).toBeCloseTo(999.99)
  })

  it('getInventory normalizes array response to PaginatedResponse and coerces numeric strings', async () => {
    (api.get as any).mockResolvedValue({
      data: [
        {
          id: 2,
          product_id: 11,
          location: 'Main',
          on_hand_qty: '10',
          allocated_qty: '0',
          in_transit_qty: '0',
          safety_stock: '5',
          reorder_point: '2',
          days_of_supply: null,
          valuation: null,
          status: 'low',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
    })

    const res = await inventoryService.getInventory({ page_size: 50 })
    expect(res.items).toHaveLength(1)
    expect(res.total).toBe(1)
    expect(res.page).toBe(1)
    expect(res.items[0].on_hand_qty).toBe(10)
  })
})
