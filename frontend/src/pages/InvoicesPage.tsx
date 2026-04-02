import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'

import { api } from '../lib/api'
import type {
  Business,
  Client,
  ClientPayload,
  Invoice,
  InvoiceLineItemPayload,
  InvoicePayload,
  InvoiceSendResponse,
} from '../types'
import { formatCurrency, formatDate, statusLabel } from '../utils/format'

type ClientMode = 'existing' | 'new'
type SubmitMode = 'draft' | 'send'

const createEmptyLineItem = (): InvoiceLineItemPayload => ({
  description: '',
  details: '',
  qty: '1',
  rate: '0',
  adjustment_pct: '0',
})

const createEmptyInvoiceForm = (): InvoicePayload => {
  const today = new Date()
  const dueDate = new Date()
  dueDate.setDate(today.getDate() + 14)

  return {
    client_id: 0,
    order_number: '',
    invoice_date: today.toISOString().slice(0, 10),
    due_date: dueDate.toISOString().slice(0, 10),
    tax_rate_pct: '10',
    notes: '',
    line_items: [
      {
        description: 'Design and development retainer',
        details: 'Initial discovery, implementation, and QA',
        qty: '1',
        rate: '1800',
        adjustment_pct: '0',
      },
    ],
  }
}

const createEmptyClientForm = (): ClientPayload => ({
  name: '',
  email: '',
  phone: '',
  address_line1: '',
  address_line2: '',
  city_state_zip: '',
  tax_id: '',
})

function calculateLineTotal(lineItem: InvoiceLineItemPayload) {
  const quantity = Number.parseFloat(lineItem.qty || '0')
  const rate = Number.parseFloat(lineItem.rate || '0')
  const adjustment = Number.parseFloat(lineItem.adjustment_pct || '0')
  const base = quantity * rate
  return base * (1 + adjustment / 100)
}

