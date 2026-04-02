import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth'
import { useTheme } from '../theme'

const navigation = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/invoices', label: 'Invoices' },
  { to: '/clients', label: 'Clients' },
  { to: '/payments', label: 'Payments' },
  { to: '/business', label: 'Business' },
  { to: '/settings', label: 'Settings' },
]

export function AppShell() {
  const { profile, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()
  const navigate = useNavigate()

  const currentSection =
    navigation.find((item) =>
      item.end ? item.to === location.pathname : location.pathname.startsWith(item.to),
    ) ?? navigation[0]

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">NL</div>
          <div className="brand-meta">
            <span className="brand-title">Admin</span>
          </div>
        </div>

        <nav className="nav-list" aria-label="Primary">
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `nav-item${isActive ? ' nav-item-active' : ''}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-foot">
          <button className="sidebar-action" type="button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </aside>

      <main className="content-area">
        <header className="topbar">
          <div className="topbar-breadcrumbs">
            <span className="topbar-path">Admin dashboard</span>
            <h2>{currentSection.label}</h2>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" type="button" onClick={toggleTheme}>
              {theme === 'dark' ? 'Light mode' : 'Dark mode'}
            </button>
            <div className="topbar-card topbar-user">
              <div className="user-pill">{profile?.username.slice(0, 2) ?? 'ad'}</div>
              <div className="topbar-user-meta">
                <strong>{profile?.username ?? 'admin'}</strong>
                <span>Authenticated</span>
              </div>
            </div>
          </div>
        </header>

        <Outlet />
      </main>
    </div>
  )
}
