import { useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { PlusIcon } from 'lucide-react'
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
import {
  listUsers,
  createUser,
  updateUser,
  grantPlantAccess,
  listUserPlantAccess,
  type AdminUser,
} from '@/features/admin/api/users'
import { listPlants } from '@/features/admin/api/plants'
import { isAdminRole, roleLabel } from '@/features/auth/roles'
import type { UserRole } from '@/features/auth/store/authStore'
import { getApiErrorMessage } from '@/lib/apiError'

const STAFF_ROLE_OPTIONS: UserRole[] = [
  'plant_manager',
  'support_l2',
  'support_l3',
  'field_tech',
  'company_viewer',
]

const viewerSchema = z.object({
  fullName: z.string().min(2, 'Enter a name'),
  email: z.string().email('Enter a valid email'),
  password: z.string().min(4, 'Min 4 characters'),
  role: z.enum(STAFF_ROLE_OPTIONS as [UserRole, ...UserRole[]]),
  plantId: z.string().min(1, 'Select a plant'),
})
type ViewerValues = z.infer<typeof viewerSchema>

export function UsersPage() {
  const queryClient = useQueryClient()
  const { data: users = [] } = useQuery({ queryKey: ['admin', 'users'], queryFn: listUsers })
  const [open, setOpen] = useState(false)

  const toggleActive = useMutation({
    mutationFn: (user: AdminUser) => updateUser(user.id, { is_active: !user.is_active }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
    onError: (error) => toast.error(getApiErrorMessage(error, 'Could not update user')),
  })

  const columns: ColumnDef<AdminUser, unknown>[] = [
    { accessorKey: 'full_name', header: 'Name' },
    { accessorKey: 'email', header: 'Email' },
    {
      id: 'role',
      header: 'Role',
      cell: ({ row }) => (
        <Badge variant={isAdminRole(row.original.role) ? 'default' : 'secondary'}>
          {roleLabel(row.original.role)}
        </Badge>
      ),
    },
    {
      id: 'plant',
      header: 'Plant access',
      cell: ({ row }) =>
        isAdminRole(row.original.role) ? (
          'All plants'
        ) : (
          <PlantAccessCell userId={row.original.id} />
        ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <Badge
          className={
            row.original.is_active
              ? 'border-transparent bg-status-online/15 text-status-online'
              : undefined
          }
          variant={row.original.is_active ? 'secondary' : 'outline'}
        >
          {row.original.is_active ? 'Active' : 'Disabled'}
        </Badge>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) =>
        isAdminRole(row.original.role) ? null : (
          <div className="flex justify-end gap-1">
            <Button variant="ghost" size="sm" onClick={() => toggleActive.mutate(row.original)}>
              {row.original.is_active ? 'Disable' : 'Enable'}
            </Button>
          </div>
        ),
    },
  ]

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Users</h1>
          <p className="text-muted-foreground text-sm">
            Create staff accounts scoped to a single plant.
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>
          <PlusIcon className="size-4" /> Add staff user
        </Button>
      </div>

      <DataTable columns={columns} data={users} emptyMessage="No users yet" />

      <AddViewerDialog open={open} onOpenChange={setOpen} />
    </div>
  )
}

function AddViewerDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
}) {
  const queryClient = useQueryClient()
  const { data: plants = [] } = useQuery({ queryKey: ['admin', 'plants'], queryFn: listPlants })
  const form = useForm<ViewerValues>({
    resolver: zodResolver(viewerSchema),
    defaultValues: { fullName: '', email: '', password: '', role: 'plant_manager', plantId: '' },
  })

  const create = useMutation({
    mutationFn: async (values: ViewerValues) => {
      const user = await createUser({
        email: values.email,
        full_name: values.fullName,
        role: values.role,
        password: values.password,
        language: 'en',
      })
      await grantPlantAccess(user.id, values.plantId)
      return user
    },
    onSuccess: (user) => {
      toast.success(`User "${user.email}" created`)
      void queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      form.reset()
      onOpenChange(false)
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Could not create user')),
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
          <DialogTitle>Add staff user</DialogTitle>
          <DialogDescription>They get read access scoped to the chosen plant.</DialogDescription>
        </DialogHeader>
        <form
          id="add-viewer-form"
          onSubmit={(e) => {
            void submit(e)
          }}
        >
          <FieldGroup>
            <Field data-invalid={Boolean(form.formState.errors.fullName)}>
              <FieldLabel htmlFor="v-name">Full name</FieldLabel>
              <Input id="v-name" placeholder="Ravi Sharma" {...form.register('fullName')} />
              {form.formState.errors.fullName && (
                <FieldError>{form.formState.errors.fullName.message}</FieldError>
              )}
            </Field>
            <Field data-invalid={Boolean(form.formState.errors.email)}>
              <FieldLabel htmlFor="v-email">Email</FieldLabel>
              <Input
                id="v-email"
                type="email"
                placeholder="viewer@jbmgroup.com"
                {...form.register('email')}
              />
              {form.formState.errors.email && (
                <FieldError>{form.formState.errors.email.message}</FieldError>
              )}
            </Field>
            <Field data-invalid={Boolean(form.formState.errors.password)}>
              <FieldLabel htmlFor="v-pass">Password</FieldLabel>
              <Input
                id="v-pass"
                type="text"
                placeholder="Set a password"
                {...form.register('password')}
              />
              {form.formState.errors.password && (
                <FieldError>{form.formState.errors.password.message}</FieldError>
              )}
            </Field>
            <Field data-invalid={Boolean(form.formState.errors.role)}>
              <FieldLabel htmlFor="v-role">Role</FieldLabel>
              <Select
                value={form.watch('role')}
                onValueChange={(v) =>
                  form.setValue('role', v as UserRole, { shouldValidate: true })
                }
              >
                <SelectTrigger id="v-role">
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {STAFF_ROLE_OPTIONS.map((r) => (
                    <SelectItem key={r} value={r}>
                      {roleLabel(r)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field data-invalid={Boolean(form.formState.errors.plantId)}>
              <FieldLabel htmlFor="v-plant">Plant</FieldLabel>
              <Select
                value={form.watch('plantId')}
                onValueChange={(v) => form.setValue('plantId', v, { shouldValidate: true })}
              >
                <SelectTrigger id="v-plant">
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
          </FieldGroup>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="add-viewer-form" disabled={create.isPending}>
            Create user
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function PlantAccessCell({ userId }: { userId: string }) {
  const { data: plants = [] } = useQuery({
    queryKey: ['admin', 'users', userId, 'plant-access'],
    queryFn: () => listUserPlantAccess(userId),
  })
  if (plants.length === 0) return <span className="text-muted-foreground">None</span>
  return <span>{plants.map((p) => p.name).join(', ')}</span>
}