export function InvoicesPage() {
  const [business, setBusiness] = useState<Business | null>(null)
  const [clients, setClients] = useState<Client[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [clientMode, setClientMode] = useState<ClientMode>('existing')
  const [clientForm, setClientForm] = useState<ClientPayload>(createEmptyClientForm())
  const [invoiceForm, setInvoiceForm] = useState<InvoicePayload>(createEmptyInvoiceForm())
  const [loading, setLoading] = useState(true)
  const [submittingMode, setSubmittingMode] = useState<SubmitMode | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [latestPaymentUrl, setLatestPaymentUrl] = useState<string | null>(null)

  async function loadPageData() {
    try {
      setLoading(true)
      const [businessData, clientData, invoiceData] = await Promise.all([
        api.get<Business>('/business'),
        api.get<Client[]>('/clients'),
        api.get<Invoice[]>('/invoices'),
      ])
      setBusiness(businessData)
      setClients(clientData)
      setInvoices(invoiceData)
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load invoices')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadPageData()
  }, [])

  const subtotal = useMemo(
    () => invoiceForm.line_items.reduce((total, item) => total + calculateLineTotal(item), 0),
    [invoiceForm.line_items],
  )
  const taxAmount = subtotal * (Number.parseFloat(invoiceForm.tax_rate_pct || '0') / 100)
  const grandTotal = subtotal + taxAmount

  function resetComposer() {
    setClientMode('existing')
    setClientForm(createEmptyClientForm())
    setInvoiceForm(createEmptyInvoiceForm())
  }

  function updateLineItem(index: number, key: keyof InvoiceLineItemPayload, value: string) {
    setInvoiceForm((current) => ({
      ...current,
      line_items: current.line_items.map((lineItem, lineIndex) =>
        lineIndex === index ? { ...lineItem, [key]: value } : lineItem,
      ),
    }))
  }

  function addLineItem() {
    setInvoiceForm((current) => ({
      ...current,
      line_items: [...current.line_items, createEmptyLineItem()],
    }))
  }

  function removeLineItem(index: number) {
    setInvoiceForm((current) => ({
      ...current,
      line_items:
        current.line_items.length === 1
          ? current.line_items
          : current.line_items.filter((_, lineIndex) => lineIndex !== index),
    }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSuccessMessage(null)
    setLatestPaymentUrl(null)

    const nativeEvent = event.nativeEvent as SubmitEvent
    const submitter = nativeEvent.submitter as HTMLButtonElement | null
    const mode = submitter?.dataset.submitMode === 'send' ? 'send' : 'draft'

    try {
      setSubmittingMode(mode)

      let clientId = invoiceForm.client_id
      if (clientMode === 'new') {
        const createdClient = await api.post<Client>('/clients', {
          ...clientForm,
          phone: clientForm.phone || undefined,
          address_line2: clientForm.address_line2 || undefined,
          tax_id: clientForm.tax_id || undefined,
        })
        clientId = createdClient.id
      }

      const createdInvoice = await api.post<Invoice>('/invoices', {
        ...invoiceForm,
        client_id: clientId,
        order_number: invoiceForm.order_number || undefined,
        notes: invoiceForm.notes || undefined,
        line_items: invoiceForm.line_items.map((lineItem) => ({
          ...lineItem,
          details: lineItem.details || undefined,
        })),
      })

      if (mode === 'send') {
        const sendResult = await api.post<InvoiceSendResponse>(`/invoices/${createdInvoice.id}/send`)
        setLatestPaymentUrl(sendResult.payment_url)
        setSuccessMessage(
          sendResult.email.status === 'sent'
            ? `Invoice ${sendResult.invoice_number} was emailed successfully.`
            : `Invoice ${sendResult.invoice_number} was created. Email sending was skipped because SMTP is not configured yet.`,
        )
      } else {
        setLatestPaymentUrl(createdInvoice.public_url ?? null)
        setSuccessMessage(`Draft ${createdInvoice.invoice_number} created successfully.`)
      }

      resetComposer()
      await loadPageData()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to create invoice')
    } finally {
      setSubmittingMode(null)
    }
  }

  async function handleSend(invoiceId: number) {
    try {
      const sendResult = await api.post<InvoiceSendResponse>(`/invoices/${invoiceId}/send`)
      setLatestPaymentUrl(sendResult.payment_url)
      setSuccessMessage(
        sendResult.email.status === 'sent'
          ? `Invoice ${sendResult.invoice_number} was emailed successfully.`
          : `Invoice ${sendResult.invoice_number} is ready. Email was skipped because SMTP is not configured yet.`,
      )
      await loadPageData()
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : 'Unable to send invoice')
    }
  }

  async function handleMarkOverdue(invoiceId: number) {
    try {
      await api.post(`/invoices/${invoiceId}/mark-overdue`)
      await loadPageData()
    } catch (markError) {
      setError(markError instanceof Error ? markError.message : 'Unable to mark invoice overdue')
    }
  }

  async function handleDelete(invoiceId: number) {
    try {
      await api.delete(`/invoices/${invoiceId}`)
      await loadPageData()
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Unable to delete invoice')
    }
  }

  return (
    <section className="page-stack">
      {error ? <div className="toast-banner error-message">{error}</div> : null}
      {successMessage ? <div className="toast-banner success-message">{successMessage}</div> : null}
      {latestPaymentUrl ? (
        <div className="toast-banner info-message">
          <span>Public invoice link ready:</span>
          <a href={latestPaymentUrl} target="_blank" rel="noreferrer">
            {latestPaymentUrl}
          </a>
        </div>
      ) : null}

      <section className="invoice-hero">
        <div>
          <p className="eyebrow">Invoice Composer</p>
          <h3>Create polished invoices with shareable payment pages</h3>
          <p className="empty-copy">
            Invoice numbers are assigned automatically by the backend. You can save a
            draft or create and send in one flow.
          </p>
        </div>
        <div className="hero-stats">
          <div className="hero-stat">
            <span>Business</span>
            <strong>{business?.name ?? 'Loading...'}</strong>
          </div>
          <div className="hero-stat">
            <span>Clients</span>
            <strong>{clients.length}</strong>
          </div>
          <div className="hero-stat">
            <span>Invoices</span>
            <strong>{invoices.length}</strong>
          </div>
        </div>
      </section>

      <div className="invoice-layout">
        <article className="page-panel invoice-composer-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Draft Invoice</p>
              <h3>Billing details and client intake</h3>
            </div>
            <span className="auto-pill">Invoice number assigned on save</span>
          </div>

          <form
            className="invoice-composer"
            onSubmit={(event) => void handleSubmit(event)}
          >
            <section className="composer-block">
              <div className="subsection-header">
                <h4>Client</h4>
                <div className="segmented-control" role="tablist" aria-label="Client mode">
                  <button
                    className={clientMode === 'existing' ? 'segment-active' : ''}
                    type="button"
                    onClick={() => setClientMode('existing')}
                  >
                    Existing
                  </button>
                  <button
                    className={clientMode === 'new' ? 'segment-active' : ''}
                    type="button"
                    onClick={() => setClientMode('new')}
                  >
                    New client
                  </button>
                </div>
              </div>

              {clientMode === 'existing' ? (
                <div className="form-grid">
                  <label className="field-span-full">
                    <span>Select client</span>
                    <select
                      required
                      value={invoiceForm.client_id}
                      onChange={(event) =>
                        setInvoiceForm({
                          ...invoiceForm,
                          client_id: Number.parseInt(event.target.value, 10) || 0,
                        })
                      }
                    >
                      <option value={0}>Choose an existing client</option>
                      {clients.map((client) => (
                        <option key={client.id} value={client.id}>
                          {client.name} · {client.email}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              ) : (
                <div className="form-grid">
                  <label>
                    <span>Client name</span>
                    <input
                      required
                      value={clientForm.name}
                      onChange={(event) =>
                        setClientForm({ ...clientForm, name: event.target.value })
                      }
                    />
                  </label>
                  <label>
                    <span>Email</span>
                    <input
                      required
                      type="email"
                      value={clientForm.email}
                      onChange={(event) =>
                        setClientForm({ ...clientForm, email: event.target.value })
                      }
                    />
                  </label>
                  <label>
                    <span>Phone</span>
                    <input
                      value={clientForm.phone}
                      onChange={(event) =>
                        setClientForm({ ...clientForm, phone: event.target.value })
                      }
                    />
                  </label>
                  <label>
                    <span>Tax ID</span>
                    <input
                      value={clientForm.tax_id}
                      onChange={(event) =>
                        setClientForm({ ...clientForm, tax_id: event.target.value })
                      }
                    />
                  </label>
                  <label className="field-span-full">
                    <span>Address line 1</span>
                    <input
                      required
                      value={clientForm.address_line1}
                      onChange={(event) =>
                        setClientForm({ ...clientForm, address_line1: event.target.value })
                      }
                    />
                  </label>
                  <label className="field-span-full">
                    <span>Address line 2</span>
                    <input
                      value={clientForm.address_line2}
                      onChange={(event) =>
                        setClientForm({ ...clientForm, address_line2: event.target.value })
                      }
                    />
                  </label>
                  <label className="field-span-full">
                    <span>City / State / ZIP</span>
                    <input
                      required
                      value={clientForm.city_state_zip}
                      onChange={(event) =>
                        setClientForm({ ...clientForm, city_state_zip: event.target.value })
                      }
                    />
                  </label>
                </div>
              )}
            </section>

            <section className="composer-block">
              <div className="subsection-header">
                <h4>Invoice details</h4>
              </div>
              <div className="form-grid">
                <label>
                  <span>Order / PO number</span>
                  <input
                    value={invoiceForm.order_number}
                    onChange={(event) =>
                      setInvoiceForm({ ...invoiceForm, order_number: event.target.value })
                    }
                  />
                </label>
                <label>
                  <span>Tax rate %</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={invoiceForm.tax_rate_pct}
                    onChange={(event) =>
                      setInvoiceForm({ ...invoiceForm, tax_rate_pct: event.target.value })
                    }
                  />
                </label>
                <label>
                  <span>Invoice date</span>
                  <input
                    required
                    type="date"
                    value={invoiceForm.invoice_date}
                    onChange={(event) =>
                      setInvoiceForm({ ...invoiceForm, invoice_date: event.target.value })
                    }
                  />
                </label>
                <label>
                  <span>Due date</span>
                  <input
                    required
                    type="date"
                    value={invoiceForm.due_date}
                    onChange={(event) =>
                      setInvoiceForm({ ...invoiceForm, due_date: event.target.value })
                    }
                  />
                </label>
                <label className="field-span-full">
                  <span>Internal note / terms</span>
                  <textarea
                    rows={3}
                    value={invoiceForm.notes}
                    onChange={(event) =>
                      setInvoiceForm({ ...invoiceForm, notes: event.target.value })
                    }
                  />
                </label>
              </div>
            </section>

            <section className="composer-block">
              <div className="subsection-header">
                <h4>Line items</h4>
                <button className="ghost-button" type="button" onClick={addLineItem}>
                  Add line item
                </button>
              </div>
              <div className="line-item-stack">
                {invoiceForm.line_items.map((lineItem, index) => (
                  <div key={index} className="line-item-card line-item-card-rich">
                    <div className="line-item-grid">
                      <label className="field-span-full">
                        <span>Description</span>
                        <input
                          required
                          value={lineItem.description}
                          onChange={(event) =>
                            updateLineItem(index, 'description', event.target.value)
                          }
                        />
                      </label>
                      <label className="field-span-full">
                        <span>Details</span>
                        <input
                          value={lineItem.details}
                          onChange={(event) =>
                            updateLineItem(index, 'details', event.target.value)
                          }
                        />
                      </label>
                      <label>
                        <span>Qty</span>
                        <input
                          required
                          type="number"
                          min="0.01"
                          step="0.01"
                          value={lineItem.qty}
                          onChange={(event) => updateLineItem(index, 'qty', event.target.value)}
                        />
                      </label>
                      <label>
                        <span>Rate</span>
                        <input
                          required
                          type="number"
                          min="0"
                          step="0.01"
                          value={lineItem.rate}
                          onChange={(event) => updateLineItem(index, 'rate', event.target.value)}
                        />
                      </label>
                      <label>
                        <span>Adjust %</span>
                        <input
                          type="number"
                          min="-100"
                          max="100"
                          step="0.01"
                          value={lineItem.adjustment_pct}
                          onChange={(event) =>
                            updateLineItem(index, 'adjustment_pct', event.target.value)
                          }
                        />
                      </label>
                      <div className="line-item-total">
                        <span>Line total</span>
                        <strong>{formatCurrency(calculateLineTotal(lineItem))}</strong>
                      </div>
                    </div>
                    <button
                      className="ghost-button danger-button"
                      type="button"
                      onClick={() => removeLineItem(index)}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            </section>

            <div className="composer-actions">
              <button className="ghost-button" type="button" onClick={resetComposer}>
                Reset
              </button>
              <div className="composer-submit-group">
                <button
                  className="ghost-button"
                  type="submit"
                  data-submit-mode="draft"
                  disabled={submittingMode !== null || (clientMode === 'existing' && clients.length === 0)}
                >
                  {submittingMode === 'draft' ? 'Saving...' : 'Save draft'}
                </button>
                <button
                  className="primary-button"
                  type="submit"
                  data-submit-mode="send"
                  disabled={submittingMode !== null || (clientMode === 'existing' && clients.length === 0)}
                >
                  {submittingMode === 'send' ? 'Creating & sending...' : 'Create and send'}
                </button>
              </div>
            </div>
          </form>
        </article>

        <aside className="page-panel invoice-summary-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Live totals</p>
              <h3>What the client will see</h3>
            </div>
          </div>
          <div className="summary-card-stack">
            <div className="summary-row">
              <span>Subtotal</span>
              <strong>{formatCurrency(subtotal)}</strong>
            </div>
            <div className="summary-row">
              <span>Tax</span>
              <strong>{formatCurrency(taxAmount)}</strong>
            </div>
            <div className="summary-row summary-row-total">
              <span>Total due</span>
              <strong>{formatCurrency(grandTotal)}</strong>
            </div>
          </div>
          <div className="summary-card-stack">
            <div className="summary-caption">Sender</div>
            <strong>{business?.name ?? 'Business profile'}</strong>
            <span>{business?.email}</span>
            <span>{business?.payment_terms}</span>
          </div>
          <div className="summary-card-stack">
            <div className="summary-caption">Payment page</div>
            <span>
              Each invoice gets a clean public URL after creation, using the backend
              invoice id.
            </span>
          </div>
        </aside>
      </div>

      <article className="page-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Invoice Register</p>
            <h3>{invoices.length} invoices</h3>
          </div>
        </div>
        {loading ? (
          <p>Loading invoices...</p>
        ) : invoices.length === 0 ? (
          <p className="empty-copy">Create an invoice to start your collection workflow.</p>
        ) : (
          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Client</th>
                  <th>Status</th>
                  <th>Due</th>
                  <th>Total</th>
                  <th>Payment link</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice) => (
                  <tr key={invoice.id}>
                    <td>
                      <strong>{invoice.invoice_number}</strong>
                      <div className="table-subcopy">{invoice.order_number}</div>
                    </td>
                    <td>{invoice.client?.name ?? `Client #${invoice.client_id}`}</td>
                    <td>
                      <span className={`badge badge-${invoice.status}`}>
                        {statusLabel(invoice.status)}
                      </span>
                    </td>
                    <td>{formatDate(invoice.due_date)}</td>
                    <td>{formatCurrency(invoice.total)}</td>
                    <td>
                      {invoice.public_url ? (
                        <a href={invoice.public_url} target="_blank" rel="noreferrer">
                          Open payment page
                        </a>
                      ) : (
                        'Available after load'
                      )}
                    </td>
                    <td>
                      <div className="action-row wrap-row">
                        <button
                          className="ghost-button"
                          type="button"
                          onClick={() =>
                            window.open(`${api.baseUrl}/public/invoices/${invoice.id}/pdf`, '_blank')
                          }
                        >
                          PDF
                        </button>
                        <button
                          className="ghost-button"
                          type="button"
                          onClick={() => void handleSend(invoice.id)}
                        >
                          Send
                        </button>
                        {invoice.public_url ? (
                          <button
                            className="ghost-button"
                            type="button"
                            onClick={() => window.open(invoice.public_url ?? '', '_blank')}
                          >
                            Page
                          </button>
                        ) : null}
                        <button
                          className="ghost-button"
                          type="button"
                          onClick={() => void handleMarkOverdue(invoice.id)}
                        >
                          Overdue
                        </button>
                        {invoice.status === 'draft' ? (
                          <button
                            className="ghost-button danger-button"
                            type="button"
                            onClick={() => void handleDelete(invoice.id)}
                          >
                            Delete
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </section>
  )
}
