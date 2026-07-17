// Governing specification: handbook/ui/01_UI_TECHNOLOGY_STANDARD (FROZEN)
//   §Data Tables: "TanStack Table ... Sorting. Filtering. Grouping. Column
//   pinning. Expandable rows. Virtualization. No HTML tables. No custom
//   table implementation." §Virtualization: "TanStack Virtual ... Large
//   datasets. Trade history. Signals. Orders. Backtests. Logs."
// handbook/ui/visual_engineering/02_LAYOUT_GRID_SYSTEM §Tables: "Full width.
//   Sticky header. Consistent row height. Search always visible. Filters
//   remain accessible." §Responsive Breakpoints: Desktop 1400+ / Laptop
//   1024-1399 / Tablet 768-1023 / Mobile <768.
// handbook/ui/visual_engineering/15_INFORMATION_DENSITY_STANDARD §Tables:
//   "Institutional tables should expose: Search, Sort, Filter, Export ...
//   dense but readable rows."
//
// This is the ONE table implementation in QuantHub (Doc 01 Primary Rule:
// "One responsibility. One library. One implementation."). TanStack Table
// is the headless sorting/filtering/column engine; TanStack Virtual takes
// over row rendering once a dataset is large enough that virtualizing pays
// for itself. Both are styled entirely through this file's own markup and
// the existing glassSurface()/design-token system — TanStack ships no CSS
// of its own, so nothing about the app's visual language changes.
//
// LAYOUT: rows render as CSS Grid (not a semantic <table>) with one shared
// `gridTemplateColumns` string computed ONCE from the visible columns and
// reused by the header and every row — virtualized or not. This was a
// deliberate choice after the first version used a real <table> and
// switched to independent per-row `display:table` elements once
// virtualized; each row recomputed its own column widths from its own cell
// content, so widths drifted between rows and text overlapped. A shared
// grid template makes header/row misalignment structurally impossible.
//
// RESPONSIVE COLUMN HIDING: `meta.hideBelow` filters columns out of the
// table entirely (not just visually) below the named breakpoint, computed
// client-side after mount (`useResponsiveTier`) so header and rows are
// always looking at the identical column set — no separate hide-in-CSS
// class that has to stay in sync with a separate JS list.
'use client'

import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import {
  type ColumnDef,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useVirtualizer } from '@tanstack/react-virtual'
import { ArrowDown, ArrowUp, ArrowUpDown, Download, Search } from 'lucide-react'
import { cn } from '@/lib/utils/cn'
import { glassSurface } from './Card'
import { EmptyState } from './States'

// Doc 02 §Responsive Breakpoints: Desktop 1400+ / Laptop 1024-1399 / Tablet
// 768-1023 / Mobile <768 — named to match tailwind.config.ts's `tablet`/
// `laptop`/`desktop` screens.
export type ResponsiveTier = 'tablet' | 'laptop' | 'desktop'
type Tier = 'mobile' | ResponsiveTier
const TIER_ORDER: Tier[] = ['mobile', 'tablet', 'laptop', 'desktop']

function computeTier(width: number): Tier {
  if (width >= 1400) return 'desktop'
  if (width >= 1024) return 'laptop'
  if (width >= 768) return 'tablet'
  return 'mobile'
}

// SSR-safe: server and the pre-hydration client render always assume
// 'desktop' (every column visible); an effect measures the real viewport
// after mount and narrows from there. Avoids a hydration mismatch from
// guessing a width the server can't know.
function useResponsiveTier(): Tier {
  const [tier, setTier] = useState<Tier>('desktop')
  useEffect(() => {
    const update = () => setTier(computeTier(window.innerWidth))
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])
  return tier
}

export interface InstitutionalColumnMeta {
  numeric?: boolean
  /** Column disappears below this breakpoint instead of shrinking unreadably (Doc 02). */
  hideBelow?: ResponsiveTier
  /** CSS grid track size, e.g. '2fr', '140px'. Defaults to '0.7fr' for numeric columns, '1fr' otherwise. */
  width?: string
}

