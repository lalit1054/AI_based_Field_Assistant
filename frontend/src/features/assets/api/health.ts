import { apiClient } from '@/lib/axios'
import type { components } from '@/types/api'

export type MachineHealth = components['schemas']['MachineHealthOut']

export async function listMachineHealth(plantId?: string): Promise<MachineHealth[]> {
  const { data } = await apiClient.get<MachineHealth[]>('/health/machines', {
    params: plantId ? { plant_id: plantId } : undefined,
  })
  return data
}

export async function getMachineHealth(machineId: string): Promise<MachineHealth | null> {
  try {
    const { data } = await apiClient.get<MachineHealth>(`/health/machines/${machineId}`)
    return data
  } catch {
    return null
  }
}
