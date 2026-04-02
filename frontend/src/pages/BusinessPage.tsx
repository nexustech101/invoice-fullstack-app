import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import { api } from '../lib/api'
import type { Business } from '../types'

type BusinessForm = {
  name: string
  email: string
  phone: string
  address_line1: string
  address_line2: string
  city_state_zip: string
  tax_id: string
  logo_url: string
  bank_name: string
  account_number: string
  bsb: string
  payment_terms: string
}

function toFormState(business: Business): BusinessForm {
  return {
    name: business.name,
    email: business.email,
    phone: business.phone ?? '',
    address_line1: business.address_line1,
    address_line2: business.address_line2 ?? '',
    city_state_zip: business.city_state_zip,
    tax_id: business.tax_id ?? '',
    logo_url: business.logo_url ?? '',
    bank_name: business.bank_name,
    account_number: business.account_number,
    bsb: business.bsb ?? '',
    payment_terms: business.payment_terms,
  }
}

export function BusinessPage() {
  const [business, setBusiness] = useState<Business | null>(null)
  const [form, setForm] = useState<BusinessForm | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadBusiness() {
    try {
      setLoading(true)
      const data = await api.get<Business>('/business')
      setBusiness(data)
      setForm(toFormState(data))
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load business')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadBusiness()
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!form) return

    try {
      setSaving(true)
      const updated = await api.put<Business>('/business', {
        ...form,
        phone: form.phone || undefined,
        address_line2: form.address_line2 || undefined,
        tax_id: form.tax_id || undefined,
        logo_url: form.logo_url || undefined,
        bsb: form.bsb || undefined,
      })
      setBusiness(updated)
      setForm(toFormState(updated))
      setError(null)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to update business')
    } finally {
      setSaving(false)
    }
  }

  if (loading || !form || !business) {
    return <section className="page-panel">Loading business profile...</section>
  }

  return (
    <section className="page-stack">
      {error ? <div className="toast-banner error-message">{error}</div> : null}

      <div className="split-grid">
        <article className="page-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Business Profile</p>
              <h3>Sender identity for invoices and receipts</h3>
            </div>
          </div>
          <form className="form-grid" onSubmit={handleSubmit}>
            <label>
              <span>Business name</span>
              <input
                required
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </label>
            <label>
              <span>Email</span>
              <input
                required
                type="email"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
              />
            </label>
            <label>
              <span>Phone</span>
              <input
                value={form.phone}
                onChange={(event) => setForm({ ...form, phone: event.target.value })}
              />
            </label>
            <label>
              <span>Tax ID</span>
              <input
                value={form.tax_id}
                onChange={(event) => setForm({ ...form, tax_id: event.target.value })}
              />
            </label>
            <label className="field-span-full">
              <span>Address line 1</span>
              <input
                required
                value={form.address_line1}
                onChange={(event) => setForm({ ...form, address_line1: event.target.value })}
              />
            </label>
            <label className="field-span-full">
              <span>Address line 2</span>
              <input
                value={form.address_line2}
                onChange={(event) => setForm({ ...form, address_line2: event.target.value })}
              />
            </label>
            <label className="field-span-full">
              <span>City / State / ZIP</span>
              <input
                required
                value={form.city_state_zip}
                onChange={(event) => setForm({ ...form, city_state_zip: event.target.value })}
              />
            </label>
            <label>
              <span>Bank name</span>
              <input
                required
                value={form.bank_name}
                onChange={(event) => setForm({ ...form, bank_name: event.target.value })}
              />
            </label>
            <label>
              <span>Account number</span>
              <input
                required
                value={form.account_number}
                onChange={(event) => setForm({ ...form, account_number: event.target.value })}
              />
            </label>
            <label>
              <span>BSB / routing</span>
              <input
                value={form.bsb}
                onChange={(event) => setForm({ ...form, bsb: event.target.value })}
              />
            </label>
            <label>
              <span>Payment terms</span>
              <input
                required
                value={form.payment_terms}
                onChange={(event) => setForm({ ...form, payment_terms: event.target.value })}
              />
            </label>
            <label className="field-span-full">
              <span>Logo URL</span>
              <input
                value={form.logo_url}
                onChange={(event) => setForm({ ...form, logo_url: event.target.value })}
              />
            </label>
            <div className="form-actions field-span-full">
              <button className="primary-button" type="submit" disabled={saving}>
                {saving ? 'Saving...' : 'Save business profile'}
              </button>
            </div>
          </form>
        </article>

        <article className="page-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Profile Preview</p>
              <h3>{business.name}</h3>
            </div>
          </div>
          <div className="profile-card">
            <div>
              <p className="eyebrow">Invoice sender</p>
              <strong>{business.email}</strong>
            </div>
            <div>
              <p className="eyebrow">Address</p>
              <strong>{business.address_line1}</strong>
              <p>{business.address_line2}</p>
              <p>{business.city_state_zip}</p>
            </div>
            <div>
              <p className="eyebrow">Settlement details</p>
              <strong>{business.bank_name}</strong>
              <p>{business.account_number}</p>
              <p>{business.bsb}</p>
            </div>
            <div>
              <p className="eyebrow">Online payments</p>
              <strong>{business.stripe_enabled ? 'Stripe Checkout enabled' : 'Stripe not configured yet'}</strong>
              <p>
                {business.stripe_webhook_ready
                  ? 'Webhook reconciliation is ready.'
                  : 'Add STRIPE_WEBHOOK_SECRET to auto-mark paid invoices from Stripe.'}
              </p>
              <p>
                {business.paypal_url
                  ? `PayPal link: ${business.paypal_url}`
                  : 'Optional PayPal button can be enabled with PAYPAL_URL.'}
              </p>
            </div>
          </div>
        </article>
      </div>
    </section>
  )
}
