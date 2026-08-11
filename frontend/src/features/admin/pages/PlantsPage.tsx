import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { PlusIcon, PowerOff } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Field, FieldLabel, FieldError, FieldGroup } from '@/components/ui/field'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { listCompanies } from '@/features/admin/api/companies'
import { listPlants, createPlant, updatePlant, type Plant } from '@/features/admin/api/plants'
import { listMachines } from '@/features/assets/api/machines'
import { getApiErrorMessage } from '@/lib/apiError'

/** Green "Active" pill (shared look with the online status colour). */
const ACTIVE_BADGE = 'border-transparent bg-status-online/15 text-status-online'

const plantSchema = z.object({
  name: z.string().min(2, 'Enter a plant name'),
  code: z.string().min(1, 'Enter a short code').max(6, 'Max 6 characters'),
  address: z.string().optional(),
})
type PlantValues = z.infer<typeof plantSchema>

export function PlantsPage() {
  const queryClient = useQueryClient()
  const { data: plants = [] } = useQuery({ queryKey: ['admin', 'plants'], queryFn: listPlants })
  const { data: machines = [] } = useQuery({
    queryKey: ['assets', 'machines'],
    queryFn: () => listMachines(),
  })
  const [open, setOpen] = useState(false)
  const [toDeactivate, setToDeactivate] = useState<Plant | null>(null)

  const deactivate = useMutation({
    mutationFn: (plant: Plant) => updatePlant(plant.id, { is_active: false }),
    onSuccess: (_data, plant) => {
      toast.success(`Deactivated ${plant.name}`)
      void queryClient.invalidateQueries({ queryKey: ['admin', 'plants'] })
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Could not deactivate plant')),
  })

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Plants</h1>
          <p className="text-muted-foreground text-sm">
            Manufacturing sites managed on the platform.
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>
          <PlusIcon className="size-4" /> Add plant
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {plants.map((plant) => {
          const count = machines.filter((m) => m.plant_id === plant.id).length
          return (
            <Card key={plant.id}>
              <CardContent className="flex flex-col gap-2 pt-6">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-semibold">{plant.name}</div>
                    <div className="text-muted-foreground text-sm">{plant.address ?? '—'}</div>
                  </div>
                  <Badge variant="outline">{plant.code}</Badge>
                </div>
                <div className="text-muted-foreground mt-2 flex items-center justify-between text-sm">
                  <span>{count} machines</span>
                  <div className="flex items-center gap-1">
                    <Badge
                      className={plant.is_active ? ACTIVE_BADGE : undefined}
                      variant={plant.is_active ? 'secondary' : 'outline'}
                    >
                      {plant.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                    {plant.is_active && (
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="text-status-offline hover:text-status-offline"
                        aria-label={`Deactivate ${plant.name}`}
                        onClick={() => setToDeactivate(plant)}
                      >
                        <PowerOff className="size-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
        {plants.length === 0 && <p className="text-muted-foreground text-sm">No plants yet.</p>}
      </div>

      <AddPlantDialog open={open} onOpenChange={setOpen} />

      <Dialog open={toDeactivate !== null} onOpenChange={(o) => !o && setToDeactivate(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Deactivate plant?</DialogTitle>
            <DialogDescription>
              <span className="font-medium">{toDeactivate?.name}</span> will be hidden from active
              views. Its machines, QR codes, and tickets are kept.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setToDeactivate(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (toDeactivate) deactivate.mutate(toDeactivate)
                setToDeactivate(null)
              }}
            >
              Deactivate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function AddPlantDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
}) {
  const queryClient = useQueryClient()
  const { data: companies = [] } = useQuery({
    queryKey: ['admin', 'companies'],
    queryFn: listCompanies,
  })
  const company = companies[0]

  const form = useForm<PlantValues>({
    resolver: zodResolver(plantSchema),
    defaultValues: { name: '', code: '', address: '' },
  })

  const create = useMutation({
    mutationFn: (values: PlantValues) =>
      createPlant({
        company_id: company!.id,
        name: values.name,
        code: values.code.toUpperCase(),
        address: values.address || null,
        timezone: 'Asia/Kolkata',
      }),
    onSuccess: (plant) => {
      toast.success(`Plant "${plant.name}" added`)
      void queryClient.invalidateQueries({ queryKey: ['admin', 'plants'] })
      form.reset()
      onOpenChange(false)
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Could not add plant')),
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
          <DialogTitle>Add plant</DialogTitle>
          <DialogDescription>Create a new manufacturing site.</DialogDescription>
        </DialogHeader>
        {!company ? (
          <p className="text-muted-foreground text-sm">
            No company exists yet — seed or create one via the API before adding plants.
          </p>
        ) : (
          <form
            id="add-plant-form"
            onSubmit={(e) => {
              void submit(e)
            }}
          >
            <FieldGroup>
              <Field data-invalid={Boolean(form.formState.errors.name)}>
                <FieldLabel htmlFor="p-name">Plant name</FieldLabel>
                <Input id="p-name" placeholder="Faridabad Plant" {...form.register('name')} />
                {form.formState.errors.name && (
                  <FieldError>{form.formState.errors.name.message}</FieldError>
                )}
              </Field>
              <Field data-invalid={Boolean(form.formState.errors.code)}>
                <FieldLabel htmlFor="p-code">Code</FieldLabel>
                <Input id="p-code" placeholder="FBD" {...form.register('code')} />
                {form.formState.errors.code && (
                  <FieldError>{form.formState.errors.code.message}</FieldError>
                )}
              </Field>
              <Field data-invalid={Boolean(form.formState.errors.address)}>
                <FieldLabel htmlFor="p-loc">Address</FieldLabel>
                <Input id="p-loc" placeholder="Faridabad, Haryana" {...form.register('address')} />
                {form.formState.errors.address && (
                  <FieldError>{form.formState.errors.address.message}</FieldError>
                )}
              </Field>
            </FieldGroup>
          </form>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="add-plant-form" disabled={!company || create.isPending}>
            Add plant
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
