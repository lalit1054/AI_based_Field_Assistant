import { apiClient } from '@/lib/axios'
import type { components } from '@/types/api'

export type QrToken = components['schemas']['QrTokenOut']

export async function listQrTokens(machineId: string): Promise<QrToken[]> {
  const { data } = await apiClient.get<QrToken[]>(`/qr/machines/${machineId}/tokens`)
  return data
}

export async function issueQrToken(machineId: string): Promise<QrToken> {
  const { data } = await apiClient.post<QrToken>(`/qr/machines/${machineId}/tokens`)
  return data
}

export async function revokeQrToken(tokenId: string): Promise<void> {
  await apiClient.post(`/qr/tokens/${tokenId}/revoke`)
}

export function qrTokenUrl(token: string): string {
  return `${location.origin}/a/${token}`
}
