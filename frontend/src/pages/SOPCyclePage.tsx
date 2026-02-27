import { useEffect, useState } from 'react'
import { Plus, ChevronRight, CheckCircle, Clock, Circle } from 'lucide-react'
import { sopService } from '@/services/sopService'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Modal } from '@/components/common/Modal'
import { SkeletonCard } from '@/components/common/LoadingSpinner'
import { formatPeriod, formatDate } from '@/utils/formatters'
import type { SOPCycle, CreateSOPCycleRequest, SOPStepStatus } from '@/types'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { can } from '@/auth/permissions'

const STEP_NAMES = [
  'Data Gathering',
  'Demand Review',
  'Supply Review',
  'Pre-S&OP Meeting',
  'Executive S&OP',
]

function StepIndicator({ step, status, current }: { step: number; status: SOPStepStatus; current: number }) {
  const isActive = step === current
  const isDone = status === 'completed'

  return (
    <div className={`flex items-center gap-2 ${isActive ? 'text-blue-600' : isDone ? 'text-emerald-600' : 'text-gray-400'}`}>
      {isDone ? (
        <CheckCircle className="h-5 w-5 flex-shrink-0" />
      ) : isActive ? (
        <Clock className="h-5 w-5 flex-shrink-0 animate-pulse" />
      ) : (
        <Circle className="h-5 w-5 flex-shrink-0" />
      )}
      <span className={`text-xs font-medium ${isActive ? 'text-blue-700' : isDone ? 'text-emerald-700' : 'text-gray-500'}`}>
        {STEP_NAMES[step - 1]}
      </span>
    </div>
  )
}

export function SOPCyclePage() {
  const { user } = useAuthStore()
  const canManage = can(user?.role, 'sop.manage')

  const [cycles, setCycles] = useState<SOPCycle[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [advancingId, setAdvancingId] = useState<number | null>(null)
  const [form, setForm] = useState<Partial<CreateSOPCycleRequest>>({})

  const load = async () => {
    setLoading(true)
    try {
      const res = await sopService.getCycles({ page_size: 20 })
      setCycles(res.items)
      setTotal(res.total)
    } catch {
      // handled
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleAdvance = async (id: number) => {
    setAdvancingId(id)
    try {
      await sopService.advanceCycle(id)
      toast.success('Cycle advanced to next step')
      load()
    } catch {
      // handled
    } finally {
      setAdvancingId(null)
    }
  }

  const handleCreate = async () => {
    if (!form.cycle_name || !form.period) {
      toast.error('Please fill in cycle name and period')
      return
    }
    try {
      await sopService.createCycle(form as CreateSOPCycleRequest)
      toast.success('S&OP cycle created')
      setShowCreate(false)
      setForm({})
      load()
    } catch {
      // handled
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">S&OP Cycles</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} cycles total</p>
        </div>
        {canManage && (
          <Button icon={<Plus />} onClick={() => setShowCreate(true)}>
            New Cycle
          </Button>
        )}
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => <SkeletonCard key={i} rows={5} />)}
        </div>
      ) : cycles.length === 0 ? (
        <Card>
          <div className="text-center py-16 text-gray-400">
            <p className="text-sm">No S&OP cycles yet. Create your first cycle.</p>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {cycles.map((cycle) => (
            <Card key={cycle.id}
              title={cycle.cycle_name}
              subtitle={`Period: ${formatPeriod(cycle.period)} · Created ${formatDate(cycle.created_at)}`}
              actions={
                <div className="flex items-center gap-2">
                  <StatusBadge status={cycle.overall_status} size="sm" />
                  {cycle.overall_status === 'active' && (
                    <Button size="sm" variant="secondary" icon={<ChevronRight />}
                      disabled={!canManage}
                      loading={advancingId === cycle.id}
                      onClick={() => handleAdvance(cycle.id)}>
                      Advance
                    </Button>
                  )}
                </div>
              }
            >
              {/* Step progress */}
              <div className="mt-2">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs text-gray-500">Step {cycle.current_step} of 5</p>
                  <div className="h-1.5 flex-1 mx-4 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ width: `${((cycle.current_step - 1) / 5) * 100}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500">{Math.round(((cycle.current_step - 1) / 5) * 100)}%</p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {([1, 2, 3, 4, 5] as const).map((step) => {
                    const statusKey = `step_${step}_status` as keyof SOPCycle
                    const dueDateKey = `step_${step}_due_date` as keyof SOPCycle
                    const status = cycle[statusKey] as SOPStepStatus
                    const dueDate = cycle[dueDateKey] as string | undefined
                    return (
                      <div key={step} className={`p-3 rounded-lg border ${
                        step === cycle.current_step ? 'border-blue-200 bg-blue-50' :
                        status === 'completed' ? 'border-emerald-200 bg-emerald-50' :
                        'border-gray-100 bg-gray-50'
                      }`}>
                        <StepIndicator step={step} status={status} current={cycle.current_step} />
                        {dueDate && (
                          <p className="text-xs text-gray-400 mt-1 ml-7">Due {formatDate(dueDate, 'MMM d')}</p>
                        )}
                      </div>
                    )
                  })}
                </div>

                {cycle.notes && (
                  <p className="text-xs text-gray-500 mt-3 italic">{cycle.notes}</p>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create S&OP Cycle"
        footer={
          <>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!canManage}>Create Cycle</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Cycle Name *</label>
            <input value={form.cycle_name ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, cycle_name: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., March 2026 S&OP" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Period *</label>
            <input type="month" value={form.period?.slice(0, 7) ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, period: e.target.value + '-01' }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[1, 2, 3, 4, 5].map((step) => (
              <div key={step}>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">
                  Step {step} Due Date
                </label>
                <input type="date"
                  onChange={(e) => setForm((f) => ({ ...f, [`step_${step}_due_date`]: e.target.value }))}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            ))}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Notes</label>
            <textarea value={form.notes ?? ''}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              rows={2}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
          </div>
        </div>
      </Modal>
    </div>
  )
}
