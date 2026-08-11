import { isAxiosError } from 'axios'

/** Backend error envelope: `{ error: "<slug>", detail: string | object }`. */
export function getApiErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}
