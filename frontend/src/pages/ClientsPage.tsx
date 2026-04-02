import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import { api } from '../lib/api'
import type { Client, ClientPayload } from '../types'
import { formatDate } from '../utils/format'

const emptyClientForm: ClientPayload = {
  name: '',
  email: '',
  phone: '',
  address_line1: '',
  address_line2: '',
  city_state_zip: '',
  tax_id: '',
}

export function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([])
  const [form, setForm] = useState<ClientPayload>(emptyClientForm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadClients() {
    try {
      setLoading(true)
      const data = await api.get<Client[]>('/clients')
      setClients(data)
      setError(null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load clients')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadClients()
  }, [])

  function startEdit(client: Client) {
    setEditingId(client.id)
    setForm({
      name: client.name,
      email: client.email,
      phone: client.phone ?? '',
      address_line1: client.address_line1,
      address_line2: client.address_line2 ?? '',
      city_state_zip: client.city_state_zip,
      tax_id: client.tax_id ?? '',
    })
  }

  function resetForm() {
    setEditingId(null)
    setForm(emptyClientForm)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      setSaving(true)
      const payload = {
        ...form,
        phone: form.phone || undefined,
        address_line2: form.address_line2 || undefined,
        tax_id: form.tax_id || undefined,
      }
      if (editingId) {
        await api.put<Client>(`/clients/${editingId}`, payload)
      } else {
        await api.post<Client>('/clients', payload)
      }
      resetForm()
      await loadClients()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to save client')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(clientId: number) {
    try {
      await api.delete(`/clients/${clientId}`)
      if (editingId === clientId) {
        resetForm()
      }
      await loadClients()
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'Unable to delete client')
    }
  }

  return (
    <section className="page-stack">
      {error ? <div className="toast-banner error-message">{error}</div> : null}

      <div className="split-grid">
        <article className="page-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">{editingId ? 'Edit Client' : 'New Client'}</p>
              <h3>Store billing contacts</h3>
            </div>
          </div>
          <form className="form-grid" onSubmit={handleSubmit}>
            <label>
              <span>Name</span>
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
            <div className="form-actions field-span-full">
              <button className="ghost-button" type="button" onClick={resetForm}>
                Reset
              </button>
              <button className="primary-button" type="submit" disabled={saving}>
                {saving ? 'Saving...' : editingId ? 'Update client' : 'Create client'}
              </button>
            </div>
          </form>
        </article>

        <article className="page-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Client Directory</p>
              <h3>{clients.length} saved contacts</h3>
            </div>
          </div>
          {loading ? (
            <p>Loading clients...</p>
          ) : clients.length === 0 ? (
            <p className="empty-copy">Add your first client to start issuing invoices.</p>
          ) : (
            <div className="table-shell">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Updated</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {clients.map((client) => (
                    <tr key={client.id}>
                      <td>{client.name}</td>
                      <td>{client.email}</td>
                      <td>{formatDate(client.updated_at)}</td>
                      <td>
                        <div className="action-row">
                          <button className="ghost-button" type="button" onClick={() => startEdit(client)}>
                            Edit
                          </button>
                          <button
                            className="ghost-button danger-button"
                            type="button"
                            onClick={() => void handleDelete(client.id)}
                          >
                            Delete
                          </button>
                        </div>
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
