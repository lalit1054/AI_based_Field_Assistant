import { Navigate, Outlet } from 'react-router'
import type { UserRole } from '@/features/auth/store/authStore'
import { useAuth } from '@/features/auth/hooks/useAuth'

interface RequireRoleProps {
  allow: UserRole[]
}

/** Assumes it runs beneath <RequireAuth>, so `user` is guaranteed to be set. */
export function RequireRole({ allow }: RequireRoleProps) {
  const { user } = useAuth()

  if (!user || !allow.includes(user.role)) {
    return <Navigate to="/403" replace />
  }

  return <Outlet />
}
