import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, GitCompare, RefreshCw, Repeat } from 'lucide-react'
import toast from 'react-hot-toast'

import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { productionSchedulingService } from '@/services/productionSchedulingService'
import { supplyService } from '@/services/supplyService'
import type {
  AgenticRecommendationStatus,
  AgenticScheduleRecommendationView,
  CanonicalProductionEventResponse,
  ProductionEventSource,
  ProductionScheduleVersionCompareResponse,
  ProductionScheduleVersionView,
  SupplyPlan,
} from '@/types'

const EVENT_SOURCES: ProductionEventSource[] = ['MES', 'ERP', 'IIOT', 'QMS', 'CMMS', 'MANUAL']

function statusPill(status: string): string {
  const s = status.toLowerCase()
  if (s.includes('approved') || s.includes('published') || s.includes('processed') || s.includes('replayed')) {
    return 'bg-emerald-100 text-emerald-700'
  }
  if (s.includes('rejected') || s.includes('failed') || s.includes('critical')) {
    return 'bg-red-100 text-red-700'
  }
  return 'bg-amber-100 text-amber-700'
}

export function ProductionControlTowerPage() {
  const [supplyPlans, setSupplyPlans] = useState<SupplyPlan[]>([])
  const [selectedSupplyPlanId, setSelectedSupplyPlanId] = useState<number | undefined>(undefined)
  const [recommendationStatus, setRecommendationStatus] = useState<AgenticRecommendationStatus | ''>('')

  const [eventSource, setEventSource] = useState<ProductionEventSource>('MES')
  const [externalEventType, setExternalEventType] = useState('MACHINE_DOWN')
  const [externalEventId, setExternalEventId] = useState(`evt-${Date.now()}`)
  const [idempotencyKey, setIdempotencyKey] = useState(`idem-${Date.now()}`)
  const [eventPayloadText, setEventPayloadText] = useState('{"workcenter":"WC-1","line":"Line-1"}')

  const [events, setEvents] = useState<CanonicalProductionEventResponse[]>([])
  const [recommendations, setRecommendations] = useState<AgenticScheduleRecommendationView[]>([])
  const [versions, setVersions] = useState<ProductionScheduleVersionView[]>([])
  const [compareResult, setCompareResult] = useState<ProductionScheduleVersionCompareResponse | null>(null)
  const [baseVersion, setBaseVersion] = useState<number | undefined>(undefined)
  const [targetVersion, setTargetVersion] = useState<number | undefined>(undefined)

  const [busyEventId, setBusyEventId] = useState<string | null>(null)
  const [busyRecommendationId, setBusyRecommendationId] = useState<string | null>(null)
  const [ingesting, setIngesting] = useState(false)
  const [comparing, setComparing] = useState(false)

  const selectedPlan = useMemo(
    () => supplyPlans.find((p) => p.id === selectedSupplyPlanId),
    [supplyPlans, selectedSupplyPlanId],
  )

  const loadSupplyPlans = async () => {
    const first = await supplyService.getPlans({ page: 1, page_size: 100 })
    let all = [...first.items]
    for (let page = 2; page <= first.total_pages; page += 1) {
      const next = await supplyService.getPlans({ page, page_size: 100 })
      all = all.concat(next.items)
    }
    setSupplyPlans(all)
    if (!selectedSupplyPlanId && all.length > 0) setSelectedSupplyPlanId(all[0].id)
  }

  const loadEvents = async () => setEvents(await productionSchedulingService.listCanonicalEvents(30))

  const loadRecommendations = async () => {
    const data = await productionSchedulingService.listRecommendations({
      supply_plan_id: selectedSupplyPlanId,
      status: recommendationStatus || undefined,
    })
    setRecommendations(data)
  }

  const loadVersions = async () => {
    if (!selectedSupplyPlanId) return setVersions([])
    const data = await productionSchedulingService.listScheduleVersions(selectedSupplyPlanId)
    setVersions(data)
    if (data.length > 0) {
      setBaseVersion(data[data.length - 1].version_number)
      setTargetVersion(data[0].version_number)
    }
  }

  useEffect(() => {
    loadSupplyPlans().catch(() => toast.error('Failed to load supply plans'))
    loadEvents().catch(() => toast.error('Failed to load event feed'))
  }, [])

  useEffect(() => {
    if (!selectedSupplyPlanId) return
    loadRecommendations().catch(() => toast.error('Failed to load recommendations'))
    loadVersions().catch(() => toast.error('Failed to load versions'))
  }, [selectedSupplyPlanId, recommendationStatus])

  const ingestEvent = async () => {
    setIngesting(true)
    try {
      const payload = JSON.parse(eventPayloadText)
      const res = await productionSchedulingService.ingestCanonicalEvent({
        event_id: externalEventId,
        event_type: externalEventType,
        event_source: eventSource,
        event_timestamp: new Date().toISOString(),
        payload,
        idempotency_key: idempotencyKey,
      })
      toast.success(res.duplicate ? 'Duplicate event detected' : 'Event ingested')
      setExternalEventId(`evt-${Date.now()}`)
      setIdempotencyKey(`idem-${Date.now()}`)
      await loadEvents()
    } catch {
      toast.error('Unable to ingest event. Check JSON payload.')
    } finally {
      setIngesting(false)
    }
  }

  const replayEvent = async (eventId: string) => {
    setBusyEventId(eventId)
    try {
      await productionSchedulingService.replayCanonicalEvent(eventId)
      toast.success(`Replay submitted for ${eventId}`)
      await loadEvents()
    } finally {
      setBusyEventId(null)
    }
  }

  const decide = async (id: string, decision: 'approve' | 'reject') => {
    setBusyRecommendationId(id)
    try {
      if (decision === 'approve') await productionSchedulingService.approveRecommendation(id, 'Approved in control tower')
      else await productionSchedulingService.rejectRecommendation(id, 'Rejected in control tower')
      await loadRecommendations()
    } finally {
      setBusyRecommendationId(null)
    }
  }

  const publish = async (id: string) => {
    setBusyRecommendationId(id)
    try {
      await productionSchedulingService.publishRecommendation(id, { apply_actions: true, note: 'Published from control tower' })
      toast.success('Published schedule version')
      await Promise.all([loadRecommendations(), loadVersions()])
    } finally {
      setBusyRecommendationId(null)
    }
  }

  const compareVersions = async () => {
    if (!selectedSupplyPlanId || !baseVersion || !targetVersion) return
    setComparing(true)
    try {
      const res = await productionSchedulingService.compareScheduleVersions(selectedSupplyPlanId, baseVersion, targetVersion)
      setCompareResult(res)
    } finally {
      setComparing(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Production Control Tower</h1>
        <p className="text-sm text-gray-500">Exception dashboard, simulation workspace, and recommendation audit controls.</p>
      </div>

      <Card title="Control Tower Filters" subtitle="Scope recommendations and simulations to a planning context">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          <select className="px-3 py-2 text-sm border border-gray-300 rounded-lg" value={selectedSupplyPlanId ?? ''} onChange={(e) => setSelectedSupplyPlanId(Number(e.target.value))}>
            {supplyPlans.map((p) => (
              <option key={p.id} value={p.id}>#{p.id} • Product {p.product_id} • {p.period.slice(0, 7)}</option>
            ))}
          </select>
          <select className="px-3 py-2 text-sm border border-gray-300 rounded-lg" value={recommendationStatus} onChange={(e) => setRecommendationStatus(e.target.value as AgenticRecommendationStatus | '')}>
            <option value="">All recommendation states</option>
            <option value="pending_approval">Pending Approval</option>
            <option value="approved">Approved</option>
            <option value="published">Published</option>
            <option value="rejected">Rejected</option>
          </select>
          <Button variant="outline" icon={<RefreshCw className="h-4 w-4" />} onClick={() => {
            loadEvents().catch(() => undefined)
            loadRecommendations().catch(() => undefined)
            loadVersions().catch(() => undefined)
          }}>
            Refresh Control Tower
          </Button>
        </div>
        {selectedPlan && <p className="mt-2 text-xs text-gray-500">Selected plan #{selectedPlan.id} • Planned Qty {selectedPlan.planned_prod_qty ?? 0}</p>}
      </Card>

      <Card title="Exception Dashboard" subtitle="Canonical ingest, idempotency checks, and replay actions">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
          <select className="px-3 py-2 text-sm border border-gray-300 rounded-lg" value={eventSource} onChange={(e) => setEventSource(e.target.value as ProductionEventSource)}>
            {EVENT_SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <input className="px-3 py-2 text-sm border border-gray-300 rounded-lg" value={externalEventType} onChange={(e) => setExternalEventType(e.target.value)} placeholder="event_type" />
          <input className="px-3 py-2 text-sm border border-gray-300 rounded-lg" value={externalEventId} onChange={(e) => setExternalEventId(e.target.value)} placeholder="event_id" title="Unique ID from source system" />
          <input className="px-3 py-2 text-sm border border-gray-300 rounded-lg" value={idempotencyKey} onChange={(e) => setIdempotencyKey(e.target.value)} placeholder="idempotency_key" title="Used to detect duplicate submits" />
          <Button onClick={ingestEvent} loading={ingesting}>Ingest Event</Button>
        </div>
        <textarea className="mt-3 w-full h-20 px-3 py-2 text-xs font-mono border border-gray-300 rounded-lg" value={eventPayloadText} onChange={(e) => setEventPayloadText(e.target.value)} />

        {events.length === 0 ? (
          <div className="mt-4 rounded-lg border border-dashed border-gray-300 p-6 text-center text-sm text-gray-500">
            <AlertTriangle className="h-5 w-5 mx-auto mb-1 text-amber-500" />
            No events in feed yet.
          </div>
        ) : (
          <>
          <div className="mt-4 overflow-x-auto border border-gray-100 rounded-lg hidden md:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {['Event', 'Source', 'Type', 'Status', 'Duplicate', 'Replay', 'Action'].map((h) => (
                    <th key={h} className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {events.map((e) => (
                  <tr key={e.event_id}>
                    <td className="px-4 py-2.5 font-mono text-xs">{e.event_id}</td>
                    <td className="px-4 py-2.5">{e.event_source}</td>
                    <td className="px-4 py-2.5">{e.event_type}</td>
                    <td className="px-4 py-2.5"><span className={`inline-flex rounded-full px-2 py-0.5 text-xs ${statusPill(e.processing_status)}`}>{e.processing_status}</span></td>
                    <td className="px-4 py-2.5 text-xs">{e.duplicate ? `yes (${e.duplicate_of_event_id})` : 'no'}</td>
                    <td className="px-4 py-2.5 tabular-nums">{e.replay_count}</td>
                    <td className="px-4 py-2.5">
                      <Button size="sm" variant="outline" icon={<Repeat className="h-3.5 w-3.5" />} loading={busyEventId === e.event_id} onClick={() => replayEvent(e.event_id)}>
                        Replay
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 md:hidden">
            {events.map((e) => (
              <div key={e.event_id} className="rounded-lg border border-gray-200 p-3 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-mono text-gray-700 break-all">{e.event_id}</p>
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs ${statusPill(e.processing_status)}`}>{e.processing_status}</span>
                </div>
                <p className="text-xs text-gray-600">{e.event_source} • {e.event_type}</p>
                <p className="text-xs text-gray-600">Duplicate: {e.duplicate ? `yes (${e.duplicate_of_event_id})` : 'no'}</p>
                <div className="flex items-center justify-between">
                  <p className="text-xs text-gray-600">Replay count: {e.replay_count}</p>
                  <Button size="sm" variant="outline" loading={busyEventId === e.event_id} onClick={() => replayEvent(e.event_id)}>
                    Replay
                  </Button>
                </div>
              </div>
            ))}
          </div>
          </>
        )}
      </Card>

      <Card title="Recommendation Audit Viewer" subtitle="Planner actions with human-in-the-loop controls">
        {recommendations.length === 0 ? (
          <p className="text-sm text-gray-500">No recommendations found for the selected filters.</p>
        ) : (
          <>
          <div className="overflow-x-auto border border-gray-100 rounded-lg hidden md:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  {['Created', 'Event', 'Status', 'Revision', 'Summary', 'Actions'].map((h) => (
                    <th key={h} className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {recommendations.map((r) => (
                  <tr key={r.recommendation_id}>
                    <td className="px-4 py-2.5 text-xs">{new Date(r.created_at).toLocaleString()}</td>
                    <td className="px-4 py-2.5">{r.event_type}</td>
                    <td className="px-4 py-2.5"><span className={`inline-flex rounded-full px-2 py-0.5 text-xs ${statusPill(r.status)}`}>{r.status}</span></td>
                    <td className="px-4 py-2.5">{r.revision_number ?? 1}</td>
                    <td className="px-4 py-2.5 max-w-[380px] truncate" title={r.recommendation_summary}>{r.recommendation_summary}</td>
                    <td className="px-4 py-2.5">
                      {r.status === 'pending_approval' ? (
                        <div className="flex gap-1">
                          <Button size="sm" loading={busyRecommendationId === r.recommendation_id} onClick={() => decide(r.recommendation_id, 'approve')}>Approve</Button>
                          <Button size="sm" variant="outline" loading={busyRecommendationId === r.recommendation_id} onClick={() => decide(r.recommendation_id, 'reject')}>Reject</Button>
                        </div>
                      ) : r.status === 'approved' ? (
                        <Button size="sm" loading={busyRecommendationId === r.recommendation_id} onClick={() => publish(r.recommendation_id)}>Publish</Button>
                      ) : (
                        <span className="text-xs text-gray-500">{r.decision_note ?? 'Finalized'}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-1 gap-3 md:hidden">
            {recommendations.map((r) => (
              <div key={r.recommendation_id} className="rounded-lg border border-gray-200 p-3 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs text-gray-500">{new Date(r.created_at).toLocaleString()}</p>
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs ${statusPill(r.status)}`}>{r.status}</span>
                </div>
                <p className="text-sm font-medium text-gray-900">{r.event_type}</p>
                <p className="text-xs text-gray-600 line-clamp-2">{r.recommendation_summary}</p>
                <p className="text-xs text-gray-500">Revision: {r.revision_number ?? 1}</p>
                <div>
                  {r.status === 'pending_approval' ? (
                    <div className="flex gap-2">
                      <Button size="sm" className="flex-1" loading={busyRecommendationId === r.recommendation_id} onClick={() => decide(r.recommendation_id, 'approve')}>Approve</Button>
                      <Button size="sm" className="flex-1" variant="outline" loading={busyRecommendationId === r.recommendation_id} onClick={() => decide(r.recommendation_id, 'reject')}>Reject</Button>
                    </div>
                  ) : r.status === 'approved' ? (
                    <Button size="sm" className="w-full" loading={busyRecommendationId === r.recommendation_id} onClick={() => publish(r.recommendation_id)}>Publish</Button>
                  ) : (
                    <p className="text-xs text-gray-500">{r.decision_note ?? 'Finalized'}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
          </>
        )}
      </Card>

      <Card title="Simulation Workspace" subtitle="Version compare for published schedule snapshots">
        {versions.length === 0 ? (
          <p className="text-sm text-gray-500">No versions available yet. Publish an approved recommendation first.</p>
        ) : (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
              <select className="px-3 py-2 text-sm border border-gray-300 rounded-lg" value={baseVersion ?? ''} onChange={(e) => setBaseVersion(Number(e.target.value))}>
                {versions.map((v) => <option key={`base-${v.version_number}`} value={v.version_number}>Base v{v.version_number}</option>)}
              </select>
              <select className="px-3 py-2 text-sm border border-gray-300 rounded-lg" value={targetVersion ?? ''} onChange={(e) => setTargetVersion(Number(e.target.value))}>
                {versions.map((v) => <option key={`target-${v.version_number}`} value={v.version_number}>Target v{v.version_number}</option>)}
              </select>
              <Button icon={<GitCompare className="h-4 w-4" />} loading={comparing} onClick={compareVersions}>Compare Versions</Button>
            </div>

            {compareResult && (
              <div className="mt-3 rounded-lg border border-indigo-100 bg-indigo-50 px-3 py-2 text-sm text-indigo-800">
                Delta v{compareResult.base_version} → v{compareResult.target_version}: {compareResult.changed_rows} row(s) changed.
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  )
}
