import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { api } from '../lib/api'
import { useTheme } from '../theme'
import type { Invoice, StripeCheckoutSessionResponse } from '../types'
import { formatCurrency, formatDate, statusLabel } from '../utils/format'

export function PublicInvoicePage() {
  const { invoiceId } = useParams()
  const [searchParams] = useSearchParams()
  const { theme, toggleTheme } = useTheme()
  const [invoice, setInvoice] = useState<Invoice | null>(null)
  const [loading, setLoading] = useState(true)
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function loadInvoice() {
      try {
        setLoading(true)
        const data = await api.get<Invoice>(`/public/invoices/${invoiceId}`, { auth: false })
        if (active) {
          setInvoice(data)
          setError(null)
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : 'Unable to load invoice')
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    if (invoiceId) {
      void loadInvoice()
    }

    return () => {
      active = false
    }
  }, [invoiceId])

  const checkoutState = searchParams.get('checkout')
  const checkoutMessage = useMemo(() => {
    if (!invoice || !checkoutState) return null
    if (checkoutState === 'cancelled') {
      return {
        tone: 'info-message',
        message: 'Stripe checkout was cancelled. You can return whenever you are ready to pay.',
      }
    }
    if (checkoutState === 'success') {
      return {
        tone: invoice.status === 'paid' || invoice.status === 'overdue_paid' ? 'success-message' : 'info-message',
        message:
          invoice.status === 'paid' || invoice.status === 'overdue_paid'
            ? 'Payment received. This invoice has been marked as paid.'
            : 'Payment submitted. This page will update once Stripe finishes confirmation.',
      }
    }
    return null
  }, [checkoutState, invoice])

  async function handleStripeCheckout() {
    if (!invoice) return
    try {
      setCheckoutLoading(true)
      const session = await api.post<StripeCheckoutSessionResponse>(
        `/public/invoices/${invoice.id}/stripe-checkout-session`,
        undefined,
        { auth: false },
      )
      window.location.href = session.url
    } catch (checkoutError) {
      setError(
        checkoutError instanceof Error
          ? checkoutError.message
          : 'Unable to start Stripe checkout',
      )
      setCheckoutLoading(false)
    }
  }

  if (loading) {
    return <section className="public-shell"><div className="public-card">Loading invoice...</div></section>
  }

  if (error || !invoice) {
    return (
      <section className="public-shell">
        <div className="public-card public-card-narrow error-message">
          {error ?? 'Invoice not found'}
        </div>
      </section>
    )
  }

  const amountDue = invoice.amount_due ?? invoice.total
  const isPaid = invoice.status === 'paid' || invoice.status === 'overdue_paid'

  return (
    <section className="public-shell">
      <div className="public-topbar">
        <Link className="public-brand" to="/">
          Northstar Ledger
        </Link>
        <button className="icon-button" type="button" onClick={toggleTheme}>
          {theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </button>
      </div>

      <article className="public-card">
        {checkoutMessage ? (
          <div className={`toast-banner ${checkoutMessage.tone}`}>{checkoutMessage.message}</div>
        ) : null}
        <div className="public-hero">
          <div>
            <p className="eyebrow">Invoice #{invoice.invoice_number}</p>
            <h1>Payment details for {invoice.client?.name ?? 'your invoice'}</h1>
            <p className="public-copy">
              Review the line items, due date, and transfer details below. This page
              is your secure payment hub with online and bank-transfer options.
            </p>
          </div>
          <div className="public-actions">
            <span className={`badge badge-${invoice.status}`}>{statusLabel(invoice.status)}</span>
            <button
              className="primary-button"
              type="button"
              onClick={() =>
                window.open(`${api.baseUrl}/public/invoices/${invoice.id}/pdf`, '_blank')
              }
            >
              Download PDF
            </button>
          </div>
        </div>

        <div className="public-grid">
          <section className="public-panel">
            <h2>Invoice summary</h2>
            <div className="summary-grid">
              <div>
                <span>Issued</span>
                <strong>{formatDate(invoice.invoice_date)}</strong>
              </div>
              <div>
                <span>Due date</span>
                <strong>{formatDate(invoice.due_date)}</strong>
              </div>
              <div>
                <span>Total</span>
                <strong>{formatCurrency(invoice.total)}</strong>
              </div>
              <div>
                <span>Amount due</span>
                <strong>{formatCurrency(amountDue)}</strong>
              </div>
            </div>

            <div className="table-shell">
              <table>
                <thead>
                  <tr>
                    <th>Description</th>
                    <th>Qty</th>
                    <th>Rate</th>
                    <th>Adjust</th>
                    <th>Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  {invoice.line_items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <strong>{item.description}</strong>
                        <div className="table-subcopy">{item.details}</div>
                      </td>
                      <td>{item.qty}</td>
                      <td>{formatCurrency(item.rate)}</td>
                      <td>{item.adjustment_pct}%</td>
                      <td>{formatCurrency(item.sub_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="public-panel">
            <h2>How to pay</h2>
            {invoice.business?.stripe_enabled ? (
              <div className="payment-card payment-card-highlight">
                <p className="eyebrow">Stripe Checkout</p>
                <strong>Secure online payment</strong>
                <p>
                  Pay the outstanding balance with Stripe-hosted checkout and supported
                  payment methods in {invoice.business.payment_currency}.
                </p>
                <div className="public-payment-actions">
                  <button
                    className="primary-button payment-cta"
                    type="button"
                    disabled={checkoutLoading || isPaid}
                    onClick={() => void handleStripeCheckout()}
                  >
                    {isPaid
                      ? 'Already paid'
                      : checkoutLoading
                        ? 'Redirecting...'
                        : 'Pay with Stripe'}
                  </button>
                  {!invoice.business?.stripe_webhook_ready ? (
                    <span className="payment-note">
                      Stripe is enabled, but automatic payment confirmation still needs the
                      webhook secret configured on the server.
                    </span>
                  ) : null}
                </div>
              </div>
            ) : null}
            {invoice.business?.paypal_url ? (
              <div className="payment-card">
                <p className="eyebrow">PayPal</p>
                <strong>Alternate online payment</strong>
                <p>Open the configured PayPal payment page in a new tab.</p>
                <div className="public-payment-actions">
                  <a
                    className="ghost-button payment-cta"
                    href={invoice.business.paypal_url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    Open PayPal
                  </a>
                </div>
              </div>
            ) : null}
            <div className="payment-card">
              <p className="eyebrow">Bank transfer</p>
              <strong>{invoice.business?.bank_name ?? 'Business bank'}</strong>
              <p>{invoice.business?.account_number}</p>
              <p>{invoice.business?.bsb}</p>
            </div>
            <div className="payment-card">
              <p className="eyebrow">From</p>
              <strong>{invoice.business?.name}</strong>
              <p>{invoice.business?.email}</p>
              <p>{invoice.business?.phone}</p>
              <p>{invoice.business?.payment_terms}</p>
            </div>
            <div className="payment-card">
              <p className="eyebrow">Bill to</p>
              <strong>{invoice.client?.name}</strong>
              <p>{invoice.client?.email}</p>
              <p>{invoice.notes || 'Thank you for your business.'}</p>
            </div>
          </aside>
        </div>
      </article>
    </section>
  )
}
