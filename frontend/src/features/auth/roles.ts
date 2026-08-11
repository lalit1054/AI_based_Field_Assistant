import type { UserRole } from '@/features/auth/store/authStore'

/**
 * The backend has 7 roles but the UI only distinguishes two staff tiers:
 * `admin` (full nav — plants/users/QR/machine writes) and everyone else
 * with a staff role (scoped/read-mostly, today's "plant viewer" shell).
 * `operator` never reaches the staff shell — it's the QR-scan flow.
 */
export const SCOPED_STAFF_ROLES: UserRole[] = [
  'plant_manager',
  'support_l2',
  'support_l3',
  'field_tech',
  'company_viewer',
]

export const STAFF_ROLES: UserRole[] = ['admin', ...SCOPED_STAFF_ROLES]

export function isAdminRole(role: UserRole | undefined): boolean {
  return role === 'admin'
}

/** Mirrors the backend's WRITE_ROLES tuple in routes_tickets.py/routes_assets.py/routes_qr.py. */
const WRITE_ROLES: UserRole[] = ['admin', 'support_l2', 'support_l3', 'plant_manager']

export function canWrite(role: UserRole | undefined): boolean {
  return Boolean(role && WRITE_ROLES.includes(role))
}

const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Administrator',
  plant_manager: 'Plant Manager',
  support_l2: 'Support (L2)',
  support_l3: 'Support (L3)',
  field_tech: 'Field Technician',
  company_viewer: 'Company Viewer',
  operator: 'Operator',
}

export function roleLabel(role: UserRole | undefined): string {
  return role ? ROLE_LABELS[role] : 'Unknown'
}
