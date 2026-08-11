import { apiClient } from '@/lib/axios'
import type { AuthUser } from '@/features/auth/store/authStore'

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: AuthUser
}

export async function staffLogin(email: string, password: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', { email, password })
  return data
}

/** Phone-only login for the operator/QR-scan flow — self-registers on first use, no OTP. */
export async function phoneLogin(phone: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/login-phone', { phone })
  return data
}

export async function logout(refreshToken: string): Promise<void> {
  await apiClient.post('/auth/logout', { refresh_token: refreshToken })
}
