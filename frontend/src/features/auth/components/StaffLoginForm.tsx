import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Field, FieldLabel, FieldError, FieldGroup } from '@/components/ui/field'
import { useStaffLogin } from '@/features/auth/hooks/useAuthMutations'
import { getApiErrorMessage } from '@/lib/apiError'

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
})
type LoginValues = z.infer<typeof loginSchema>

interface StaffLoginFormProps {
  onSuccess?: () => void
}

export function StaffLoginForm({ onSuccess }: StaffLoginFormProps) {
  const login = useStaffLogin()
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  return (
    <form
      noValidate
      onSubmit={(e) => {
        void form.handleSubmit((values) => {
          login.mutate(values, { onSuccess })
        })(e)
      }}
    >
      <FieldGroup>
        <div>
          <h2 className="text-xl font-semibold">Sign in</h2>
          <p className="text-muted-foreground mt-1 text-sm">Staff access</p>
        </div>
        <Field data-invalid={Boolean(form.formState.errors.email)}>
          <FieldLabel htmlFor="email">Email</FieldLabel>
          <Input
            id="email"
            type="email"
            autoComplete="username"
            aria-invalid={Boolean(form.formState.errors.email)}
            {...form.register('email')}
          />
          {form.formState.errors.email && (
            <FieldError>{form.formState.errors.email.message}</FieldError>
          )}
        </Field>
        <Field data-invalid={Boolean(form.formState.errors.password)}>
          <FieldLabel htmlFor="password">Password</FieldLabel>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            aria-invalid={Boolean(form.formState.errors.password)}
            {...form.register('password')}
          />
          {form.formState.errors.password && (
            <FieldError>{form.formState.errors.password.message}</FieldError>
          )}
        </Field>
        {login.isError && (
          <FieldError>{getApiErrorMessage(login.error, 'Invalid email or password')}</FieldError>
        )}
        <Button type="submit" className="w-full" disabled={login.isPending}>
          {login.isPending ? 'Signing in…' : 'Sign in'}
        </Button>
      </FieldGroup>
    </form>
  )
}
