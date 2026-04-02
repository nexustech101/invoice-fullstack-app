import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'

import { api } from '../lib/api'
import type { Invoice, Payment, PaymentPayload } from '../types'
import { formatCurrency, formatDate, statusLabel } from '../utils/format'

const emptyPaymentForm: PaymentPayload = {
  invoice_id: 0,
  date: new Date().toISOString().slice(0, 10),
  amount: '',
  method: 'bank_transfer',
  transaction_id: '',
  notes: '',
}

export function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [form, setForm] = useState<PaymentPayload>(emptyPaymentForm)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadPageData() {
    try {
      setLoading(true)
      const [paymentData, invoiceData] = await Promise.all([
        api.get<Payment[]>('/payments'),
        api.get<Invoice[]>('/invoices'),
      ])
      setPayments(paymentData)
      setInvoices(invoiceData)
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load payments')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadPageData()
  }, [])

  const invoiceOptions = useMemo(
    () =>
      invoices.map((invoice) => ({
        id: invoice.id,
        label: `${invoice.invoice_number} · ${invoice.client?.name ?? 'Client'} · ${formatCurrency(
          invoice.total,
        )}`,
      })),
    [invoices],
  )

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      setSaving(true)
      await api.post<Payment>('/payments', {
        ...form,
        transaction_id: form.transaction_id || undefined,
        notes: form.notes || undefined,
      })
      setForm(emptyPaymentForm)
      await loadPageData()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to record payment')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(paymentId: number) {
    try {
      await api.delete(`/payments/${paymentId}`)
      await loadPageData()
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Unable to delete payment')
    }
  }

  return (
    <section className="page-stack">
      {error ? <div className="toast-banner error-message">{error}</div> : null}

      <div className="split-grid">
        <article className="page-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Record Payment</p>
              <h3>Apply money against an invoice</h3>
            </div>
          </div>
          <form className="form-grid" onSubmit={handleSubmit}>
            <label className="field-span-full">
              <span>Invoice</span>
              <select
                required
                value={form.invoice_id}
                onChange={(event) =>
                  setForm({ ...form, invoice_id: Number.parseInt(event.target.value, 10) || 0 })
                }
              >
                <option value={0}>Select an invoice</option>
                {invoiceOptions.map((invoice) => (
                  <option key={invoice.id} value={invoice.id}>
                    {invoice.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Date</span>
              <input
                required
                type="date"
                value={form.date}
                onChange={(event) => setForm({ ...form, date: event.target.value })}
              />
            </label>
            <label>
              <span>Amount</span>
              <input
                required
                type="number"
                min="0.01"
                step="0.01"
                value={form.amount}
                onChange={(event) => setForm({ ...form, amount: event.target.value })}
              />
            </label>
            <label>
              <span>Method</span>
              <select
                value={form.method}
                onChange={(event) => setForm({ ...form, method: event.target.value })}
              >
                <option value="bank_transfer">Bank transfer</option>
                <option value="stripe">Stripe</option>
                <option value="paypal">PayPal</option>
                <option value="cash">Cash</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label>
              <span>Transaction ID</span>
              <input
                value={form.transaction_id}
                onChange={(event) => setForm({ ...form, transaction_id: event.target.value })}
              />
            </label>
            <label className="field-span-full">
              <span>Notes</span>
              <textarea
                rows={3}
                value={form.notes}
                onChange={(event) => setForm({ ...form, notes: event.target.value })}
              />
            </label>
            <div className="form-actions field-span-full">
              <button
                className="ghost-button"
                type="button"
                onClick={() => setForm(emptyPaymentForm)}
              >
                Reset
              </button>
              <button className="primary-button" type="submit" disabled={saving || invoices.length === 0}>
                {saving ? 'Saving...' : 'Record payment'}
              </button>
            </div>
          </form>
        </article>

        <article className="page-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Payment History</p>
              <h3>{payments.length} payments</h3>
            </div>
          </div>
          {loading ? (
            <p>Loading payments...</p>
          ) : payments.length === 0 ? (
            <p className="empty-copy">Payments will appear here once you start collecting invoices.</p>
          ) : (
            <div className="table-shell">
              <table>
                <thead>
                  <tr>
                    <th>Invoice ID</th>
                    <th>Date</th>
                    <th>Method</th>
                    <th>Amount</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {payments.map((payment) => (
                    <tr key={payment.id}>
                      <td>#{payment.invoice_id}</td>
                      <td>{formatDate(payment.date)}</td>
                      <td>{statusLabel(payment.method)}</td>
                      <td>{formatCurrency(payment.amount)}</td>
                      <td>
                        <button
                          className="ghost-button danger-button"
                          type="button"
                          onClick={() => void handleDelete(payment.id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      </div>
    </section>
  )
}
