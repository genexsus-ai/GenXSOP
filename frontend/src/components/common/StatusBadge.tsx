import { clsx } from 'clsx'
import { getStatusColor, formatStatus } from '@/utils/formatters'

interface StatusBadgeProps {
  status: string
  size?: 'sm' | 'md'
  className?: string
}

export function StatusBadge({ status, size = 'md', className }: StatusBadgeProps) {
  return (
    <span
      className={clsx(
        'badge',
        getStatusColor(status),
        size === 'sm' && 'text-[10px] px-2 py-0',
        className,
      )}
    >
      {formatStatus(status)}
    </span>
  )
}
