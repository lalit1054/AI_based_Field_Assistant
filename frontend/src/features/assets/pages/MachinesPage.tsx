import { useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { PlusIcon, WrenchIcon } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Field, FieldLabel, FieldError, FieldGroup } from '@/components/ui/field'
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { DataTable } from '@/components/DataTable'
import { StatusBadge } from '@/components/StatusBadge'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { useScopedPlants } from '@/features/auth/hooks/useScopedPlants'
import { isAdminRole } from '@/features/auth/roles'
import { listLines } from '@/features/admin/api/lines'
import { listMachineHealth } from '@/features/assets/api/health'
import {
  listMachines,
  createMachine,
  updateMachine,
  type Machine,
} from '@/features/assets/api/machines'
import { getApiErrorMessage } from '@/lib/apiError'

function relativeTime(iso: string | null) {
  if (!iso) return 'never'
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.round(hrs / 24)}d ago`
}

const LIFECYCLE_BADGE: Record<Machine['status'], { label: string; className?: string }> = {
  active: {
    label: 'Active',
    className: 'border-transparent bg-status-online/15 text-status-online',
  },
  maintenance: {
    label: 'Maintenance',
    className: 'border-transparent bg-status-degraded/15 text-status-degraded',
  },
  decommissioned: { label: 'Decommissioned' },
}

export function MachinesPage() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const isAdmin = isAdminRole(user?.role)
  const { plants } = useScopedPlants()

  const [plantFilter, setPlantFilter] = useState<string>('all')
  const [addOpen, setAddOpen] = useState(false)

  const { data: allMachines = [] } = useQuery({
    queryKey: ['assets', 'machines'],
    queryFn: () => listMachines(),
  })
  const { data: health = [] } = useQuery({
    queryKey: ['health', 'machines'],
    queryFn: () => listMachineHealth(),
  })
  const healthByMachine = new Map(health.map((h) => [h.machine_id, h]))

  const scopedPlantIds = new Set(plants.map((p) => p.id))
  const inScope = isAdmin ? allMachines : allMachines.filter((m) => scopedPlantIds.has(m.plant_id))
  const machines =
    plantFilter === 'all' ? inScope : inScope.filter((m) => m.plant_id === plantFilter)

  const setMaintenance = useMutation({
    mutationFn: (machine: Machine) =>
      updateMachine(machine.id, {
        status: machine.status === 'maintenance' ? 'active' : 'maintenance',
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['assets', 'machines'] }),
    onError: (error) => toast.error(getApiErrorMessage(error, 'Could not update machine')),
  })

  const columns: ColumnDef<Machine, unknown>[] = [
    {
      id: 'name',
      header: 'Machine',
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.name}</div>
          <div className="text-muted-foreground text-xs">{row.original.machine_type}</div>
        </div>
      ),
    },
    {
      id: 'plant',
      header: 'Plant',
      cell: ({ row }) => plants.find((p) => p.id === row.original.plant_id)?.name ?? '—',
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const badge = LIFECYCLE_BADGE[row.original.status]
        return (
          <Badge variant={badge.className ? 'secondary' : 'outline'} className={badge.className}>
            {badge.label}
          </Badge>
        )
      },
    },
    {
      id: 'online',
      header: 'Live status',
      cell: ({ row }) => {
        const h = healthByMachine.get(row.original.id)
        return h ? (
          <StatusBadge
            status={h.is_online ? 'online' : 'offline'}
            label={h.is_online ? 'Online' : 'Offline'}
          />
        ) : (
          <span className="text-muted-foreground text-sm">No data</span>
        )
      },
    },
    {
      id: 'lastSeen',
      header: 'Last heartbeat',
      cell: ({ row }) => relativeTime(healthByMachine.get(row.original.id)?.last_heartbeat ?? null),
    },
    ...(isAdmin
      ? [
          {
            id: 'actions',
            header: '',
            cell: ({ row }) => (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMaintenance.mutate(row.original)}
                disabled={row.original.status === 'decommissioned'}
              >
                <WrenchIcon className="size-4" />
                {row.original.status === 'maintenance' ? 'Set active' : 'Set maintenance'}
              </Button>
            ),
          } satisfies ColumnDef<Machine, unknown>,
        ]
      : []),
  ]

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">Machine Health</h1>
          <p className="text-muted-foreground text-sm">
            Live status across all monitored equipment.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {plants.length > 1 && (
            <Select value={plantFilter} onValueChange={setPlantFilter}>
              <SelectTrigger className="max-w-[200px]">
                <SelectValue placeholder="All plants" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All plants</SelectItem>
                {plants.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {isAdmin && (
            <Button onClick={() => setAddOpen(true)}>
              <PlusIcon className="size-4" /> Add machine
            </Button>
          )}
        </div>
      </div>

      <DataTable columns={columns} data={machines} emptyMessage="No machines found" />

      {isAdmin && <AddMachineDialog open={addOpen} onOpenChange={setAddOpen} />}
    </div>
  )
}

const machineSchema = z.object({
  name: z.string().min(2, 'Enter a machine name'),
  plantId: z.string().min(1, 'Select a plant'),
  lineId: z.string().optional(),
})
type MachineValues = z.infer<typeof machineSchema>

function AddMachineDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
}) {
  const queryClient = useQueryClient()
  const { plants } = useScopedPlants()
  const form = useForm<MachineValues>({
    resolver: zodResolver(machineSchema),
    defaultValues: { name: '', plantId: '', lineId: '' },
  })
  const plantId = form.watch('plantId')

  const { data: lines = [] } = useQuery({
    queryKey: ['admin', 'lines', plantId],
    queryFn: () => listLines(plantId),
    enabled: Boolean(plantId),
  })

  const create = useMutation({
    mutationFn: (values: MachineValues) =>
      createMachine({
        plant_id: values.plantId,
        line_id: values.lineId || null,
        machine_type: 'VISUAL_INSPECTION',
        name: values.name,
      }),
    onSuccess: (machine) => {
      toast.success(`Machine "${machine.name}" added`)
      void queryClient.invalidateQueries({ queryKey: ['assets', 'machines'] })
      form.reset()
      onOpenChange(false)
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Could not add machine')),
  })

  const submit = form.handleSubmit((values) => create.mutate(values))

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) form.reset()
        onOpenChange(o)
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add machine</DialogTitle>
          <DialogDescription>
            Register a machine under a plant and, optionally, a line.
          </DialogDescription>
        </DialogHeader>
        <form
          id="add-machine-form"
          onSubmit={(e) => {
            void submit(e)
          }}
        >
          <FieldGroup>
            <Field data-invalid={Boolean(form.formState.errors.name)}>
              <FieldLabel htmlFor="m-name">Machine name</FieldLabel>
              <Input id="m-name" placeholder="VI 12 Parts Inspection" {...form.register('name')} />
              {form.formState.errors.name && (
                <FieldError>{form.formState.errors.name.message}</FieldError>
              )}
            </Field>
            <Field data-invalid={Boolean(form.formState.errors.plantId)}>
              <FieldLabel htmlFor="m-plant">Plant</FieldLabel>
              <Select
                value={form.watch('plantId')}
                onValueChange={(v) => form.setValue('plantId', v, { shouldValidate: true })}
              >
                <SelectTrigger id="m-plant">
                  <SelectValue placeholder="Select a plant" />
                </SelectTrigger>
                <SelectContent>
                  {plants.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {form.formState.errors.plantId && (
                <FieldError>{form.formState.errors.plantId.message}</FieldError>
              )}
            </Field>
            <Field>
              <FieldLabel htmlFor="m-line">Line (optional)</FieldLabel>
              <Select
                value={form.watch('lineId')}
                onValueChange={(v) => form.setValue('lineId', v, { shouldValidate: true })}
                disabled={!plantId}
              >
                <SelectTrigger id="m-line">
                  <SelectValue placeholder="No line" />
                </SelectTrigger>
                <SelectContent>
                  {lines.map((l) => (
                    <SelectItem key={l.id} value={l.id}>
                      {l.name ?? `Line ${l.line_number}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </FieldGroup>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="add-machine-form" disabled={create.isPending}>
            Add machine
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
