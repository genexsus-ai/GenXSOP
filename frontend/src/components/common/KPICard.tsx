import { clsx } from 'clsx'
import type { ReactNode } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface KPICardProps {
  title: string
  value: string | number
  change?: number
  changeLabel?: string
  trend?: 'up' | 'down' | 'neutral'
  icon?: ReactNode
  color?: 'blue' | 'emerald' | 'amber' | 'red' | 'purple' | 'indigo'
  subtitle?: string
  loading?: boolean
  onClick?: () => void
}

const colorMap = {
  blue:    { bg: 'bg-blue-50',    icon: 'bg-blue-100 text-blue-600',    text: 'text-blue-600' },
  emerald: { bg: 'bg-emerald-50', icon: 'bg-emerald-100 text-emerald-600', text: 'text-emerald-600' },
  amber:   { bg: 'bg-amber-50',   icon: 'bg-amber-100 text-amber-600',   text: 'text-amber-600' },
  red:     { bg: 'bg-red-50',     icon: 'bg-red-100 text-red-600',       text: 'text-red-600' },
  purple:  { bg: 'bg-purple-50',  icon: 'bg-purple-100 text-purple-600', text: 'text-purple-600' },
  indigo:  { bg: 'bg-indigo-50',  icon: 'bg-indigo-100 text-indigo-600', text: 'text-indigo-600' },
}

export function KPICard({
  title,
  value,
  change,
  changeLabel,
  trend,
  icon,
  color = 'blue',
  subtitle,
  loading,
  onClick,
}: KPICardProps) {
  const colors = colorMap[color]

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-100 p-5 animate-pulse">
        <div className="flex items-center justify-between mb-3">
          <div className="h-3 bg-gray-200 rounded w-24" />
          <div className="h-9 w-9 bg-gray-100 rounded-lg" />
        </div>
        <div className="h-7 bg-gray-200 rounded w-20 mb-2" />
        <div className="h-3 bg-gray-100 rounded w-16" />
      </div>
    )
  }

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const trendColor = trend === 'up' ? 'text-emerald-600' : trend === 'down' ? 'text-red-500' : 'text-gray-400'

  return (
    <div
      className={clsx(
        'bg-white rounded-xl border border-gray-100 p-5 transition-shadow',
        onClick && 'cursor-pointer hover:shadow-md',
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{title}</p>
        {icon && (
          <div className={clsx('p-2 rounded-lg', colors.icon)}>
            <span className="h-4 w-4 block">{icon}</span>
          </div>
        )}
      </div>

      <p className="text-2xl font-bold text-gray-900 tabular-nums mb-1">{value}</p>

      {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}

      {change !== undefined && (
        <div className={clsx('flex items-center gap-1 mt-2', trendColor)}>
          <TrendIcon className="h-3.5 w-3.5" />
          <span className="text-xs font-medium">
            {change > 0 ? '+' : ''}{change.toFixed(1)}%
            {changeLabel && <span className="text-gray-400 font-normal ml-1">{changeLabel}</span>}
          </span>
        </div>
      )}
    </div>
  )
}
