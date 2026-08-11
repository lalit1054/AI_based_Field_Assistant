import { apiClient } from '@/lib/axios'
import type { components } from '@/types/api'

export type DashboardStats = components['schemas']['DashboardStatsOut']

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await apiClient.get<DashboardStats>('/dashboard/stats')
  return data
}
