import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from './components/AppShell'
import { ProtectedRoute } from './components/ProtectedRoute'
import { BusinessPage } from './pages/BusinessPage'
import { ClientsPage } from './pages/ClientsPage'
import { DashboardPage } from './pages/DashboardPage'
import { InvoicesPage } from './pages/InvoicesPage'
import { LoginPage } from './pages/LoginPage'
import { PaymentsPage } from './pages/PaymentsPage'
import { PublicInvoicePage } from './pages/PublicInvoicePage'
import { SettingsPage } from './pages/SettingsPage'

function NotFoundPage() {
  return (
    <section className="page-panel">
      <p className="eyebrow">404</p>
      <h3>That page does not exist.</h3>
    </section>
  )
}

function App() {
  return (
    <Routes>
      <Route path="pay/:invoiceId" element={<PublicInvoicePage />} />
      <Route path="login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="invoices" element={<InvoicesPage />} />
          <Route path="clients" element={<ClientsPage />} />
          <Route path="payments" element={<PaymentsPage />} />
          <Route path="business" element={<BusinessPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="home" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  )
}

export default App
