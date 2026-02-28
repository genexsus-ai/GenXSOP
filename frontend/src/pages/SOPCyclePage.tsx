import { useEffect, useState } from 'react'
import { Plus, ChevronRight, CheckCircle, Clock, Circle, Edit3, Save } from 'lucide-react'
import { sopService } from '@/services/sopService'
import { authService } from '@/services/authService'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { StatusBadge } from '@/components/common/StatusBadge'
import { Modal } from '@/components/common/Modal'
import { SkeletonCard } from '@/components/common/LoadingSpinner'
import { formatPeriod, formatDate } from '@/utils/formatters'
import type { SOPCycle, CreateSOPCycleRequest, SOPStepStatus, UpdateSOPCycleRequest, User } from '@/types'
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
  const canCompleteCycle = user?.role === 'admin' || user?.role === 'executive'

  const [cycles, setCycles] = useState<SOPCycle[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [editingCycle, setEditingCycle] = useState<SOPCycle | null>(null)
  const [advancingId, setAdvancingId] = useState<number | null>(null)
  const [savingId, setSavingId] = useState<number | null>(null)
  const [completingId, setCompletingId] = useState<number | null>(null)
  const [form, setForm] = useState<Partial<CreateSOPCycleRequest>>({})
  const [editForm, setEditForm] = useState<UpdateSOPCycleRequest>({})

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

  useEffect(() => {
    const loadUsers = async () => {
      if (!canManage && !canCompleteCycle) return
      try {
        const allUsers = await authService.listUsers()
        setUsers(allUsers)
      } catch {
        setUsers([])
      }
    }
    loadUsers()
  }, [canManage, canCompleteCycle])

  const ownerName = (ownerId?: number) => {
    if (!ownerId) return 'Unassigned'
    const match = users.find((u) => Number(u.id) === Number(ownerId))
    return match?.full_name ?? `User #${ownerId}`
  }

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

  const openEdit = (cycle: SOPCycle) => {
    setEditingCycle(cycle)
    setEditForm({
      cycle_name: cycle.cycle_name,
      period: cycle.period,
      step_1_due_date: cycle.step_1_due_date,
      step_1_owner_id: cycle.step_1_owner_id,
      step_2_due_date: cycle.step_2_due_date,
      step_2_owner_id: cycle.step_2_owner_id,
      step_3_due_date: cycle.step_3_due_date,
      step_3_owner_id: cycle.step_3_owner_id,
      step_4_due_date: cycle.step_4_due_date,
      step_4_owner_id: cycle.step_4_owner_id,
      step_5_due_date: cycle.step_5_due_date,
      step_5_owner_id: cycle.step_5_owner_id,
      notes: cycle.notes,
      decisions: cycle.decisions,
      action_items: cycle.action_items,
    })
    setShowEdit(true)
  }

  const handleSaveCycleDetails = async () => {
    if (!editingCycle) return
    setSavingId(editingCycle.id)
    try {
      await sopService.updateCycle(editingCycle.id, editForm)
      toast.success('S&OP cycle details saved')
      setShowEdit(false)
      setEditingCycle(null)
      await load()
    } catch {
      // handled
    } finally {
      setSavingId(null)
    }
  }

  const handleComplete = async (cycle: SOPCycle) => {
    setCompletingId(cycle.id)
    try {
      if (canManage && (editForm.decisions || editForm.action_items || editForm.notes)) {
        await sopService.updateCycle(cycle.id, {
          decisions: editForm.decisions,
          action_items: editForm.action_items,
          notes: editForm.notes,
        })
      }
      await sopService.completeCycle(cycle.id)
      toast.success('S&OP cycle marked as completed')
      await load()
    } catch {
      // handled
    } finally {
      setCompletingId(null)
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
                  {canManage && (
                    <Button size="sm" variant="outline" icon={<Edit3 />} onClick={() => openEdit(cycle)}>
                      Edit
                    </Button>
                  )}
                  {cycle.overall_status === 'active' && cycle.current_step >= 5 && canCompleteCycle && (
                    <Button
                      size="sm"
                      icon={<CheckCircle />}
                      loading={completingId === cycle.id}
                      onClick={() => handleComplete(cycle)}
                    >
                      Complete
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
                    const ownerKey = `step_${step}_owner_id` as keyof SOPCycle
                    const status = cycle[statusKey] as SOPStepStatus
                    const dueDate = cycle[dueDateKey] as string | undefined
                    const ownerId = cycle[ownerKey] as number | undefined
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
                        <p className="text-xs text-gray-400 mt-1 ml-7">Owner: {ownerName(ownerId)}</p>
                      </div>
                    )
                  })}
                </div>

                {(cycle.decisions || cycle.action_items) && (
                  <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="rounded-lg border border-emerald-100 bg-emerald-50 p-3">
                      <p className="text-xs font-medium text-emerald-800 mb-1">Decisions</p>
                      <p className="text-xs text-emerald-900 whitespace-pre-wrap">{cycle.decisions || '—'}</p>
                    </div>
                    <div className="rounded-lg border border-amber-100 bg-amber-50 p-3">
                      <p className="text-xs font-medium text-amber-800 mb-1">Action Items</p>
                      <p className="text-xs text-amber-900 whitespace-pre-wrap">{cycle.action_items || '—'}</p>
                    </div>
                  </div>
                )}

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

      <Modal
        isOpen={showEdit}
        onClose={() => {
          setShowEdit(false)
          setEditingCycle(null)
        }}
        title="Edit S&OP Cycle"
        footer={
          <>
            <Button variant="outline" onClick={() => setShowEdit(false)}>Cancel</Button>
            <Button icon={<Save />} loading={savingId === editingCycle?.id} onClick={handleSaveCycleDetails}>
              Save
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Cycle Name</label>
            <input
              value={editForm.cycle_name ?? ''}
              onChange={(e) => setEditForm((prev) => ({ ...prev, cycle_name: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Period</label>
            <input
              type="month"
              value={editForm.period?.slice(0, 7) ?? ''}
              onChange={(e) => setEditForm((prev) => ({ ...prev, period: `${e.target.value}-01` }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[1, 2, 3, 4, 5].map((step) => {
              const dueKey = `step_${step}_due_date` as keyof UpdateSOPCycleRequest
              const ownerKey = `step_${step}_owner_id` as keyof UpdateSOPCycleRequest
              return (
                <div key={`edit-step-${step}`} className="rounded-lg border border-gray-100 p-3">
                  <p className="text-xs font-medium text-gray-700 mb-2">Step {step}</p>
                  <label className="block text-xs text-gray-500 mb-1">Due Date</label>
                  <input
                    type="date"
                    value={String(editForm[dueKey] ?? '')}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, [dueKey]: e.target.value }))}
                    className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded mb-2"
                  />
                  <label className="block text-xs text-gray-500 mb-1">Owner</label>
                  <select
                    value={Number(editForm[ownerKey] ?? 0)}
                    onChange={(e) => setEditForm((prev) => ({
                      ...prev,
                      [ownerKey]: Number(e.target.value) || undefined,
                    }))}
                    className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded"
                  >
                    <option value={0}>Unassigned</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>
                    ))}
                  </select>
                </div>
              )
            })}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Decisions</label>
            <textarea
              rows={3}
              value={editForm.decisions ?? ''}
              onChange={(e) => setEditForm((prev) => ({ ...prev, decisions: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Action Items</label>
            <textarea
              rows={3}
              value={editForm.action_items ?? ''}
              onChange={(e) => setEditForm((prev) => ({ ...prev, action_items: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1.5">Notes</label>
            <textarea
              rows={2}
              value={editForm.notes ?? ''}
              onChange={(e) => setEditForm((prev) => ({ ...prev, notes: e.target.value }))}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}
