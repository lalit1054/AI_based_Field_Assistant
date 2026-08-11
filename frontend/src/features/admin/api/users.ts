import { apiClient } from '@/lib/axios'
import type { components } from '@/types/api'
import type { Plant } from '@/features/admin/api/plants'

export type AdminUser = components['schemas']['app__schemas__admin__UserOut']
export type UserCreateIn = components['schemas']['UserCreateIn']
export type UserUpdateIn = components['schemas']['UserUpdateIn']

export async function listUsers(): Promise<AdminUser[]> {
  const { data } = await apiClient.get<AdminUser[]>('/admin/users')
  return data
}

export async function createUser(input: UserCreateIn): Promise<AdminUser> {
  const { data } = await apiClient.post<AdminUser>('/admin/users', input)
  return data
}

export async function updateUser(userId: string, input: UserUpdateIn): Promise<AdminUser> {
  const { data } = await apiClient.patch<AdminUser>(`/admin/users/${userId}`, input)
  return data
}

export async function listUserPlantAccess(userId: string): Promise<Plant[]> {
  const { data } = await apiClient.get<Plant[]>(`/admin/users/${userId}/plant-access`)
  return data
}

export async function grantPlantAccess(userId: string, plantId: string): Promise<void> {
  await apiClient.post(`/admin/users/${userId}/plant-access`, { plant_id: plantId })
}

export async function revokePlantAccess(userId: string, plantId: string): Promise<void> {
  await apiClient.delete(`/admin/users/${userId}/plant-access/${plantId}`)
}
