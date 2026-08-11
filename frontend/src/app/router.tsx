import { createBrowserRouter, Navigate } from 'react-router'
import { RequireAuth } from '@/app/guards/RequireAuth'
import { RequireRole } from '@/app/guards/RequireRole'
import { StaffShell } from '@/components/layout/StaffShell'
import { OperatorShell } from '@/components/layout/OperatorShell'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { QrLandingPage } from '@/features/qr-landing/pages/QrLandingPage'
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage'
import { PlantsPage } from '@/features/admin/pages/PlantsPage'
import { UsersPage } from '@/features/admin/pages/UsersPage'
import { MachinesPage } from '@/features/assets/pages/MachinesPage'
import { TicketsPage } from '@/features/tickets/pages/TicketsPage'
import { QrCodesPage } from '@/features/qr/pages/QrCodesPage'
import { NotFoundPage } from '@/app/NotFoundPage'
import { ForbiddenPage } from '@/app/ForbiddenPage'
import { STAFF_ROLES } from '@/features/auth/roles'

// The operator QR-scan landing (`/a/:token`) is public; the rest is the
// admin/staff dashboard, gated to STAFF_ROLES (everything but `operator`).
export const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/login" replace /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/403', element: <ForbiddenPage /> },
  {
    // Public operator flow — reached by scanning a machine's QR sticker. No auth.
    element: <OperatorShell />,
    children: [{ path: '/a/:token', element: <QrLandingPage /> }],
  },
  {
    element: <RequireAuth loginPath="/login" />,
    children: [
      {
        element: <RequireRole allow={STAFF_ROLES} />,
        children: [
          {
            path: '/app',
            element: <StaffShell />,
            children: [
              { index: true, element: <Navigate to="/app/dashboard" replace /> },
              { path: 'dashboard', element: <DashboardPage /> },
              { path: 'plants', element: <PlantsPage /> },
              { path: 'machines', element: <MachinesPage /> },
              { path: 'tickets', element: <TicketsPage /> },
              { path: 'qr', element: <QrCodesPage /> },
              { path: 'users', element: <UsersPage /> },
            ],
          },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
])
