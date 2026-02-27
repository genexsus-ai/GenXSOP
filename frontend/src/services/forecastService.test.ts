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
import { forecastService } from './forecastService'

describe('forecastService (normalization)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getResults normalizes backend array response to PaginatedResponse', async () => {
    (api.get as any).mockResolvedValue({
      data: [
        {
          id: 1,
          product_id: 10,
          model_type: 'arima',
          period: '2026-01-01',
          predicted_qty: 123,
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    })

    const res = await forecastService.getResults({ page_size: 50 })
    expect(res.items).toHaveLength(1)
    expect(res.total).toBe(1)
    expect(res.page).toBe(1)
  })

  it('getAccuracy normalizes backend avg_mape response to ForecastAccuracy[]', async () => {
    (api.get as any).mockResolvedValue({
      data: [{ model_type: 'ml_ensemble', avg_mape: 12.34, sample_count: 6 }],
    })

    const res = await forecastService.getAccuracy()
    expect(res).toHaveLength(1)
    expect(res[0].model_type).toBe('ml_ensemble')
    expect(res[0].mape).toBe(12.34)
    expect(res[0].wape).toBe(0)
    expect(res[0].bias).toBe(0)
    expect(res[0].period_count).toBe(6)
  })

  it('generateForecast calls backend with query params and maps response to Forecast[]', async () => {
    (api.post as any).mockResolvedValue({
      data: {
        product_id: 1,
        model_type: 'prophet',
        horizon: 2,
        diagnostics: {
          selected_model: 'prophet',
          selection_reason: 'Best backtest score',
          advisor_confidence: 0.82,
          advisor_enabled: true,
          fallback_used: false,
        },
        forecasts: [
          { period: '2026-02-01', predicted_qty: 100, lower_bound: 90, upper_bound: 110, confidence: 80 },
          { period: '2026-03-01', predicted_qty: 120, lower_bound: 105, upper_bound: 130, confidence: 80 },
        ],
      },
    })

    const res = await forecastService.generateForecast({ product_id: 1, model_type: 'prophet', horizon_months: 2 })
    expect(api.post).toHaveBeenCalledWith(
      '/forecasting/generate',
      null,
      expect.objectContaining({ params: expect.objectContaining({ product_id: 1, horizon: 2, model_type: 'prophet' }) }),
    )
    expect(res.forecasts).toHaveLength(2)
    expect(res.forecasts[0].model_type).toBe('prophet')
    expect(res.forecasts[0].predicted_qty).toBe(100)
    expect(res.diagnostics?.selected_model).toBe('prophet')
  })
})
