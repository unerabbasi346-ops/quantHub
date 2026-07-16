// Perf pass: the loading state for a dynamically-imported page shell
// (next/dynamic's `loading`) — a full-page placeholder, built from the
// existing Skeleton primitive rather than a new one.
import { Skeleton } from './Skeleton'

export function PageSkeleton() {
  return (
    <div className="space-y-6 p-6" role="status" aria-label="Loading page">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>
      <Skeleton className="h-80 w-full" />
    </div>
  )
}
