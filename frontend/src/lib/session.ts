export const SESSION_TOKEN_KEY = 'invoice-admin-token'
export const AUTH_EXPIRED_EVENT = 'invoice-auth-expired'

export function getSessionToken(): string | null {
  if (typeof window === 'undefined') {
    return null
  }

  return window.localStorage.getItem(SESSION_TOKEN_KEY)
}

export function persistSessionToken(token: string) {
  window.localStorage.setItem(SESSION_TOKEN_KEY, token)
}

export function clearSessionToken() {
  window.localStorage.removeItem(SESSION_TOKEN_KEY)
}
