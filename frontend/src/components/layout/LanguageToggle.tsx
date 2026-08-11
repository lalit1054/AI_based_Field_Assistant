import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'

const LANGUAGES = [
  { code: 'en', label: 'EN' },
  { code: 'hi', label: 'हिंदी' },
] as const

export function LanguageToggle() {
  const { i18n, t } = useTranslation()

  return (
    <div role="group" aria-label={t('common.language')} className="border-border inline-flex rounded-lg border p-1">
      {LANGUAGES.map(({ code, label }) => (
        <Button
          key={code}
          type="button"
          size="sm"
          variant={i18n.resolvedLanguage === code ? 'default' : 'ghost'}
          className="tap-target px-3"
          aria-pressed={i18n.resolvedLanguage === code}
          onClick={() => void i18n.changeLanguage(code)}
        >
          {label}
        </Button>
      ))}
    </div>
  )
}
