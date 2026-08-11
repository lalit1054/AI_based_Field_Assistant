import { apiClient } from '@/lib/axios'
import type { components } from '@/types/api'

export type ChatSession = components['schemas']['ChatSessionOut']
export type ChatMessage = components['schemas']['ChatMessageOut']

export async function createChatSession(machineId: string): Promise<ChatSession> {
  const { data } = await apiClient.post<ChatSession>('/chat/sessions', { machine_id: machineId })
  return data
}

export async function sendChatMessage(sessionId: string, content: string): Promise<ChatMessage[]> {
  const { data } = await apiClient.post<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`, {
    content,
  })
  return data
}
