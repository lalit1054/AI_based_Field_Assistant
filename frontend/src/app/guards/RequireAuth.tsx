import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { SkeletonBlock } from '@/components/feedback/SkeletonBlock'

interface RequireAuthProps {
  loginPath?: string
}

export function RequireAuth({ loginPath = '/login' }: RequireAuthProps) {
  const { isAuthenticated, isBootstrapping } = useAuth()
  const location = useLocation()

  if (isBootstrapping) {
    return (
      <div className="flex min-h-svh items-center justify-center p-6">
        <SkeletonBlock className="w-full max-w-sm" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to={loginPath} replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}
