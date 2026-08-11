import { apiClient } from '@/lib/axios'
import type { components } from '@/types/api'

export type KbDocument = components['schemas']['KbDocumentOut']

export async function listKbDocuments(): Promise<KbDocument[]> {
  const { data } = await apiClient.get<KbDocument[]>('/kb/documents')
  return data
}
