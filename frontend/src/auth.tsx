import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from 'react'

import { api } from './lib/api'
import {
  AUTH_EXPIRED_EVENT,
  clearSessionToken,
  getSessionToken,
  persistSessionToken,
} from './lib/session'
import type { AdminProfile, LoginPayload, LoginResponse } from './types'

type AuthContextValue = {
  loading: boolean
  isAuthenticated: boolean
  profile: AdminProfile | null
  login: (payload: LoginPayload) => Promise<void>
  logout: () => void
  applySession: (payload: LoginResponse) => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: PropsWithChildren) {
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<AdminProfile | null>(null)

  async function loadProfile() {
    try {
      const nextProfile = await api.get<AdminProfile>('/auth/me')
      setProfile(nextProfile)
    } catch {
      clearSessionToken()
      setProfile(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const token = getSessionToken()
    if (!token) {
      setLoading(false)
      return
    }

    void loadProfile()
  }, [])

  useEffect(() => {
    function handleExpiredSession() {
      clearSessionToken()
      setProfile(null)
      setLoading(false)
    }

    window.addEventListener(AUTH_EXPIRED_EVENT, handleExpiredSession)
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleExpiredSession)
  }, [])

  async function applySession(payload: LoginResponse) {
    persistSessionToken(payload.access_token)
    setLoading(true)
    await loadProfile()
  }

  async function login(payload: LoginPayload) {
    const session = await api.post<LoginResponse>('/auth/login', payload, { auth: false })
    await applySession(session)
  }

  function logout() {
    clearSessionToken()
    setProfile(null)
  }

  const value = useMemo(
    () => ({
      loading,
      isAuthenticated: Boolean(profile),
      profile,
      login,
      logout,
      applySession,
    }),
    [loading, profile],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
