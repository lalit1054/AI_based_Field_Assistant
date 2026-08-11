import { apiClient } from '@/lib/axios'
import type { components } from '@/types/api'

export type Line = components['schemas']['LineOut']
export type LineIn = components['schemas']['LineIn']

export async function listLines(plantId?: string): Promise<Line[]> {
  const { data } = await apiClient.get<Line[]>('/admin/lines', {
    params: plantId ? { plant_id: plantId } : undefined,
  })
  return data
}

export async function createLine(input: LineIn): Promise<Line> {
  const { data } = await apiClient.post<Line>('/admin/lines', input)
  return data
}
