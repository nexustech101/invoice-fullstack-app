import { useEffect, useState, type FormEvent } from 'react'

import { useAuth } from '../auth'
import { api } from '../lib/api'
import type { LoginResponse } from '../types'

type SettingsForm = {
  current_password: string
  new_username: string
  new_password: string
  confirm_password: string
}

export function SettingsPage() {
  const { profile, applySession } = useAuth()
  const [form, setForm] = useState<SettingsForm>({
    current_password: '',
    new_username: profile?.username ?? 'admin',
    new_password: '',
    confirm_password: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    setForm((current) => ({
      ...current,
      new_username: profile?.username ?? current.new_username,
    }))
  }, [profile?.username])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSuccess(null)

    if (form.new_password !== form.confirm_password) {
      setError('The new password and confirmation do not match.')
      return
    }

    try {
      setSaving(true)
      const response = await api.post<LoginResponse>('/auth/change-credentials', {
        current_password: form.current_password,
        new_username: form.new_username,
        new_password: form.new_password,
      })
      await applySession(response)
      setForm((current) => ({
        ...current,
        current_password: '',
        new_password: '',
        confirm_password: '',
      }))
      setSuccess('Credentials updated. Your session has been rotated to the new login.')
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to update credentials')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="page-stack">
      {error ? <div className="toast-banner error-message">{error}</div> : null}
      {success ? <div className="toast-banner success-message">{success}</div> : null}

      <div className="split-grid settings-grid">
        <article className="page-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Access control</p>
              <h3>Admin credentials</h3>
            </div>
          </div>
          <form className="form-grid" onSubmit={handleSubmit}>
            <label className="field-span-full">
              <span>Current username</span>
              <input value={profile?.username ?? ''} disabled />
            </label>
            <label className="field-span-full">
              <span>Current password</span>
              <input
                autoComplete="current-password"
                required
                type="password"
                value={form.current_password}
                onChange={(event) =>
                  setForm({ ...form, current_password: event.target.value })
                }
              />
            </label>
            <label>
              <span>New username</span>
              <input
                autoComplete="username"
                minLength={3}
                required
                value={form.new_username}
                onChange={(event) => setForm({ ...form, new_username: event.target.value })}
              />
            </label>
            <label>
              <span>New password</span>
              <input
                autoComplete="new-password"
                minLength={4}
                required
                type="password"
                value={form.new_password}
                onChange={(event) => setForm({ ...form, new_password: event.target.value })}
              />
            </label>
            <label className="field-span-full">
              <span>Confirm new password</span>
              <input
                autoComplete="new-password"
                minLength={4}
                required
                type="password"
                value={form.confirm_password}
                onChange={(event) =>
                  setForm({ ...form, confirm_password: event.target.value })
                }
              />
            </label>
            <div className="form-actions field-span-full">
              <button className="primary-button" type="submit" disabled={saving}>
                {saving ? 'Updating credentials...' : 'Save credentials'}
              </button>
            </div>
          </form>
        </article>

        <article className="page-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Security notes</p>
              <h3>Recommended next steps</h3>
            </div>
          </div>
          <div className="profile-card settings-card">
            <div>
              <p className="eyebrow">Default credentials</p>
              <strong>Change `admin / admin` before sharing the dashboard publicly.</strong>
            </div>
            <div>
              <p className="eyebrow">Session rotation</p>
              <strong>Saving new credentials invalidates older tokens automatically.</strong>
            </div>
            <div>
              <p className="eyebrow">Public invoice pages</p>
              <strong>Client payment links remain public and are not affected by admin sign-in.</strong>
            </div>
          </div>
        </article>
      </div>
    </section>
  )
}
