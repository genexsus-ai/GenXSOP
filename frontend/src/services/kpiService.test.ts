import { describe, expect, it, vi, beforeEach } from 'vitest'

// Mock the shared axios instance used by services
vi.mock('./api', () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
    },
  }
})

import api from './api'
import { kpiService } from './kpiService'

describe('kpiService (normalization)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getMetrics normalizes Decimal-like string fields to numbers (paginated response)', async () => {
    (api.get as any).mockResolvedValue({
      data: {
        items: [
          {
            id: 1,
            metric_name: 'forecast_accuracy',
            metric_category: 'demand',
            period: '2026-02-01',
            value: '87.3',
            target: '90.0',
            variance_pct: '-3.0',
            created_at: '2026-02-01T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
    })

    const res = await kpiService.getMetrics()
    expect(res.items).toHaveLength(1)
    expect(typeof res.items[0].value).toBe('number')
    expect(res.items[0].value).toBeCloseTo(87.3)
    expect(res.items[0].target).toBeCloseTo(90)
    expect(res.items[0].variance_pct).toBeCloseTo(-3)
  })

  it('getMetrics normalizes array response to PaginatedResponse and converts numeric strings', async () => {
    (api.get as any).mockResolvedValue({
      data: [
        {
          id: 2,
          metric_name: 'otif',
          metric_category: 'service',
          period: '2026-02-01',
          value: '94.2',
          unit: '%',
          created_at: '2026-02-01T00:00:00Z',
        },
      ],
    })

    const res = await kpiService.getMetrics({ page_size: 50 })
    expect(res.items).toHaveLength(1)
    expect(res.total).toBe(1)
    expect(res.page).toBe(1)
    expect(res.items[0].value).toBeCloseTo(94.2)
  })
})
