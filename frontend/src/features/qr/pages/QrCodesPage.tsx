import { useRef } from 'react'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { QRCodeSVG, QRCodeCanvas } from 'qrcode.react'
import { toast } from 'sonner'
import { QrCode, Copy, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { useScopedPlants } from '@/features/auth/hooks/useScopedPlants'
import { listMachines, type Machine } from '@/features/assets/api/machines'
import { listQrTokens, issueQrToken, qrTokenUrl, type QrToken } from '@/features/qr/api/qr'
import { getApiErrorMessage } from '@/lib/apiError'

/** Green "Active" pill (shared look with the online status colour). */
const ACTIVE_BADGE = 'border-transparent bg-status-online/15 text-status-online'

export function QrCodesPage() {
  const { plants } = useScopedPlants()
  const { data: machines = [] } = useQuery({
    queryKey: ['assets', 'machines'],
    queryFn: () => listMachines(),
  })

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold">QR Codes</h1>
        <p className="text-muted-foreground text-sm">
          Generate a QR sticker for each machine and download it to print. Operators scan it to
          report an issue.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {machines.map((machine) => (
          <QrCard
            key={machine.id}
            machine={machine}
            plantName={plants.find((p) => p.id === machine.plant_id)?.name ?? '—'}
          />
        ))}
      </div>
    </div>
  )
}

function QrCard({ machine, plantName }: { machine: Machine; plantName: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const queryClient = useQueryClient()

  const { data: tokens = [] } = useQuery({
    queryKey: ['qr', 'tokens', machine.id],
    queryFn: () => listQrTokens(machine.id),
  })
  const token: QrToken | undefined = tokens.find((t) => t.is_active)

  const generate = useMutation({
    mutationFn: () => issueQrToken(machine.id),
    onSuccess: () => {
      toast.success(`QR generated for ${machine.name}`)
      void queryClient.invalidateQueries({ queryKey: ['qr', 'tokens', machine.id] })
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Could not generate QR code')),
  })

  const handleDownload = () => {
    const src = canvasRef.current
    if (!src) return
    // Normalise to exactly 640×640 on a white background.
    const out = document.createElement('canvas')
    out.width = 640
    out.height = 640
    const ctx = out.getContext('2d')
    if (!ctx) return
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, 640, 640)
    ctx.drawImage(src, 0, 0, 640, 640)
    const link = document.createElement('a')
    link.href = out.toDataURL('image/png')
    link.download = `${machine.name.replace(/\s+/g, '-').toLowerCase()}-qr.png`
    link.click()
    toast.success('QR downloaded (640×640 PNG)')
  }

  const url = token ? qrTokenUrl(token.token) : ''

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 pt-6 text-center">
        <div className="flex w-full items-start justify-between text-left">
          <div>
            <div className="font-medium">{machine.name}</div>
            <div className="text-muted-foreground text-xs">{plantName}</div>
          </div>
          {token ? (
            <Badge className={ACTIVE_BADGE} variant="secondary">
              Active
            </Badge>
          ) : (
            <Badge variant="outline">None</Badge>
          )}
        </div>

        {token ? (
          <>
            <div className="rounded-lg bg-white p-3">
              <QRCodeSVG value={url} size={148} level="M" marginSize={0} />
            </div>
            {/* Hidden hi-res canvas used only as the source for the 640×640 download. */}
            <QRCodeCanvas
              ref={canvasRef}
              value={url}
              size={640}
              level="M"
              marginSize={4}
              className="hidden"
            />
            <code className="text-muted-foreground w-full truncate rounded bg-muted/50 px-2 py-1 text-xs">
              {url}
            </code>
            <div className="flex w-full gap-2">
              <Button variant="outline" size="sm" className="flex-1" onClick={handleDownload}>
                <Download className="size-4" />
                Download QR
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  void navigator.clipboard?.writeText(url)
                  toast.success('Link copied')
                }}
              >
                <Copy className="size-4" />
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="bg-muted text-muted-foreground flex size-40 flex-col items-center justify-center rounded-lg">
              <QrCode className="size-8" />
              <span className="mt-1 text-xs">Not generated</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
            >
              <QrCode className="size-4" />
              Generate
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}