// Re-exported so callers only need one import for column defs.
export type InstitutionalColumnDef<TData> = ColumnDef<TData, any> & {
  meta?: InstitutionalColumnMeta
}

interface InstitutionalTableProps<TData> {
  data: TData[]
  columns: InstitutionalColumnDef<TData>[]
  getRowId?: (row: TData, index: number) => string
  /** Global text search across every column's accessor value. Omit to hide the search box. */
  searchPlaceholder?: string
  /** File name (without extension) for the CSV export button. Omit to hide export. */
  exportFilename?: string
  initialSorting?: SortingState
  emptyState?: ReactNode
  className?: string
  /** Max height of the scroll viewport; required for virtualization to kick in. */
  maxHeight?: number
  /** Row count above which rendering switches to virtualized rows. */
  virtualizeThreshold?: number
  /** Row height in px — fixed once virtualized (react-virtual needs a stable estimate). */
  rowHeight?: number
  /** Makes rows clickable (cursor + hover emphasis) and fires with the row's original data. */
  onRowClick?: (row: TData) => void
  /** Row whose data matches this predicate gets a persistent selected highlight. */
  isRowSelected?: (row: TData) => boolean
  /** Extra classes per row (e.g. green/red tint by sign). */
  rowClassName?: (row: TData) => string
}

