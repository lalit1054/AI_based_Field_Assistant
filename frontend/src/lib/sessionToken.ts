const REFRESH_TOKEN_KEY = 'refresh_token'

/**
 * Single choke point for the refresh token. It lives in sessionStorage —
 * not memory (would break reload) and not localStorage (persists past the
 * tab, unlike the access token which is deliberately never persisted).
 */
export const sessionToken = {
  get(): string | null {
    return sessionStorage.getItem(REFRESH_TOKEN_KEY)
  },
  set(token: string): void {
    sessionStorage.setItem(REFRESH_TOKEN_KEY, token)
  },
  clear(): void {
    sessionStorage.removeItem(REFRESH_TOKEN_KEY)
  },
}
