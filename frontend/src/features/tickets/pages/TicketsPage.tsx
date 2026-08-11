import { useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DataTable } from '@/components/DataTable'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { canWrite, isAdminRole } from '@/features/auth/roles'
import { useScopedPlants } from '@/features/auth/hooks/useScopedPlants'
import { listMachines } from '@/features/assets/api/machines'
import { listTickets, updateTicket, type Ticket } from '@/features/tickets/api/tickets'
import { getApiErrorMessage } from '@/lib/apiError'

type TicketPriority = Ticket['priority']
type TicketStatus = Ticket['status']

const PRIORITY_STYLES: Record<TicketPriority, string> = {
  low: 'bg-muted text-muted-foreground',
  medium: 'bg-status-online/15 text-status-online',
  high: 'bg-status-degraded/15 text-status-degraded',
  critical: 'bg-status-offline/15 text-status-offline',
}

const STATUS_LABEL: Record<TicketStatus, string> = {
  new: 'New',
  assigned: 'Assigned',
  in_progress: 'In progress',
  on_hold: 'On hold',
  resolved: 'Resolved',
  closed: 'Closed',
  reopened: 'Reopened',
}

const CLOSED_STATUSES: TicketStatus[] = ['resolved', 'closed']

function relativeTime(iso: string) {
  const hrs = Math.round((Date.now() - new Date(iso).getTime()) / 3600000)
  if (hrs < 1) return 'just now'
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.round(hrs / 24)}d ago`
}

type Filter = 'all' | 'open' | 'closed'

export function TicketsPage() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const isAdmin = isAdminRole(user?.role)
  const canClose = canWrite(user?.role)
  const { plants } = useScopedPlants()
  const [filter, setFilter] = useState<Filter>('all')

  const { data: tickets = [] } = useQuery({ queryKey: ['tickets'], queryFn: () => listTickets() })
  const { data: machines = [] } = useQuery({
    queryKey: ['assets', 'machines'],
    queryFn: () => listMachines(),
  })
  const machineById = new Map(machines.map((m) => [m.id, m]))
  const plantById = new Map(plants.map((p) => [p.id, p]))

  const closeTicket = useMutation({
    mutationFn: (ticket: Ticket) => updateTicket(ticket.id, { status: 'closed' }),
    onSuccess: () => {
      toast.success('Ticket closed')
      void queryClient.invalidateQueries({ queryKey: ['tickets'] })
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Could not close ticket')),
  })

  const filtered = tickets.filter((t) => {
    if (filter === 'open') return !CLOSED_STATUSES.includes(t.status)
    if (filter === 'closed') return CLOSED_STATUSES.includes(t.status)
    return true
  })

  const columns: ColumnDef<Ticket, unknown>[] = [
    {
      id: 'title',
      header: 'Issue',
      cell: ({ row }) => {
        const machine = machineById.get(row.original.machine_id)
        const plant = machine ? plantById.get(machine.plant_id) : undefined
        return (
          <div>
            <div className="font-medium">{row.original.title}</div>
            <div className="text-muted-foreground text-xs">
              {row.original.ticket_number} · {machine?.name ?? '—'}
              {plant ? ` · ${plant.name}` : ''}
            </div>
          </div>
        )
      },
    },
    {
      id: 'priority',
      header: 'Priority',
      cell: ({ row }) => (
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize ${PRIORITY_STYLES[row.original.priority]}`}
        >
          {row.original.priority}
        </span>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <Badge variant={CLOSED_STATUSES.includes(row.original.status) ? 'outline' : 'secondary'}>
          {STATUS_LABEL[row.original.status]}
        </Badge>
      ),
    },
    { id: 'created', header: 'Created', cell: ({ row }) => relativeTime(row.original.created_at) },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        if (!canClose) return null
        const closed = row.original.status === 'closed'
        return (
          <Button
            variant={closed ? 'ghost' : 'outline'}
            size="sm"
            disabled={closed || closeTicket.isPending}
            onClick={() => closeTicket.mutate(row.original)}
          >
            {closed ? 'Closed' : 'Close ticket'}
          </Button>
        )
      },
    },
  ]

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold">Tickets</h1>
        <p className="text-muted-foreground text-sm">
          {isAdmin
            ? 'Review and close issues raised from the shop floor.'
            : 'Issues raised for your plant.'}
        </p>
      </div>

      <Tabs value={filter} onValueChange={(v) => setFilter(v as Filter)}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="open">Open</TabsTrigger>
          <TabsTrigger value="closed">Closed</TabsTrigger>
        </TabsList>
      </Tabs>

      <DataTable columns={columns} data={filtered} emptyMessage="No tickets in this view" />
    </div>
  )
}
