import { useNavigate, useLocation } from 'react-router'
import { Card, CardContent } from '@/components/ui/card'
import { StaffLoginForm } from '@/features/auth/components/StaffLoginForm'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/app/dashboard'

  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-muted/30 px-4 py-8">
      <div className="mb-6 flex flex-col items-center gap-1 text-center">
        <div className="bg-primary text-primary-foreground flex size-11 items-center justify-center rounded-xl text-lg font-bold">
          JBM
        </div>
        <h1 className="mt-2 text-lg font-semibold">AI Field Assistant</h1>
        <p className="text-muted-foreground text-sm">Plant operations dashboard</p>
      </div>
      <Card className="w-full max-w-sm">
        <CardContent className="pt-6">
          <StaffLoginForm onSuccess={() => void navigate(redirectTo, { replace: true })} />
        </CardContent>
      </Card>
    </div>
  )
}