function csvEscape(value: unknown): string {
  const s = value == null ? '' : String(value)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function InstitutionalTable<TData>({
  data,
  columns,
  getRowId,
  searchPlaceholder,
  exportFilename,
  initialSorting = [],
  emptyState,
  className,
  maxHeight = 480,
  virtualizeThreshold = 150,
  rowHeight = 44,
  onRowClick,
  isRowSelected,
  rowClassName,
}: InstitutionalTableProps<TData>) {
  const tier = useResponsiveTier()
  const visibleColumns = useMemo(
    () =>
      columns.filter((c) => {
        const hideBelow = c.meta?.hideBelow
        return !hideBelow || TIER_ORDER.indexOf(tier) >= TIER_ORDER.indexOf(hideBelow)
      }),
    [columns, tier],
  )

  const [sorting, setSorting] = useState<SortingState>(initialSorting)
  const [globalFilter, setGlobalFilter] = useState('')

  const table = useReactTable({
    data,
    columns: visibleColumns,
    getRowId,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    enableMultiSort: true,
    globalFilterFn: 'includesString',
  })

  const rows = table.getRowModel().rows
  const headerCells = table.getHeaderGroups()[0]?.headers ?? []
  const virtualize = rows.length > virtualizeThreshold

  const gridTemplateColumns = useMemo(
    () =>
      headerCells
        .map((h) => {
          const meta = h.column.columnDef.meta as InstitutionalColumnMeta | undefined
          return meta?.width ?? (meta?.numeric ? '0.7fr' : '1fr')
        })
        .join(' '),
    [headerCells],
  )
  const gridStyle: CSSProperties = { gridTemplateColumns }

  const scrollRef = useRef<HTMLDivElement>(null)
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => rowHeight,
    overscan: 10,
    enabled: virtualize,
  })

  const exportCsv = () => {
    const cols = table.getVisibleLeafColumns()
    const header = cols.map((c) => csvEscape(typeof c.columnDef.header === 'string' ? c.columnDef.header : c.id))
    const body = rows.map((r) => cols.map((c) => csvEscape(r.getValue(c.id))).join(','))
    const csv = [header.join(','), ...body].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${exportFilename}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const hasToolbar = Boolean(searchPlaceholder || exportFilename)

  return (
    <div className={cn(glassSurface('flat'), className)}>
      {hasToolbar && (
        <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-2.5">
          {searchPlaceholder ? (
            <label className="relative flex min-w-0 flex-1 items-center">
              <Search size={14} className="pointer-events-none absolute left-2.5 text-fg-subtle" />
              <input
                type="text"
                value={globalFilter}
                onChange={(e) => setGlobalFilter(e.target.value)}
                placeholder={searchPlaceholder}
                className="w-full max-w-xs rounded-md border border-border bg-surface/60 py-1.5 pl-8 pr-2.5 text-xs text-fg placeholder:text-fg-subtle focus:border-border-strong focus:outline-none"
              />
            </label>
          ) : (
            <span />
          )}
          {exportFilename && (
            <button
              type="button"
              onClick={exportCsv}
              disabled={rows.length === 0}
              className="flex shrink-0 items-center gap-1.5 rounded-md border border-border bg-surface/60 px-2.5 py-1.5 text-[11px] font-medium text-fg-muted transition-colors hover:border-border-strong hover:text-fg disabled:pointer-events-none disabled:opacity-40"
            >
              <Download size={13} />
              Export CSV
            </button>
          )}
        </div>
      )}

      {rows.length === 0 ? (
        <div className="p-2">{emptyState ?? <EmptyState title="No rows" description="Nothing matches the current view." />}</div>
      ) : (
        <div ref={scrollRef} className="w-full overflow-auto" style={{ maxHeight: virtualize ? maxHeight : undefined }}>
          {/* Header — sticky, one grid row, its track sizes are the single source of truth every body row copies. */}
          <div
            className="sticky top-0 z-10 grid border-b border-border bg-surface-raised/95 backdrop-blur"
            style={gridStyle}
          >
            {headerCells.map((header) => {
              const meta = header.column.columnDef.meta as InstitutionalColumnMeta | undefined
              const sortState = header.column.getIsSorted()
              return (
                <div
                  key={header.id}
                  className={cn(
                    'px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-fg-subtle',
                    meta?.numeric && 'text-right',
                  )}
                >
                  {header.isPlaceholder ? null : header.column.getCanSort() ? (
                    <button
                      type="button"
                      onClick={header.column.getToggleSortingHandler()}
                      title={sortState ? undefined : 'Sort — shift-click to add a secondary sort'}
                      className={cn(
                        'inline-flex items-center gap-1 hover:text-fg-muted',
                        meta?.numeric && 'flex-row-reverse',
                      )}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {sortState === 'asc' ? (
                        <ArrowUp size={11} />
                      ) : sortState === 'desc' ? (
                        <ArrowDown size={11} />
                      ) : (
                        <ArrowUpDown size={11} className="opacity-30" />
                      )}
                    </button>
                  ) : (
                    flexRender(header.column.columnDef.header, header.getContext())
                  )}
                </div>
              )
            })}
          </div>

          {/* Body */}
          {virtualize ? (
            <div style={{ position: 'relative', height: virtualizer.getTotalSize() }}>
              {virtualizer.getVirtualItems().map((virtualRow) => (
                <div
                  key={rows[virtualRow.index].id}
                  onClick={onRowClick ? () => onRowClick(rows[virtualRow.index].original) : undefined}
                  className={cn(
                    'grid items-center border-b border-border/70 transition-colors duration-150 hover:bg-surface-hover/60',
                    onRowClick && 'cursor-pointer',
                    isRowSelected?.(rows[virtualRow.index].original) && 'bg-accent-soft',
                    rowClassName?.(rows[virtualRow.index].original),
                  )}
                  style={{
                    ...gridStyle,
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: rowHeight,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  {rows[virtualRow.index].getVisibleCells().map((cell) => {
                    const meta = cell.column.columnDef.meta as InstitutionalColumnMeta | undefined
                    return (
                      <div
                        key={cell.id}
                        className={cn('truncate px-4 text-table text-fg', meta?.numeric && 'text-right tabular-nums font-mono')}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          ) : (
            <div className="divide-y divide-border/70">
              {rows.map((row) => (
                <div
                  key={row.id}
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                  className={cn(
                    'grid items-center transition-colors duration-150 hover:bg-surface-hover/60',
                    onRowClick && 'cursor-pointer',
                    isRowSelected?.(row.original) && 'bg-accent-soft',
                    rowClassName?.(row.original),
                  )}
                  style={gridStyle}
                >
                  {row.getVisibleCells().map((cell) => {
                    const meta = cell.column.columnDef.meta as InstitutionalColumnMeta | undefined
                    return (
                      <div
                        key={cell.id}
                        className={cn('px-4 py-2.5 text-table text-fg', meta?.numeric && 'text-right tabular-nums font-mono')}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
