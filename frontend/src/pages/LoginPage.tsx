import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth'
import { useTheme } from '../theme'

export function LoginPage() {
  const { loading, isAuthenticated, login } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const redirectPath =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? '/'

  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      setSubmitting(true)
      setError(null)
      await login({ username, password })
      navigate(redirectPath, { replace: true })
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : 'Unable to sign in')
    } finally {
      setSubmitting(false)
    }
  }

  if (!loading && isAuthenticated) {
    return <Navigate to={redirectPath} replace />
  }

  return (
    <section className="auth-shell">
      <div className="auth-topbar">
        <div className="public-brand">Northstar Ledger</div>
        <button className="icon-button" type="button" onClick={toggleTheme}>
          {theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </button>
      </div>

      <div className="auth-layout">
        <article className="auth-card auth-card-feature">
          <p className="eyebrow">Secure dashboard</p>
          <h1>Admin sign in</h1>
          <p className="auth-copy">
            Public invoice pages stay accessible for clients, but the dashboard now
            requires authentication before anyone can view invoices, clients, payments,
            or business data.
          </p>
          <div className="auth-feature-list">
            <div className="auth-feature-item">
              <strong>Default access</strong>
              <span>Username `admin` and password `admin`.</span>
            </div>
            <div className="auth-feature-item">
              <strong>Rotate immediately</strong>
              <span>Change credentials from the new Settings area after sign-in.</span>
            </div>
            <div className="auth-feature-item">
              <strong>Protected admin API</strong>
              <span>All dashboard routes now require a valid bearer session.</span>
            </div>
          </div>
        </article>

        <article className="auth-card">
          <div className="panel-header auth-panel-header">
            <div>
              <p className="eyebrow">Welcome back</p>
              <h3>Sign in to continue</h3>
            </div>
          </div>

          <form className="form-grid" onSubmit={handleSubmit}>
            <label className="field-span-full">
              <span>Username</span>
              <input
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </label>
            <label className="field-span-full">
              <span>Password</span>
              <input
                autoComplete="current-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            {error ? <div className="toast-banner error-message field-span-full">{error}</div> : null}
            <div className="form-actions field-span-full">
              <button className="primary-button auth-submit" type="submit" disabled={submitting}>
                {submitting ? 'Signing in...' : 'Sign in'}
              </button>
            </div>
          </form>
        </article>
      </div>
    </section>
  )
}
