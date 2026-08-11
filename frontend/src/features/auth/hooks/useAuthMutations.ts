import { useMutation } from '@tanstack/react-query'
import {
  staffLogin,
  phoneLogin,
  logout as apiLogout,
  type TokenResponse,
} from '@/features/auth/api/auth'
import { useAuthStore } from '@/features/auth/store/authStore'
import { sessionToken } from '@/lib/sessionToken'

function applySession(session: TokenResponse) {
  sessionToken.set(session.refresh_token)
  useAuthStore.getState().setSession(session.access_token, session.user)
}

/** Email + password sign-in (admin & staff roles). */
export function useStaffLogin() {
  return useMutation({
    mutationFn: (payload: { email: string; password: string }) =>
      staffLogin(payload.email, payload.password),
    onSuccess: applySession,
  })
}

/** Phone-only sign-in for the operator/QR-scan flow (no password, no OTP). */
export function usePhoneLogin() {
  return useMutation({
    mutationFn: (phone: string) => phoneLogin(phone),
    onSuccess: applySession,
  })
}

export function useLogout() {
  return useMutation({
    mutationFn: async () => {
      const token = sessionToken.get()
      if (token) await apiLogout(token)
    },
    onSettled: () => {
      sessionToken.clear()
      useAuthStore.getState().clear()
    },
  })
}
