import { useEffect, useMemo, useState } from 'react'
import { RefreshCw } from 'lucide-react'

import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { SkeletonTable } from '@/components/common/LoadingSpinner'
import { StatusBadge } from '@/components/common/StatusBadge'
import { formatNumber, formatPercent, formatPeriod } from '@/utils/formatters'
import { supplyService } from '@/services/supplyService'
import { productionSchedulingService } from '@/services/productionSchedulingService'
import type {
  ProductionCapacitySummary,
  ProductionSchedule,
  ProductionScheduleStatus,
  SupplyPlan,
} from '@/types'
import toast from 'react-hot-toast'

const SHIFT_OPTIONS = ['Shift-A', 'Shift-B', 'Shift-C']
const STATUS_OPTIONS: ProductionScheduleStatus[] = ['draft', 'released', 'in_progress', 'completed']

export function ProductionSchedulingPage() {
  const [supplyPlans, setSupplyPlans] = useState<SupplyPlan[]>([])
  const [selectedSupplyPlanId, setSelectedSupplyPlanId] = useState<number | undefined>(undefined)
  const [workcenters, setWorkcenters] = useState('WC-1')
  const [lines, setLines] = useState('Line-1')
  const [selectedShifts, setSelectedShifts] = useState<string[]>(['Shift-A', 'Shift-B'])
  const [durationHours, setDurationHours] = useState(8)

  const [rows, setRows] = useState<ProductionSchedule[]>([])
  const [capacitySummary, setCapacitySummary] = useState<ProductionCapacitySummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [statusUpdatingId, setStatusUpdatingId] = useState<number | null>(null)

  const selectedPlan = useMemo(
    () => supplyPlans.find((p) => p.id === selectedSupplyPlanId),
    [supplyPlans, selectedSupplyPlanId],
  )

  const loadSupplyPlans = async () => {
    try {
      const first = await supplyService.getPlans({ page: 1, page_size: 100 })
      let all = [...first.items]
      for (let page = 2; page <= first.total_pages; page += 1) {
        const next = await supplyService.getPlans({ page, page_size: 100 })
        all = all.concat(next.items)
      }
      setSupplyPlans(all)
      if (!selectedSupplyPlanId && all.length > 0) {
        setSelectedSupplyPlanId(all[0].id)
      }
    } catch {
      // handled globally
    }
  }

  const loadSchedules = async () => {
    setLoading(true)
    try {
      const data = await productionSchedulingService.listSchedules(
        selectedSupplyPlanId ? { supply_plan_id: selectedSupplyPlanId } : undefined,
      )
      setRows(data)
    } catch {
      setRows([])
    } finally {
      setLoading(false)
    }
  }

  const loadCapacity = async () => {
    if (!selectedSupplyPlanId) {
      setCapacitySummary(null)
      return
    }
    try {
      const data = await productionSchedulingService.getCapacitySummary(selectedSupplyPlanId)
      setCapacitySummary(data)
    } catch {
      setCapacitySummary(null)
    }
  }

  useEffect(() => { loadSupplyPlans() }, [])
  useEffect(() => {
    loadSchedules()
    loadCapacity()
  }, [selectedSupplyPlanId])

  const toggleShift = (shift: string) => {
    setSelectedShifts((prev) =>
      prev.includes(shift) ? prev.filter((s) => s !== shift) : [...prev, shift],
    )
  }

  const parseCsv = (v: string) => v.split(',').map((x) => x.trim()).filter(Boolean)

  const generate = async () => {
    if (!selectedSupplyPlanId) {
      toast.error('Please select a supply plan first')
      return
    }
    const wcList = parseCsv(workcenters)
    const lineList = parseCsv(lines)
    if (wcList.length === 0 || lineList.length === 0 || selectedShifts.length === 0) {
      toast.error('Workcenters, lines, and at least one shift are required')
      return
    }

    setGenerating(true)
    try {
      await productionSchedulingService.generateSchedule({
        supply_plan_id: selectedSupplyPlanId,
        workcenters: wcList,
        lines: lineList,
        shifts: selectedShifts,
        duration_hours_per_slot: durationHours,
      })
      toast.success('Production schedule generated')
      loadSchedules()
      loadCapacity()
    } catch {
      // handled
    } finally {
      setGenerating(false)
    }
  }

  const updateStatus = async (id: number, status: ProductionScheduleStatus) => {
    setStatusUpdatingId(id)
    try {
      await productionSchedulingService.updateScheduleStatus(id, status)
      toast.success('Schedule status updated')
      loadSchedules()
    } catch {
      // handled
    } finally {
      setStatusUpdatingId(null)
    }
  }

  const resequence = async (id: number, direction: 'up' | 'down') => {
    try {
      const reordered = await productionSchedulingService.resequenceSchedule(id, direction)
      setRows(reordered)
      toast.success('Sequence updated')
    } catch {
      // handled globally
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Production Scheduling</h1>
        <p className="text-sm text-gray-500 mt-0.5">Line / shift / workcenter sequencing for supply plan execution</p>
      </div>

      <Card title="Generate Schedule" subtitle="Create finite slots from selected supply plan">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Supply Plan</label>
            <select
              value={selectedSupplyPlanId ?? ''}
              onChange={(e) => setSelectedSupplyPlanId(e.target.value ? Number(e.target.value) : undefined)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            >
              {supplyPlans.map((p) => (
                <option key={p.id} value={p.id}>
                  #{p.id} — Product {p.product_id} — {p.period.slice(0, 7)} — {formatNumber(p.planned_prod_qty ?? 0)}
                </option>
              ))}
            </select>
            {selectedPlan && (
              <p className="mt-1 text-xs text-gray-500">
                Selected: {formatPeriod(selectedPlan.period)} • Planned Qty {formatNumber(selectedPlan.planned_prod_qty ?? 0)}
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Workcenters (comma-separated)</label>
            <input
              value={workcenters}
              onChange={(e) => setWorkcenters(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
              placeholder="WC-1, WC-2"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Lines (comma-separated)</label>
            <input
              value={lines}
              onChange={(e) => setLines(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
              placeholder="Line-1, Line-2"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Duration Hours per Slot</label>
            <input
              type="number"
              min={1}
              max={24}
              value={durationHours}
              onChange={(e) => setDurationHours(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>
        </div>

        <div className="mt-4">
          <label className="block text-xs font-medium text-gray-700 mb-1.5">Shifts</label>
          <div className="flex flex-wrap gap-2">
            {SHIFT_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => toggleShift(s)}
                className={`px-3 py-1.5 rounded-full text-xs border ${selectedShifts.includes(s)
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4 flex gap-2">
          <Button onClick={generate} loading={generating}>Generate Schedule</Button>
          <Button variant="outline" onClick={loadSchedules} icon={<RefreshCw className="h-4 w-4" />}>Refresh</Button>
        </div>
      </Card>

      <Card title="Capacity Diagnostics" subtitle="Quick load validation against supply plan max capacity">
        {!capacitySummary ? (
          <p className="text-sm text-gray-500">Select a supply plan to view capacity diagnostics.</p>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
              <div className="rounded-lg border border-gray-200 px-3 py-2">
                <p className="text-[11px] text-gray-500">Slots</p>
                <p className="text-sm font-semibold text-gray-900">{capacitySummary.slot_count}</p>
              </div>
              <div className="rounded-lg border border-gray-200 px-3 py-2">
                <p className="text-[11px] text-gray-500">Planned Total Qty</p>
                <p className="text-sm font-semibold text-gray-900">{formatNumber(capacitySummary.planned_total_qty)}</p>
              </div>
              <div className="rounded-lg border border-gray-200 px-3 py-2">
                <p className="text-[11px] text-gray-500">Capacity Max Qty</p>
                <p className="text-sm font-semibold text-gray-900">{formatNumber(capacitySummary.capacity_max_qty)}</p>
              </div>
              <div className="rounded-lg border border-gray-200 px-3 py-2">
                <p className="text-[11px] text-gray-500">Utilization</p>
                <p className={`text-sm font-semibold ${capacitySummary.overloaded ? 'text-red-600' : 'text-emerald-600'}`}>
                  {formatPercent(capacitySummary.utilization_pct)}
                </p>
              </div>
              <div className="rounded-lg border border-gray-200 px-3 py-2">
                <p className="text-[11px] text-gray-500">Status</p>
                <p className={`text-sm font-semibold ${capacitySummary.overloaded ? 'text-red-600' : 'text-emerald-600'}`}>
                  {capacitySummary.overloaded ? 'Overloaded' : 'Within Capacity'}
                </p>
              </div>
            </div>

            <div className="overflow-x-auto border border-gray-100 rounded-lg">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50">
                    {['Workcenter', 'Line', 'Shift', 'Slots', 'Total Planned Qty'].map((h) => (
                      <th key={h} className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {capacitySummary.groups.map((g) => (
                    <tr key={`${g.workcenter}-${g.line}-${g.shift}`}>
                      <td className="px-4 py-2">{g.workcenter}</td>
                      <td className="px-4 py-2">{g.line}</td>
                      <td className="px-4 py-2">{g.shift}</td>
                      <td className="px-4 py-2 tabular-nums">{g.slot_count}</td>
                      <td className="px-4 py-2 tabular-nums">{formatNumber(g.total_planned_qty)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Card>

      <Card title="Scheduled Slots" subtitle="Sequenced by order, workcenter, line, and shift">
        {loading ? (
          <SkeletonTable rows={8} cols={8} />
        ) : rows.length === 0 ? (
          <p className="text-sm text-gray-500">No schedule rows available. Generate a schedule first.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {['Seq', 'Workcenter', 'Line', 'Shift', 'Planned Qty', 'Start', 'End', 'Status', 'Set Status', 'Reorder'].map((h) => (
                    <th key={h} className="text-left px-4 py-2.5 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-2.5 tabular-nums">{r.sequence_order}</td>
                    <td className="px-4 py-2.5">{r.workcenter}</td>
                    <td className="px-4 py-2.5">{r.line}</td>
                    <td className="px-4 py-2.5">{r.shift}</td>
                    <td className="px-4 py-2.5 tabular-nums">{formatNumber(r.planned_qty)}</td>
                    <td className="px-4 py-2.5 text-gray-700">{new Date(r.planned_start_at).toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-gray-700">{new Date(r.planned_end_at).toLocaleString()}</td>
                    <td className="px-4 py-2.5"><StatusBadge status={r.status} size="sm" /></td>
                    <td className="px-4 py-2.5">
                      <select
                        value={r.status}
                        disabled={statusUpdatingId === r.id}
                        onChange={(e) => updateStatus(r.id, e.target.value as ProductionScheduleStatus)}
                        className="px-2 py-1.5 text-xs border border-gray-300 rounded-md"
                      >
                        {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex gap-1">
                        <Button size="sm" variant="outline" onClick={() => resequence(r.id, 'up')}>↑</Button>
                        <Button size="sm" variant="outline" onClick={() => resequence(r.id, 'down')}>↓</Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
