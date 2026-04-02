import { useEffect, useState } from 'react'

import { api } from '../lib/api'
import type { DashboardData } from '../types'
import { formatCurrency, formatDate, statusLabel } from '../utils/format'

export function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function loadDashboard() {
      try {
        setLoading(true)
        const data = await api.get<DashboardData>('/dashboard')
        if (active) {
          setDashboard(data)
          setError(null)
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to load dashboard')
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void loadDashboard()

    return () => {
      active = false
    }
  }, [])

  if (loading) {
    return <section className="page-panel">Loading dashboard...</section>
  }

  if (error || !dashboard) {
    return <section className="page-panel error-message">{error ?? 'Dashboard unavailable'}</section>
  }

  const metrics = [
    { label: 'Total Revenue', value: formatCurrency(dashboard.summary.total_revenue) },
    { label: 'Outstanding', value: formatCurrency(dashboard.summary.outstanding_amount) },
    { label: 'Invoices', value: String(dashboard.summary.total_invoices) },
    { label: 'Overdue', value: String(dashboard.summary.overdue_invoices) },
  ]

  const maxRevenue = Math.max(
    ...dashboard.monthly_revenue.map((entry) => Number.parseFloat(entry.amount)),
    1,
  )
  const hottestMonth = dashboard.monthly_revenue.reduce((current, entry) =>
    Number.parseFloat(entry.amount) > Number.parseFloat(current.amount) ? entry : current,
  )
  const averageRevenue =
    dashboard.monthly_revenue.reduce(
      (total, entry) => total + Number.parseFloat(entry.amount),
      0,
    ) / Math.max(dashboard.monthly_revenue.length, 1)

  return (
    <section className="page-stack">
      <div className="metrics-grid">
        {metrics.map((metric) => (
          <article key={metric.label} className="metric-card">
            <p>{metric.label}</p>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </div>

      <div className="split-grid">
        <article className="page-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Revenue Trend</p>
              <h3>Revenue heatmap</h3>
            </div>
          </div>
          <div className="heatmap-shell">
            <div className="heatmap-meta">
              <div className="heatmap-stat">
                <span>Peak month</span>
                <strong>{hottestMonth.label}</strong>
                <p>{formatCurrency(hottestMonth.amount)}</p>
              </div>
              <div className="heatmap-stat">
                <span>Monthly average</span>
                <strong>{formatCurrency(averageRevenue)}</strong>
                <p>Across the last 12 months</p>
              </div>
            </div>

            <div className="heatmap-grid" role="img" aria-label="Monthly revenue heatmap">
              {dashboard.monthly_revenue.map((entry) => {
                const amount = Number.parseFloat(entry.amount)
                const intensity = Math.max(0.12, amount / maxRevenue)

                return (
                  <div
                    key={entry.month}
                    className="heatmap-cell"
                    style={{
                      opacity: `${0.35 + intensity * 0.65}`,
                      transform: `scale(${0.94 + intensity * 0.08})`,
                    }}
                    title={`${entry.label}: ${formatCurrency(entry.amount)}`}
                  >
                    <span className="heatmap-month">{entry.label}</span>
                    <strong>{formatCurrency(entry.amount)}</strong>
                  </div>
                )
              })}
            </div>

            <div className="heatmap-legend">
              <span>Low</span>
              <div className="heatmap-legend-scale">
                <i />
                <i />
                <i />
                <i />
              </div>
              <span>High</span>
            </div>
          </div>
        </article>

        <article className="page-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Status Mix</p>
              <h3>Invoice workflow snapshot</h3>
            </div>
          </div>
          <div className="chip-wrap">
            {Object.entries(dashboard.by_status).map(([status, count]) => (
              <div key={status} className="status-chip">
                <span className={`badge badge-${status}`}>{statusLabel(status)}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
          <div className="top-list">
            <h4>Top clients</h4>
            {dashboard.top_clients.length === 0 ? (
              <p className="empty-copy">Payments will surface your highest-value clients here.</p>
            ) : (
              dashboard.top_clients.map((client) => (
                <div key={client.client_id} className="list-row">
                  <span>{client.client_name}</span>
                  <strong>{formatCurrency(client.amount)}</strong>
                </div>
              ))
            )}
          </div>
        </article>
      </div>

      <article className="page-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Recent Payments</p>
            <h3>Latest money in</h3>
          </div>
        </div>
        {dashboard.recent_payments.length === 0 ? (
          <p className="empty-copy">No payments recorded yet.</p>
        ) : (
          <div className="table-shell">
            <table>
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Client</th>
                  <th>Date</th>
                  <th>Method</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.recent_payments.map((payment) => (
                  <tr key={payment.id}>
                    <td>{payment.invoice_number}</td>
                    <td>{payment.client_name}</td>
                    <td>{formatDate(payment.date)}</td>
                    <td>{statusLabel(payment.method)}</td>
                    <td>{formatCurrency(payment.amount)}</td>
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
