import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"

import { Button } from "@/components/ui/button"

interface PaginationProps {
  offset: number
  limit: number
  /** Count of rows returned in the current page — used to infer whether a next page exists. */
  currentPageCount: number
  onOffsetChange: (offset: number) => void
}

/** Prev/next pager for offset+limit backed list endpoints (no total-count field in these APIs). */
function Pagination({ offset, limit, currentPageCount, onOffsetChange }: PaginationProps) {
  const page = Math.floor(offset / limit) + 1
  const hasPrev = offset > 0
  const hasNext = currentPageCount === limit

  return (
    <div className="flex items-center justify-end gap-2 pt-2">
      <span className="text-sm text-muted-foreground">Page {page}</span>
      <Button
        type="button"
        variant="outline"
        size="icon-sm"
        disabled={!hasPrev}
        onClick={() => onOffsetChange(Math.max(0, offset - limit))}
        aria-label="Previous page"
      >
        <ChevronLeftIcon className="size-4" />
      </Button>
      <Button
        type="button"
        variant="outline"
        size="icon-sm"
        disabled={!hasNext}
        onClick={() => onOffsetChange(offset + limit)}
        aria-label="Next page"
      >
        <ChevronRightIcon className="size-4" />
      </Button>
    </div>
  )
}

export { Pagination }
