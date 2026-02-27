import { useEffect, useState } from 'react'
import {
  TrendingUp, Package, BarChart3,
  AlertTriangle, CheckCircle, Clock, ArrowRight,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { dashboardService } from '@/services/dashboardService'
import { KPICard } from '@/components/common/KPICard'
import { Card } from '@/components/common/Card'
import { StatusBadge } from '@/components/common/StatusBadge'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { formatCurrency, formatPercent, formatDate } from '@/utils/formatters'
import type { DashboardSummary, DashboardAlert } from '@/types'

function safePercent(value?: number | null): string {
  return typeof value === 'number' ? formatPercent(value) : '—'
}

export function DashboardPage() {
  const navigate = useNavigate()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [alerts, setAlerts] = useState<DashboardAlert[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [s, a] = await Promise.all([
          dashboardService.getSummary(),
          dashboardService.getAlerts(),
        ])
        setSummary(s)
        setAlerts(a)
      } catch {
        // handled by interceptor
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" message="Loading dashboard..." />
      </div>
    )
  }

  const alertIcon = (severity: string) => {
    if (severity === 'critical') return <AlertTriangle className="h-4 w-4 text-red-500" />
    if (severity === 'warning') return <AlertTriangle className="h-4 w-4 text-amber-500" />
    return <CheckCircle className="h-4 w-4 text-blue-500" />
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">S&OP overview and key metrics</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Forecast Accuracy"
          value={safePercent(summary?.forecast_accuracy)}
          trend={summary && summary.forecast_accuracy >= 85 ? 'up' : 'down'}
          change={summary?.forecast_accuracy_change}
          changeLabel="vs last month"
          icon={<TrendingUp className="h-4 w-4" />}
          color="blue"
          onClick={() => navigate('/forecasting')}
        />
        <KPICard
          title="On-Time In-Full"
          value={safePercent(summary?.otif_rate)}
          trend={summary && summary.otif_rate >= 90 ? 'up' : 'down'}
          change={summary?.otif_change}
          changeLabel="vs last month"
          icon={<CheckCircle className="h-4 w-4" />}
          color="emerald"
          onClick={() => navigate('/kpi')}
        />
        <KPICard
          title="Inventory Value"
          value={typeof summary?.total_inventory_value === 'number' ? formatCurrency(summary.total_inventory_value) : '—'}
          icon={<Package className="h-4 w-4" />}
          color="purple"
          subtitle={summary ? `${summary.low_stock_count} low stock alerts` : undefined}
          onClick={() => navigate('/inventory')}
        />
        <KPICard
          title="Active S&OP Cycle"
          value={summary?.active_sop_cycle ?? 'None'}
          icon={<Clock className="h-4 w-4" />}
          color="amber"
          subtitle={summary?.sop_cycle_stage ? `Stage: ${summary.sop_cycle_stage}` : undefined}
          onClick={() => navigate('/sop-cycle')}
        />
      </div>

      {/* Second row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Alerts */}
        <Card
          title="Active Alerts"
          subtitle={`${alerts.length} items requiring attention`}
          className="lg:col-span-1"
          actions={
            <button
              onClick={() => navigate('/kpi')}
              className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              View all <ArrowRight className="h-3 w-3" />
            </button>
          }
        >
          {alerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-gray-400">
              <CheckCircle className="h-8 w-8 mb-2" />
              <p className="text-sm">No active alerts</p>
            </div>
          ) : (
            <ul className="space-y-3">
              {alerts.slice(0, 6).map((alert, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="mt-0.5 flex-shrink-0">{alertIcon(alert.severity)}</span>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-gray-800 truncate">{alert.title}</p>
                    <p className="text-xs text-gray-500 truncate">{alert.message}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Quick stats */}
        <Card title="Planning Status" className="lg:col-span-2">
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'Demand Plans', value: summary?.demand_plans_count ?? 0, status: 'active', path: '/demand' },
              { label: 'Supply Plans', value: summary?.supply_plans_count ?? 0, status: 'active', path: '/supply' },
              { label: 'Open Scenarios', value: summary?.open_scenarios_count ?? 0, status: 'draft', path: '/scenarios' },
              { label: 'Products Tracked', value: summary?.products_count ?? 0, status: 'normal', path: '/products' },
            ].map(({ label, value, status, path }) => (
              <button
                key={label}
                onClick={() => navigate(path)}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors text-left"
              >
                <div>
                  <p className="text-xs text-gray-500">{label}</p>
                  <p className="text-xl font-bold text-gray-900 mt-0.5">{value}</p>
                </div>
                <StatusBadge status={status} size="sm" />
              </button>
            ))}
          </div>
        </Card>
      </div>

      {/* Recent activity */}
      <Card
        title="Recent Activity"
        actions={
          <button className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
            View all <ArrowRight className="h-3 w-3" />
          </button>
        }
      >
        {summary?.recent_activity && summary.recent_activity.length > 0 ? (
          <div className="space-y-3">
            {summary.recent_activity.map((item, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
                <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <BarChart3 className="h-4 w-4 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-800">{item.description}</p>
                  <p className="text-xs text-gray-400">{formatDate(item.created_at)}</p>
                </div>
                <StatusBadge status={item.status} size="sm" />
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400 text-center py-6">No recent activity</p>
        )}
      </Card>
    </div>
  )
}
