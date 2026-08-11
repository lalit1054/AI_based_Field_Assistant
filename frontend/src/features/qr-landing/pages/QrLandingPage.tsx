import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  CheckCircle2,
  QrCode,
  AlertTriangle,
  Wrench,
  Sparkles,
  Activity,
  ChevronRight,
  ChevronLeft,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Field, FieldLabel, FieldError, FieldGroup } from '@/components/ui/field'
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { SkeletonBlock } from '@/components/feedback/SkeletonBlock'
import { useAuth } from '@/features/auth/hooks/useAuth'
import { usePhoneLogin } from '@/features/auth/hooks/useAuthMutations'
import { resolveQrToken, type QrResolveOut } from '@/features/qr-landing/api/qrLanding'
import { getMachineHealth } from '@/features/assets/api/health'
import {
  createChatSession,
  sendChatMessage,
  type ChatMessage as ApiChatMessage,
} from '@/features/chat/api/chat'
import { createTicket } from '@/features/tickets/api/tickets'
import { getApiErrorMessage } from '@/lib/apiError'

function relativeTime(iso: string | null | undefined) {
  if (!iso) return 'never'
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs} hr ago`
  return `${Math.round(hrs / 24)} days ago`
}

type View = 'menu' | 'ask' | 'health' | 'report'

export function QrLandingPage() {
  const { token = '' } = useParams()
  const { isAuthenticated, isBootstrapping } = useAuth()
  const { data, isLoading } = useQuery({
    queryKey: ['qr-landing', token],
    queryFn: () => resolveQrToken(token),
    enabled: Boolean(token),
  })

  if (isLoading || isBootstrapping || !data) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <SkeletonBlock className="w-full max-w-sm" />
      </div>
    )
  }

  if ('error' in data) {
    return <InvalidToken reason={data.error} />
  }

  if (!isAuthenticated) {
    return <PhoneGate machineName={data.machine.machine_name} />
  }

  return <MachineHub machine={data.machine} />
}

function InvalidToken({ reason }: { reason: 'not_found' | 'revoked' }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
      <div className="bg-status-offline/10 text-status-offline flex size-14 items-center justify-center rounded-full">
        <QrCode className="size-7" />
      </div>
      <h1 className="text-lg font-semibold">
        {reason === 'revoked' ? 'This QR code is no longer active' : 'QR code not recognised'}
      </h1>
      <p className="text-muted-foreground text-sm">
        {reason === 'revoked'
          ? 'A new sticker may have been issued for this machine. Please contact your supervisor.'
          : "We couldn't find a machine for this code. Check that you scanned the right sticker."}
      </p>
    </div>
  )
}

const phoneSchema = z.object({
  phone: z.string().regex(/^\+[1-9]\d{7,14}$/, 'Enter a valid phone number, e.g. +919800000010'),
})
type PhoneValues = z.infer<typeof phoneSchema>

function PhoneGate({ machineName }: { machineName: string }) {
  const login = usePhoneLogin()
  const form = useForm<PhoneValues>({
    resolver: zodResolver(phoneSchema),
    defaultValues: { phone: '' },
  })

  const submit = form.handleSubmit((values) => login.mutate(values.phone))

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-4 text-center">
      <div>
        <h1 className="text-lg font-semibold">Sign in to continue</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Enter your phone number to ask questions or report an issue for{' '}
          <span className="font-medium">{machineName}</span>.
        </p>
      </div>
      <form
        className="w-full max-w-xs"
        onSubmit={(e) => {
          void submit(e)
        }}
      >
        <FieldGroup>
          <Field data-invalid={Boolean(form.formState.errors.phone)}>
            <FieldLabel htmlFor="phone">Phone number</FieldLabel>
            <Input
              id="phone"
              type="tel"
              placeholder="+919800000010"
              className="tap-target"
              {...form.register('phone')}
            />
            {form.formState.errors.phone && (
              <FieldError>{form.formState.errors.phone.message}</FieldError>
            )}
          </Field>
          {login.isError && (
            <FieldError>{getApiErrorMessage(login.error, 'Could not sign in')}</FieldError>
          )}
          <Button type="submit" size="lg" className="tap-target w-full" disabled={login.isPending}>
            {login.isPending ? 'Signing in…' : 'Continue'}
          </Button>
        </FieldGroup>
      </form>
    </div>
  )
}

function MachineHub({ machine }: { machine: QrResolveOut }) {
  const [view, setView] = useState<View>('menu')

  if (view === 'menu') {
    return (
      <div className="flex flex-col gap-4">
        <Card>
          <CardContent className="flex items-start justify-between gap-2 pt-6">
            <div>
              <div className="text-muted-foreground text-xs uppercase tracking-wide">Machine</div>
              <h1 className="text-lg font-semibold">{machine.machine_name}</h1>
              <p className="text-muted-foreground text-sm">
                {machine.plant_name}
                {machine.line_name ? ` · ${machine.line_name}` : ''}
              </p>
            </div>
            <Badge variant="outline" className="capitalize">
              {machine.machine_status}
            </Badge>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-3">
          <MenuOption
            icon={Sparkles}
            title="Ask me"
            subtitle="Get help troubleshooting this machine"
            onClick={() => setView('ask')}
          />
          <MenuOption
            icon={Activity}
            title="Machine Health"
            subtitle="See live status and readings"
            onClick={() => setView('health')}
          />
          <MenuOption
            icon={Wrench}
            title="Report an Issue"
            subtitle="Raise a ticket for a technician"
            onClick={() => setView('report')}
          />
        </div>
      </div>
    )
  }

  const titles: Record<Exclude<View, 'menu'>, string> = {
    ask: 'Ask me',
    health: 'Machine Health',
    report: 'Report an Issue',
  }

  return (
    <div className="flex flex-1 flex-col gap-3">
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          className="tap-target -ml-2"
          onClick={() => setView('menu')}
        >
          <ChevronLeft className="size-4" /> Back
        </Button>
        <span className="text-muted-foreground truncate text-sm">{machine.machine_name}</span>
      </div>
      <h1 className="text-lg font-semibold">{titles[view]}</h1>
      {view === 'ask' && <AskPanel machine={machine} />}
      {view === 'health' && <HealthPanel machine={machine} />}
      {view === 'report' && <ReportPanel machine={machine} />}
    </div>
  )
}

function MenuOption({
  icon: Icon,
  title,
  subtitle,
  onClick,
}: {
  icon: typeof Sparkles
  title: string
  subtitle: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="border-border bg-card hover:border-primary/40 tap-target flex items-center gap-3 rounded-xl border p-4 text-left transition-colors"
    >
      <div className="bg-primary/10 text-primary flex size-11 shrink-0 items-center justify-center rounded-xl">
        <Icon className="size-5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="font-semibold">{title}</div>
        <div className="text-muted-foreground text-sm">{subtitle}</div>
      </div>
      <ChevronRight className="text-muted-foreground size-5 shrink-0" />
    </button>
  )
}

// ---- Machine Health ---------------------------------------------------------

function HealthPanel({ machine }: { machine: QrResolveOut }) {
  const { data: health, isLoading } = useQuery({
    queryKey: ['health', 'machines', machine.machine_id],
    queryFn: () => getMachineHealth(machine.machine_id),
  })

  if (isLoading) return <SkeletonBlock className="h-40 w-full" />

  if (!health) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-muted-foreground text-sm">
            No health data has been reported for this machine yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  const rows = [
    { label: 'CPU', value: health.cpu_percent != null ? `${health.cpu_percent}%` : '—' },
    { label: 'Memory', value: health.memory_percent != null ? `${health.memory_percent}%` : '—' },
    { label: 'Disk', value: health.disk_percent != null ? `${health.disk_percent}%` : '—' },
    { label: 'Last heartbeat', value: relativeTime(health.last_heartbeat) },
  ]

  return (
    <div className="flex flex-col gap-3">
      <Card>
        <CardContent className="flex flex-col gap-3 pt-6">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Current status</span>
            <Badge
              className={
                health.is_online
                  ? 'border-transparent bg-status-online/15 text-status-online'
                  : undefined
              }
              variant={health.is_online ? 'secondary' : 'outline'}
            >
              {health.is_online ? 'Online' : 'Offline'}
            </Badge>
          </div>
          {!health.is_online && (
            <div className="bg-status-degraded/10 text-status-degraded flex items-center gap-2 rounded-md p-2 text-sm">
              <AlertTriangle className="size-4 shrink-0" />
              This machine isn't reporting in — it may be powered off or disconnected.
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-col pt-2">
          {rows.map((r) => (
            <div
              key={r.label}
              className="flex items-center justify-between border-b py-3 text-sm last:border-0"
            >
              <span className="text-muted-foreground">{r.label}</span>
              <span className="font-medium">{r.value}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

// ---- Ask me (chat) -----------------------------------------------------------

function AskPanel({ machine }: { machine: QrResolveOut }) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ApiChatMessage[]>([])
  const [input, setInput] = useState('')

  const startSession = useMutation({
    mutationFn: () => createChatSession(machine.machine_id),
    onSuccess: (session) => setSessionId(session.id),
  })
  const send = useMutation({
    mutationFn: (content: string) => sendChatMessage(sessionId!, content),
    onSuccess: (newMessages) => setMessages((m) => [...m, ...newMessages]),
  })

  useEffect(() => {
    if (!sessionId && !startSession.isPending) startSession.mutate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSend = () => {
    const text = input.trim()
    if (!text || !sessionId || send.isPending) return
    setInput('')
    send.mutate(text)
  }

  return (
    <div className="flex flex-1 flex-col gap-3">
      <div className="flex flex-1 flex-col gap-2">
        {messages.length === 0 && !send.isPending && (
          <div className="bg-muted mr-auto max-w-[85%] rounded-2xl rounded-bl-sm px-3 py-2 text-sm">
            Hi! I can help with {machine.machine_name}. Describe the problem and I'll suggest what
            to try.
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={
              m.role === 'user'
                ? 'bg-primary text-primary-foreground ml-auto max-w-[85%] rounded-2xl rounded-br-sm px-3 py-2 text-sm'
                : 'bg-muted mr-auto max-w-[85%] rounded-2xl rounded-bl-sm px-3 py-2 text-sm'
            }
          >
            {m.content}
          </div>
        ))}
        {send.isPending && (
          <div className="bg-muted text-muted-foreground mr-auto rounded-2xl px-3 py-2 text-sm">
            Typing…
          </div>
        )}
      </div>

      <form
        className="flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          handleSend()
        }}
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your question…"
          className="tap-target"
          disabled={!sessionId}
        />
        <Button
          type="submit"
          size="lg"
          className="tap-target"
          disabled={!input.trim() || !sessionId || send.isPending}
        >
          Send
        </Button>
      </form>
    </div>
  )
}

// ---- Report an Issue --------------------------------------------------------

const reportSchema = z.object({
  title: z.string().min(4, 'Please describe the problem'),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
})
type ReportValues = z.infer<typeof reportSchema>

function ReportPanel({ machine }: { machine: QrResolveOut }) {
  const form = useForm<ReportValues>({
    resolver: zodResolver(reportSchema),
    defaultValues: { title: '', priority: 'high' },
  })

  const report = useMutation({
    mutationFn: (values: ReportValues) =>
      createTicket({
        machine_id: machine.machine_id,
        title: values.title,
        priority: values.priority,
        category: 'other',
      }),
  })

  if (report.isSuccess) {
    const ticket = report.data
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
        <div className="bg-status-online/10 text-status-online flex size-14 items-center justify-center rounded-full">
          <CheckCircle2 className="size-7" />
        </div>
        <h2 className="text-lg font-semibold">Issue reported</h2>
        <p className="text-muted-foreground text-sm">
          A support engineer has been notified about{' '}
          <span className="font-medium">{machine.machine_name}</span>.
        </p>
        <code className="bg-muted rounded px-2 py-1 text-xs">{ticket.ticket_number}</code>
        <Button
          variant="outline"
          className="tap-target mt-2"
          onClick={() => {
            form.reset()
            report.reset()
          }}
        >
          Report another issue
        </Button>
      </div>
    )
  }

  const submit = form.handleSubmit((values) => report.mutate(values))

  return (
    <form
      onSubmit={(e) => {
        void submit(e)
      }}
    >
      <FieldGroup>
        <Field data-invalid={Boolean(form.formState.errors.title)}>
          <FieldLabel htmlFor="title">What's the problem?</FieldLabel>
          <Textarea
            id="title"
            rows={3}
            placeholder="e.g. Camera feed is frozen and parts aren't being scanned"
            aria-invalid={Boolean(form.formState.errors.title)}
            {...form.register('title')}
          />
          {form.formState.errors.title && (
            <FieldError>{form.formState.errors.title.message}</FieldError>
          )}
        </Field>

        <Field>
          <FieldLabel htmlFor="priority">How urgent is it?</FieldLabel>
          <Select
            value={form.watch('priority')}
            onValueChange={(v) =>
              form.setValue('priority', v as ReportValues['priority'], { shouldValidate: true })
            }
          >
            <SelectTrigger id="priority" className="tap-target">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="low">Low — minor / cosmetic</SelectItem>
              <SelectItem value="medium">Medium — affecting quality</SelectItem>
              <SelectItem value="high">High — line slowed down</SelectItem>
              <SelectItem value="critical">Critical — line stopped</SelectItem>
            </SelectContent>
          </Select>
        </Field>

        {report.isError && (
          <FieldError>{getApiErrorMessage(report.error, 'Could not report the issue')}</FieldError>
        )}

        <Button type="submit" size="lg" className="tap-target w-full" disabled={report.isPending}>
          Report issue
        </Button>
      </FieldGroup>
    </form>
  )
}
