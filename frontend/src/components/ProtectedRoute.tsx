import { Navigate, Outlet } from 'react-router-dom'

import { LoadingNote } from './ui/empty-state'
import { useAuth } from '../lib/auth'

export default function ProtectedRoute() {
  const { user, loading } = useAuth()

  if (loading) return <div className="p-8"><LoadingNote /></div>
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}
