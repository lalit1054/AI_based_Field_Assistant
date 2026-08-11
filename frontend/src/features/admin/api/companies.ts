import { apiClient } from '@/lib/axios'
import type { components } from '@/types/api'

export type Company = components['schemas']['CompanyOut']
export type CompanyIn = components['schemas']['CompanyIn']

export async function listCompanies(): Promise<Company[]> {
  const { data } = await apiClient.get<Company[]>('/admin/companies')
  return data
}

export async function createCompany(input: CompanyIn): Promise<Company> {
  const { data } = await apiClient.post<Company>('/admin/companies', input)
  return data
}
