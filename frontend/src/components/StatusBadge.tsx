import { Circle } from 'lucide-react'
import { cn } from '@/lib/utils'

export type Status = 'online' | 'degraded' | 'offline'

const STATUS_STYLES: Record<Status, string> = {
  online: 'bg-status-online/15 text-status-online',
  degraded: 'bg-status-degraded/15 text-status-degraded',
  offline: 'bg-status-offline/15 text-status-offline',
}

const DOT_STYLES: Record<Status, string> = {
  online: 'fill-status-online text-status-online',
  degraded: 'fill-status-degraded text-status-degraded',
  offline: 'fill-status-offline text-status-offline',
}

interface StatusBadgeProps {
  status: Status
  label: string
  className?: string
}

/** Consistent green=online / amber=degraded / red=offline convention, used across health cards, tickets, and dashboards. */
export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-sm font-medium',
        STATUS_STYLES[status],
        className,
      )}
    >
      <Circle className={cn('size-2', DOT_STYLES[status])} />
      {label}
    </span>
  )
}
