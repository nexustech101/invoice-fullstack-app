import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../auth'

export function ProtectedRoute() {
  const { loading, isAuthenticated } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <section className="auth-loading-shell">
        <div className="auth-card auth-card-compact">Checking your session...</div>
      </section>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}
