import { useEffect, useState } from 'react'
import { Plus, Play, CheckCircle, XCircle, GitBranch, TrendingUp, DollarSign } from 'lucide-react'
import { scenarioService } from '@/services/scenarioService'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Modal } from '@/components/common/Modal'
import { SkeletonCard } from '@/components/common/LoadingSpinner'
import { formatCurrency, formatPercent, formatDate } from '@/utils/formatters'
import type { Scenario, CreateScenarioRequest, ScenarioTradeoffSummary } from '@/types'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { can } from '@/auth/permissions'

const SCENARIO_TYPES = [
  { value: 'what_if', label: 'What-If Analysis' },
  { value: 'stress_test', label: 'Stress Test' },
  { value: 'baseline', label: 'Baseline' },
]

export function ScenariosPage() {
  const { user } = useAuthStore()
  const canWrite = can(user?.role, 'scenario.write')
  const canApprove = can(user?.role, 'scenario.approve')

  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  const [tradeoffByScenarioId, setTradeoffByScenarioId] = useState<Record<number, ScenarioTradeoffSummary>>({})
  const [form, setForm] = useState<Partial<CreateScenarioRequest>>({
    scenario_type: 'what_if',
    parameters: {
      period: new Date().toISOString().slice(0, 10),
      demand_change_pct: 0,
      supply_capacity_pct: 0,
      price_change_pct: 0,
      inventory_release_pct: 0,
    },
  })

  const scenarioParams = form.parameters ?? {}

  const setScenarioParam = (key: string, value: string | number) => {
    setForm((prev) => ({
      ...prev,
      parameters: {
        ...(prev.parameters ?? {}),
        [key]: value,
      },
    }))
  }

  const load = async () => {
    setLoading(true)
    try {
      const res = await scenarioService.getScenarios({ page_size: 50 })
      setScenarios(res.items)
      setTotal(res.total)

      const completed = res.items.filter((s) => s.status === 'completed' || s.status === 'approved')
      if (completed.length > 0) {
        const summaries = await Promise.all(
          completed.map(async (s) => {
            try {
              const summary = await scenarioService.getTradeoffSummary(s.id)
              return [s.id, summary] as const
            } catch {
              return null
            }
          })
        )
        const next: Record<number, ScenarioTradeoffSummary> = {}
        summaries.forEach((entry) => {
          if (entry) next[entry[0]] = entry[1]
        })
        setTradeoffByScenarioId(next)
      } else {
        setTradeoffByScenarioId({})
      }
    } catch {
      // handled
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleRun = async (id: number) => {
    setActionLoading(id)
    try {
      await scenarioService.runScenario(id)
      toast.success('Scenario executed successfully')
      load()
    } catch {
      // handled
    } finally {
      setActionLoading(null)
    }
  }

  const handleApprove = async (id: number) => {
    setActionLoading(id)
    try {
      await scenarioService.approveScenario(id)
      toast.success('Scenario approved')
      load()
    } catch {
      // handled
    } finally {
      setActionLoading(null)
    }
  }

  const handleCreate = async () => {
    if (!form.name) {
      toast.error('Please enter a scenario name')
      return
    }
    try {
      await scenarioService.createScenario({
        name: form.name!,
        description: form.description,
        scenario_type: form.scenario_type ?? 'what_if',
        parameters: {
          period: scenarioParams.period,
          demand_change_pct: Number(scenarioParams.demand_change_pct ?? 0),
          supply_capacity_pct: Number(scenarioParams.supply_capacity_pct ?? 0),
          price_change_pct: Number(scenarioParams.price_change_pct ?? 0),
          inventory_release_pct: Number(scenarioParams.inventory_release_pct ?? 0),
        },
      })
      toast.success('Scenario created')
      setShowCreate(false)
      setForm({
        scenario_type: 'what_if',
        parameters: {
          period: new Date().toISOString().slice(0, 10),
          demand_change_pct: 0,
          supply_capacity_pct: 0,
          price_change_pct: 0,
          inventory_release_pct: 0,
        },
      })
      load()
    } catch {
      // handled
    }
  }

  const typeColor: Record<string, string> = {
    what_if: 'bg-blue-50 text-blue-700',
    stress_test: 'bg-red-50 text-red-700',
    baseline: 'bg-gray-100 text-gray-700',
    best_case: 'bg-emerald-50 text-emerald-700',
    worst_case: 'bg-red-50 text-red-700',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Scenario Planning</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} scenarios</p>
        </div>
        {canWrite && (
          <Button icon={<Plus />} onClick={() => setShowCreate(true)}>
            New Scenario
          </Button>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => <SkeletonCard key={i} rows={4} />)}
        </div>
      ) : scenarios.length === 0 ? (
        <Card>
          <div className="text-center py-16 text-gray-400">
            <GitBranch className="h-10 w-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">No scenarios yet. Create your first scenario.</p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scenarios.map((scenario) => (
            <div key={scenario.id} className="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-gray-900 truncate">{scenario.name}</h3>
                  {scenario.description && (
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{scenario.description}</p>
                  )}
                </div>
                <StatusBadge status={scenario.status} size="sm" className="ml-2 flex-shrink-0" />
              </div>

              <div className="flex items-center gap-2 mb-4">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeColor[scenario.scenario_type] ?? 'bg-gray-100 text-gray-700'}`}>
                  {scenario.scenario_type.replace(/_/g, ' ')}
                </span>
                <span className="text-xs text-gray-400">{formatDate(scenario.created_at)}</span>
              </div>

              {/* Impact metrics */}
              {scenario.results && (
                <div className="grid grid-cols-2 gap-2 mb-4">
                  {scenario.revenue_impact != null && (
                    <div className="bg-gray-50 rounded-lg p-2">
                      <p className="text-xs text-gray-500 flex items-center gap-1">
                        <DollarSign className="h-3 w-3" /> Revenue
                      </p>
                      <p className={`text-sm font-semibold ${scenario.revenue_impact >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                        {scenario.revenue_impact >= 0 ? '+' : ''}{formatCurrency(scenario.revenue_impact)}
                      </p>
                    </div>
                  )}
                  {scenario.service_level_impact != null && (
                    <div className="bg-gray-50 rounded-lg p-2">
                      <p className="text-xs text-gray-500 flex items-center gap-1">
                        <TrendingUp className="h-3 w-3" /> Service Level
                      </p>
                      <p className={`text-sm font-semibold ${scenario.service_level_impact >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                        {scenario.service_level_impact >= 0 ? '+' : ''}{formatPercent(scenario.service_level_impact)}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {tradeoffByScenarioId[scenario.id]?.tradeoff && (
                <div className="grid grid-cols-2 gap-2 mb-4">
                  <div className="bg-gray-50 rounded-lg p-2">
                    <p className="text-xs text-gray-500">Carrying Cost</p>
                    <p className="text-sm font-semibold text-gray-900">
                      {formatCurrency(tradeoffByScenarioId[scenario.id].tradeoff!.inventory_carrying_cost)}
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-2">
                    <p className="text-xs text-gray-500">Working Capital Δ</p>
                    <p className="text-sm font-semibold text-gray-900">
                      {formatCurrency(tradeoffByScenarioId[scenario.id].tradeoff!.working_capital_delta)}
                    </p>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
                {canWrite && scenario.status === 'draft' && (
                  <Button size="sm" variant="secondary" icon={<Play />}
                    loading={actionLoading === scenario.id}
                    onClick={() => handleRun(scenario.id)}>
                    Run
                  </Button>
                )}
                {canApprove && scenario.status === 'submitted' && (
                  <>
                    <Button size="sm" variant="secondary" icon={<CheckCircle />}
                      loading={actionLoading === scenario.id}
                      onClick={() => handleApprove(scenario.id)}>
                      Approve
                    </Button>
                    <Button size="sm" variant="ghost" icon={<XCircle />}
                      onClick={() => scenarioService.rejectScenario(scenario.id).then(load)}>
                      Reject
                    </Button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create Scenario"
        footer={
          <>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!canWrite}>Create Scenario</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Scenario Name *</label>
            <input value={form.name ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Q2 Demand Surge +20%" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Type</label>
            <select value={form.scenario_type ?? 'what_if'}
              onChange={(e) => setForm((f) => ({ ...f, scenario_type: e.target.value as CreateScenarioRequest['scenario_type'] }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
              {SCENARIO_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Description</label>
            <textarea value={form.description ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              rows={3}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              placeholder="Describe the scenario assumptions..." />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Scenario Period</label>
            <input
              type="date"
              value={String(scenarioParams.period ?? '')}
              onChange={(e) => setScenarioParam('period', e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Demand Change (%)</label>
              <input
                type="number"
                value={Number(scenarioParams.demand_change_pct ?? 0)}
                onChange={(e) => setScenarioParam('demand_change_pct', Number(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Supply Capacity Change (%)</label>
              <input
                type="number"
                value={Number(scenarioParams.supply_capacity_pct ?? 0)}
                onChange={(e) => setScenarioParam('supply_capacity_pct', Number(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Price Change (%)</label>
              <input
                type="number"
                value={Number(scenarioParams.price_change_pct ?? 0)}
                onChange={(e) => setScenarioParam('price_change_pct', Number(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Inventory Release (%)</label>
              <input
                type="number"
                value={Number(scenarioParams.inventory_release_pct ?? 0)}
                onChange={(e) => setScenarioParam('inventory_release_pct', Number(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
