type TabKey = 'analytics' | 'policies' | 'exceptions' | 'recommendations' | 'runs'

type Tab = {
  key: TabKey
  label: string
}

const TABS: readonly Tab[] = [
  { key: 'analytics', label: 'Analytics' },
  { key: 'policies', label: 'Policies' },
  { key: 'exceptions', label: 'Exceptions' },
  { key: 'recommendations', label: 'Recommendations' },
  { key: 'runs', label: 'Runs' },
] as const

export function InventoryTabs({ active, onSelect }: { active: TabKey; onSelect: (key: TabKey) => void }) {
  return (
    <div className="border-b border-gray-200">
      <nav className="-mb-px flex flex-wrap gap-2">
        {TABS.map((t) => {
          const isActive = t.key === active
          return (
            <button
              key={t.key}
              onClick={() => onSelect(t.key)}
              className={`px-3 py-2 text-sm rounded-t-lg border-b-2 transition-colors ${
                isActive
                  ? 'border-blue-600 text-blue-700 bg-blue-50'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
              }`}
            >
              {t.label}
            </button>
          )
        })}
      </nav>
    </div>
  )
}

export type { TabKey as InventoryTabKey }
