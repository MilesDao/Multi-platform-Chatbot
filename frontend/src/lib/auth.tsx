import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { apiFetch, getToken, setToken } from './api'
import type { TokenResponse, User } from './types'

interface AuthValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  bootstrap: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) {
      setLoading(false)
      return
    }
    apiFetch<User>('/api/auth/me')
      .then(setUser)
      .catch(() => {
        setToken(null)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const authenticate = useCallback(async (path: string, email: string, password: string) => {
    const result = await apiFetch<TokenResponse>(path, {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    setToken(result.access_token)
    setUser(result.user)
  }, [])

  const value = useMemo<AuthValue>(
    () => ({
      user,
      loading,
      login: (email, password) => authenticate('/api/auth/login', email, password),
      bootstrap: (email, password) =>
        authenticate('/api/auth/bootstrap', email, password),
      logout: () => {
        setToken(null)
        setUser(null)
      },
    }),
    [user, loading, authenticate],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (value === null) throw new Error('useAuth must be used inside an AuthProvider')
  return value
}
