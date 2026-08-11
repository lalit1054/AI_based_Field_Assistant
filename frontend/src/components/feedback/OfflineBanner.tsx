import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { WifiOff } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

export function OfflineBanner() {
  const { t } = useTranslation()
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  useEffect(() => {
    const setOnline = () => setIsOnline(true)
    const setOffline = () => setIsOnline(false)
    window.addEventListener('online', setOnline)
    window.addEventListener('offline', setOffline)
    return () => {
      window.removeEventListener('online', setOnline)
      window.removeEventListener('offline', setOffline)
    }
  }, [])

  if (isOnline) return null

  return (
    <Alert
      role="status"
      className="border-status-degraded bg-status-degraded/10 rounded-none border-x-0 border-t-0"
    >
      <WifiOff className="size-4" />
      <AlertDescription>{t('common.offlineBanner')}</AlertDescription>
    </Alert>
  )
}
