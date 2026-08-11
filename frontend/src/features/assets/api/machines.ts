import { apiClient } from '@/lib/axios'
import type { components } from '@/types/api'

export type Machine = components['schemas']['MachineOut']
export type MachineIn = components['schemas']['MachineIn']
export type MachineUpdate = components['schemas']['MachineUpdate']

export async function listMachines(plantId?: string): Promise<Machine[]> {
  const { data } = await apiClient.get<Machine[]>('/assets/machines', {
    params: plantId ? { plant_id: plantId } : undefined,
  })
  return data
}

export async function createMachine(input: MachineIn): Promise<Machine> {
  const { data } = await apiClient.post<Machine>('/assets/machines', input)
  return data
}

export async function updateMachine(machineId: string, input: MachineUpdate): Promise<Machine> {
  const { data } = await apiClient.patch<Machine>(`/assets/machines/${machineId}`, input)
  return data
}
