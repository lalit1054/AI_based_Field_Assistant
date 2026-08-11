import { NavLink, Outlet } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { LayoutDashboard, Ticket, Server, Factory, Users, QrCode, LogOut } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { isAdminRole, roleLabel, SCOPED_STAFF_ROLES } from '@/features/auth/roles'
import { listUserPlantAccess } from '@/features/admin/api/users'
import type { UserRole } from '@/features/auth/store/authStore'

interface NavItem {
  to: string
  label: string
  icon: typeof Ticket
  roles: UserRole[]
}

const NAV_ITEMS: NavItem[] = [
  {
    to: '/app/dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    roles: ['admin', ...SCOPED_STAFF_ROLES],
  },
  { to: '/app/plants', label: 'Plants', icon: Factory, roles: ['admin'] },
  {
    to: '/app/machines',
    label: 'Machine Health',
    icon: Server,
    roles: ['admin', ...SCOPED_STAFF_ROLES],
  },
  { to: '/app/tickets', label: 'Tickets', icon: Ticket, roles: ['admin', ...SCOPED_STAFF_ROLES] },
  { to: '/app/qr', label: 'QR Codes', icon: QrCode, roles: ['admin'] },
  { to: '/app/users', label: 'Users', icon: Users, roles: ['admin'] },
]

export function StaffShell() {
  const { user, logout } = useAuth()
  const role = user?.role ?? 'company_viewer'
  const items = NAV_ITEMS.filter((item) => item.roles.includes(role))

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .map((part) => part[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : '?'

  const { data: accessiblePlants = [] } = useQuery({
    queryKey: ['admin', 'users', user?.id, 'plant-access'],
    queryFn: () => listUserPlantAccess(user!.id),
    enabled: Boolean(user) && !isAdminRole(role),
  })
  const plantLabel = isAdminRole(role)
    ? 'All plants'
    : accessiblePlants.length > 0
      ? accessiblePlants.map((p) => p.name).join(', ')
      : 'No plants assigned'

  return (
    <div className="flex min-h-svh">
      <aside className="border-border bg-sidebar text-sidebar-foreground hidden w-64 shrink-0 flex-col border-r md:flex">
        <div className="border-border flex h-16 items-center gap-2 border-b px-4">
          <div className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-lg text-xs font-bold">
            JBM
          </div>
          <div className="flex flex-col leading-tight">
            <span className="text-sm font-semibold">Field Assistant</span>
            <span className="text-muted-foreground text-xs">Plant Operations</span>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {items.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'hover:bg-sidebar-accent/60',
                )
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="border-border flex h-16 items-center justify-end gap-3 border-b px-4">
          <div className="mr-auto flex flex-col leading-tight md:hidden">
            <span className="text-sm font-semibold">JBM Field Assistant</span>
          </div>
          <div className="hidden flex-col items-end leading-tight sm:flex">
            <span className="text-sm font-medium">{user?.full_name}</span>
            <span className="text-muted-foreground text-xs">
              {roleLabel(role)} · {plantLabel}
            </span>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-2 rounded-full outline-none">
              <Avatar className="size-9">
                <AvatarFallback>{initials}</AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => logout()}>
                <LogOut className="size-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main className="bg-muted/20 flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
