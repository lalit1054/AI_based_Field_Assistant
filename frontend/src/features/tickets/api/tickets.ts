import { apiClient } from '@/lib/axios'
import type { components } from '@/types/api'

export type Ticket = components['schemas']['TicketOut']
export type TicketIn = components['schemas']['TicketIn']
export type TicketUpdate = components['schemas']['TicketUpdate']

export interface ListTicketsParams {
  status?: components['schemas']['TicketStatus']
  plant_id?: string
  machine_id?: string
}

export async function listTickets(params: ListTicketsParams = {}): Promise<Ticket[]> {
  const { data } = await apiClient.get<Ticket[]>('/tickets', { params })
  return data
}

export async function createTicket(input: TicketIn): Promise<Ticket> {
  const { data } = await apiClient.post<Ticket>('/tickets', input)
  return data
}

export async function updateTicket(ticketId: string, input: TicketUpdate): Promise<Ticket> {
  const { data } = await apiClient.patch<Ticket>(`/tickets/${ticketId}`, input)
  return data
}
