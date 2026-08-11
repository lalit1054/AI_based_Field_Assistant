import { apiClient } from '@/lib/axios'
import type { components } from '@/types/api'

export type QrResolveOut = components['schemas']['QrResolveOut']

export type ResolveResult = { machine: QrResolveOut } | { error: 'not_found' | 'revoked' }

export async function resolveQrToken(token: string): Promise<ResolveResult> {
  try {
    const { data } = await apiClient.get<QrResolveOut>(`/a/${token}`)
    return { machine: data }
  } catch {
    // The backend doesn't distinguish "never existed" from "revoked" in the
    // response body (both 404) — treat any failure as not_found.
    return { error: 'not_found' }
  }
}
