import { clsx } from 'clsx'
import { Loader2 } from 'lucide-react'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  message?: string
  fullPage?: boolean
  className?: string
}

const sizes = { sm: 'h-4 w-4', md: 'h-6 w-6', lg: 'h-10 w-10' }

export function LoadingSpinner({ size = 'md', message, fullPage, className }: LoadingSpinnerProps) {
  const content = (
    <div className={clsx('flex flex-col items-center justify-center gap-3', className)}>
      <Loader2 className={clsx('animate-spin text-blue-600', sizes[size])} />
      {message && <p className="text-sm text-gray-500">{message}</p>}
    </div>
  )

  if (fullPage) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-white/80 z-50">
        {content}
      </div>
    )
  }

  return content
}

export function SkeletonCard({ rows = 3 }: { rows?: number }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-5 space-y-3 animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-1/3" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-3 bg-gray-100 rounded" style={{ width: `${70 + (i % 3) * 10}%` }} />
      ))}
    </div>
  )
}

export function SkeletonTable({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="animate-pulse">
      <div className="h-10 bg-gray-100 rounded mb-2" />
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 py-3 border-b border-gray-50">
          {Array.from({ length: cols }).map((_, c) => (
            <div key={c} className="h-4 bg-gray-100 rounded flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}
