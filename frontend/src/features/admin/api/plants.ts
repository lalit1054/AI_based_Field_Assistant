import { apiClient } from '@/lib/axios'
import type { components } from '@/types/api'

export type Plant = components['schemas']['PlantOut']
export type PlantIn = components['schemas']['PlantIn']
export type PlantUpdate = components['schemas']['PlantUpdate']

export async function listPlants(): Promise<Plant[]> {
  const { data } = await apiClient.get<Plant[]>('/admin/plants')
  return data
}

export async function createPlant(input: PlantIn): Promise<Plant> {
  const { data } = await apiClient.post<Plant>('/admin/plants', input)
  return data
}

export async function updatePlant(plantId: string, input: PlantUpdate): Promise<Plant> {
  const { data } = await apiClient.patch<Plant>(`/admin/plants/${plantId}`, input)
  return data
}
