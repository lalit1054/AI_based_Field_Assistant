import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { Factory, Server, Ticket, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { getDashboardStats } from '@/features/dashboard/api/dashboard'

export function DashboardPage() {
  const { user } = useAuth()
  const { data } = useQuery({ queryKey: ['dashboard', 'stats'], queryFn: getDashboardStats })

  const plantsCount = data?.plants_count ?? 0
  const machinesCount = data?.machines_count ?? 0
  const online = data?.machines_online ?? 0
  const offline = data?.machines_offline ?? 0
  const openTickets = data?.open_tickets_count ?? 0
  const recentTickets = data?.recent_tickets ?? []

  const stats = [
    { label: 'Plants', value: plantsCount, icon: Factory, to: '/app/plants' },
    { label: 'Machines', value: machinesCount, icon: Server, to: '/app/machines' },
    { label: 'Open tickets', value: openTickets, icon: Ticket, to: '/app/tickets' },
    { label: 'Offline machines', value: offline, icon: AlertTriangle, to: '/app/machines' },
  ]

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Welcome, {user?.full_name?.split(' ')[0]}</h1>
        <p className="text-muted-foreground text-sm">Here's how your plants are doing right now.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, to }) => (
          <Link key={label} to={to}>
            <Card className="hover:border-primary/40 transition-colors">
              <CardContent className="flex items-center gap-4 pt-6">
                <div className="bg-primary/10 text-primary flex size-11 items-center justify-center rounded-xl">
                  <Icon className="size-5" />
                </div>
                <div>
                  <div className="text-2xl font-semibold">{value}</div>
                  <div className="text-muted-foreground text-sm">{label}</div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Fleet health</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <HealthRow
              label="Online"
              count={online}
              total={machinesCount}
              className="bg-status-online"
            />
            <HealthRow
              label="Offline"
              count={offline}
              total={machinesCount}
              className="bg-status-offline"
            />
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Recent tickets</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {recentTickets.map((t) => (
              <div
                key={t.id}
                className="flex items-center justify-between gap-3 border-b py-2 last:border-0"
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">{t.title}</div>
                  <div className="text-muted-foreground truncate text-xs">{t.machine_name}</div>
                </div>
                <span className="text-muted-foreground shrink-0 text-xs capitalize">
                  {t.status.replace('_', ' ')}
                </span>
              </div>
            ))}
            {recentTickets.length === 0 && (
              <p className="text-muted-foreground text-sm">No tickets yet.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function HealthRow({
  label,
  count,
  total,
  className,
}: {
  label: string
  count: number
  total: number
  className: string
}) {
  const pct = total ? Math.round((count / total) * 100) : 0
  return (
    <div className="flex items-center gap-3">
      <div className="w-16 text-sm font-medium">{label}</div>
      <div className="bg-muted h-2 flex-1 overflow-hidden rounded-full">
        <div className={`h-full ${className}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right text-sm font-medium">{count}</span>
    </div>
  )
}
