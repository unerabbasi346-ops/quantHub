// Governing specification: Doc 06 — UI/UX Design System (QH-006 v1.0)
// Per Doc 00 §14.11
//
// TEMPORARY Step 4.0 showcase — not one of the 9 route groups (Doc 08
// §Application Structure), not linked from SidebarNav, and uses only
// static example data (no service/hook/API calls — no data wiring per
// this step's scope). Exists solely to prove the theme tokens, app
// shell, and core reusable components render correctly together. Should
// be removed once real feature pages (Step 4.2+) exercise the same
// components with live data.
//
// 'use client': this demo page passes an inline onClick into ErrorState's
// onRetry (a Client Component prop) — Next.js App Router disallows passing
// functions from a Server Component across that boundary, so the page
// itself is marked client. A real feature page (Step 4.2+) would instead
// pass a real retry handler from its own 'use client' hook-driven component.
'use client'

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ContextPanel,
  ErrorState,
  EmptyState,
  LoadingState,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tabs,
  pnlBadgeVariant,
} from '@/components/ui'

const EXAMPLE_ROWS = [
  { symbol: 'BTC/USDT', qty: '0.00405983', price: '61,959.99', pnl: -0.0087 },
  { symbol: 'ETH/USDT', qty: '1.20000000', price: '3,412.50', pnl: 12.44 },
]

export default function DesignSystemPreviewPage() {
  return (
    <div className="flex gap-6">
      <div className="flex-1 space-y-8">
        <div>
          <h1 className="text-2xl font-semibold text-fg">Design System Foundation</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Step 4.0 — Doc 06 theme tokens + core components (static example data only).
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Buttons</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            <Button variant="primary">Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="danger">Danger</Button>
            <Button variant="primary" disabled>
              Disabled
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Badges</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Badge variant="profit">Profit</Badge>
            <Badge variant="risk">Risk</Badge>
            <Badge variant="info">Info</Badge>
            <Badge variant="warning">Warning</Badge>
            <Badge variant="neutral">Neutral</Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Positions (example)</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Quantity</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Unrealized P&amp;L</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {EXAMPLE_ROWS.map((row) => (
                  <TableRow key={row.symbol}>
                    <TableCell>{row.symbol}</TableCell>
                    <TableCell numeric>{row.qty}</TableCell>
                    <TableCell numeric>{row.price}</TableCell>
                    <TableCell numeric>
                      <Badge variant={pnlBadgeVariant(row.pnl)}>
                        {row.pnl >= 0 ? '+' : ''}
                        {row.pnl.toFixed(2)}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tabs</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs
              items={[
                { value: 'overview', label: 'Overview', content: <p className="text-sm text-fg-muted">Overview panel content.</p> },
                { value: 'orders', label: 'Orders', content: <p className="text-sm text-fg-muted">Orders panel content.</p> },
                { value: 'risk', label: 'Risk', content: <p className="text-sm text-fg-muted">Risk panel content.</p> },
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Loading / Empty / Error states</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <LoadingState />
            <EmptyState
              title="No positions yet"
              description="Positions will appear here once a strategy has been run."
            />
            <ErrorState
              description="Could not reach the API."
              onRetry={() => {}}
            />
          </CardContent>
        </Card>
      </div>

      <ContextPanel title="Contextual Panel (example)">
        <p className="text-sm text-fg-muted">
          Doc 06 §Layout&apos;s optional contextual panel — composed by a
          feature page when it has something contextual to show.
        </p>
      </ContextPanel>
    </div>
  )
}
