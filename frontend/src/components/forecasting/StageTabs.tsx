type StageStatus = 'complete' | 'active' | 'locked' | 'ready'

type Stage<K extends string = string> = {
  key: K
  label: string
}

type StageTabsProps<K extends string = string> = {
  stages: readonly Stage<K>[]
  activeStage: K
  stageEnabled: Record<K, boolean>
  getStatus: (stage: K) => StageStatus
  onSelect: (stage: K) => void
}

export function StageTabs<K extends string>({ stages, activeStage, stageEnabled, getStatus, onSelect }: StageTabsProps<K>) {
  return (
    <div className="border-b border-gray-200">
      <nav className="-mb-px flex flex-wrap gap-2">
        {stages.map((stage) => {
          const status = getStatus(stage.key)
          const active = activeStage === stage.key
          const disabled = !stageEnabled[stage.key]
          return (
            <button
              key={stage.key}
              onClick={() => !disabled && onSelect(stage.key)}
              disabled={disabled}
              className={`px-3 py-2 text-sm rounded-t-lg border-b-2 transition-colors ${
                active
                  ? 'border-blue-600 text-blue-700 bg-blue-50'
                  : disabled
                    ? 'border-transparent text-gray-300 cursor-not-allowed'
                    : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
              }`}
            >
              <span>{stage.label}</span>
              <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full ${
                status === 'complete'
                  ? 'bg-emerald-100 text-emerald-700'
                  : status === 'active'
                    ? 'bg-blue-100 text-blue-700'
                    : status === 'locked'
                      ? 'bg-gray-100 text-gray-400'
                      : 'bg-amber-100 text-amber-700'
              }`}>
                {status}
              </span>
            </button>
          )
        })}
      </nav>
    </div>
  )
}
