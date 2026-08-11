import axios, { type AxiosError } from 'axios'
import { useAuthStore, type AuthUser } from '@/features/auth/store/authStore'
import { sessionToken } from '@/lib/sessionToken'

declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    _retry?: boolean
  }
}

export const apiClient = axios.create({
  baseURL: '/api',
})

apiClient.interceptors.request.use((config) => {
  const { accessToken } = useAuthStore.getState()
  if (accessToken) {
    config.headers.set('Authorization', `Bearer ${accessToken}`)
  }
  return config
})

interface RefreshResponse {
  access_token: string
  refresh_token: string
  user: AuthUser
}

let refreshPromise: Promise<RefreshResponse | null> | null = null

/**
 * The refresh token isn't an httpOnly cookie — the backend expects it in
 * the request body and rotates it (revokes the old one) on every call, so
 * the new one must be persisted immediately or the *next* refresh fails.
 */
async function refreshAccessToken(): Promise<RefreshResponse | null> {
  const currentRefreshToken = sessionToken.get()
  if (!currentRefreshToken) return null

  refreshPromise ??= axios
    .post<RefreshResponse>('/api/auth/refresh', { refresh_token: currentRefreshToken })
    .then((res) => res.data)
    .catch(() => null)
    .finally(() => {
      refreshPromise = null
    })

  const refreshed = await refreshPromise
  if (refreshed) {
    sessionToken.set(refreshed.refresh_token)
  }
  return refreshed
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config
    const isAuthEndpoint = originalRequest?.url?.includes('/auth/')

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true
      const refreshed = await refreshAccessToken()
      if (refreshed) {
        useAuthStore.getState().setAccessToken(refreshed.access_token)
        originalRequest.headers.set('Authorization', `Bearer ${refreshed.access_token}`)
        return apiClient(originalRequest)
      }
      sessionToken.clear()
      useAuthStore.getState().clear()
    }

    return Promise.reject(error)
  },
)

export { refreshAccessToken }
