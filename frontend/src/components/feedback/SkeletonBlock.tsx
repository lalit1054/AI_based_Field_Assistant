import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface SkeletonBlockProps {
  lines?: number
  className?: string
}

export function SkeletonBlock({ lines = 3, className }: SkeletonBlockProps) {
  return (
    <div className={cn('flex flex-col gap-2', className)} aria-hidden="true">
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} className={cn('h-4 w-full', i === lines - 1 && 'w-2/3')} />
      ))}
    </div>
  )
}
