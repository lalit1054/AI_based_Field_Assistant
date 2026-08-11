import { create } from 'zustand'

/** Mirrors the backend's UserRole enum (app/db/enums.py). */
export type UserRole =
  | 'operator'
  | 'field_tech'
  | 'support_l2'
  | 'support_l3'
  | 'plant_manager'
  | 'admin'
  | 'company_viewer'

export interface AuthUser {
  id: string
  full_name: string
  phone: string | null
  email: string | null
  role: UserRole
}

interface AuthState {
  accessToken: string | null
  user: AuthUser | null
  /** true while the silent refresh-on-load check is in flight */
  isBootstrapping: boolean
  setSession: (accessToken: string, user: AuthUser) => void
  setAccessToken: (accessToken: string) => void
  setBootstrapped: () => void
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  isBootstrapping: true,
  setSession: (accessToken, user) => set({ accessToken, user, isBootstrapping: false }),
  setAccessToken: (accessToken) => set({ accessToken }),
  setBootstrapped: () => set({ isBootstrapping: false }),
  clear: () => set({ accessToken: null, user: null, isBootstrapping: false }),
}))
