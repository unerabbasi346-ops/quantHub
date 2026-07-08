// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
//   §Components: "Standardize ... tables ..."
//   §Data Visualization: "efficient rendering for large datasets" —
//   virtualization deferred per S-6 until profiling justifies it (Doc 08
//   §Performance); these are the plain canonical primitives for now.
// Per Doc 00 §14.11
import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from 'react'
import { cn } from '@/lib/utils/cn'

// Doc 08 §Architecture: stateless presentation components.
export function Table({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={cn('w-full border-collapse text-sm', className)} {...props} />
    </div>
  )
}

export function TableHeader({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={className} {...props} />
}

export function TableBody({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn('divide-y divide-border/70', className)} {...props} />
}

export function TableRow({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn('transition-colors duration-150 hover:bg-surface-hover/60', className)}
      {...props}
    />
  )
}

export function TableHead({ className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        'border-b border-border px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-fg-subtle',
        className,
      )}
      {...props}
    />
  )
}

// `numeric` right-aligns and tabular-nums a cell — the common case for
// price/quantity/P&L columns in trading tables (Doc 06 §Data Visualization
// "consistent ... formatting").
export function TableCell({
  className,
  numeric,
  ...props
}: TdHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return (
    <td
      className={cn(
        'px-4 py-2.5 text-fg',
        numeric && 'text-right tabular-nums font-mono',
        className,
      )}
      {...props}
    />
  )
}
