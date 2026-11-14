import { lazy, Suspense, useEffect, useState } from 'react'
import {
  Activity,
  BookOpenText,
  ChartNoAxesCombined,
  ChevronLeft,
  ChevronRight,
  CircleCheck,
  CircleHelp,
  CircleX,
  LayoutDashboard,
  Plus,
  RefreshCw,
  Ticket,
} from 'lucide-react'
import {
  BrowserRouter,
  NavLink,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'

import { api } from './api'
import { ErrorInline, LoadingState } from './components'

const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((module) => ({
    default: module.DashboardPage,
  })),
)
const TicketsPage = lazy(() =>
  import('./pages/TicketsPage').then((module) => ({ default: module.TicketsPage })),
)
const NewTicketPage = lazy(() =>
  import('./pages/NewTicketPage').then((module) => ({
    default: module.NewTicketPage,
  })),
)
const TicketDetailsPage = lazy(() =>
  import('./pages/TicketDetailsPage').then((module) => ({
    default: module.TicketDetailsPage,
  })),
)
const KnowledgePage = lazy(() =>
  import('./pages/KnowledgePage').then((module) => ({
    default: module.KnowledgePage,
  })),
)
const AnalyticsPage = lazy(() =>
  import('./pages/AnalyticsPage').then((module) => ({
    default: module.AnalyticsPage,
  })),
)

const navigation = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard, end: true },
  { label: 'Tickets', to: '/tickets', icon: Ticket },
  { label: 'Knowledge base', to: '/knowledge', icon: BookOpenText },
  { label: 'Analytics', to: '/analytics', icon: ChartNoAxesCombined },
]

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/tickets': 'Tickets',
  '/tickets/new': 'New ticket',
  '/knowledge': 'Knowledge base',
  '/analytics': 'Analytics',
}

function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [apiState, setApiState] = useState<'checking' | 'online' | 'offline'>(
    'checking',
  )
  const [healthError, setHealthError] = useState('')
  const [checking, setChecking] = useState(false)
  const location = useLocation()
  const pageTitle =
    location.pathname.startsWith('/tickets/') &&
    location.pathname !== '/tickets/new'
      ? 'Ticket details'
      : pageTitles[location.pathname] ?? 'ResolveIQ'

  async function checkConnection() {
    setChecking(true)
    try {
      await api.health()
      setApiState('online')
      setHealthError('')
    } catch (error) {
      setApiState('offline')
      setHealthError(
        error instanceof Error ? error.message : 'Backend health check failed.',
      )
    } finally {
      setChecking(false)
    }
  }

  useEffect(() => {
    let active = true
    void api.health().then(
      () => {
        if (active) {
          setApiState('online')
          setHealthError('')
        }
      },
      (error: unknown) => {
        if (active) {
          setApiState('offline')
          setHealthError(
            error instanceof Error ? error.message : 'Backend health check failed.',
          )
        }
      },
    )
    return () => {
      active = false
    }
  }, [])

  return (
    <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <aside className="sidebar">
        <NavLink to="/" className="brand-lockup" aria-label="ResolveIQ dashboard">
          <span className="brand-mark">
            <Activity size={20} strokeWidth={2.5} />
          </span>
          {!collapsed && (
            <span className="brand-name">
              resolve<span>iq</span>
            </span>
          )}
        </NavLink>

        <div className="workspace-switcher">
          <span className="workspace-avatar">R</span>
          {!collapsed && (
            <span className="workspace-copy">
              <span>Workspace</span>
              <strong>ResolveIQ demo</strong>
            </span>
          )}
          {!collapsed && <ChevronRight className="ml-auto text-slate-400" size={15} />}
        </div>

        {!collapsed && <p className="nav-caption">WORKSPACE</p>}
        <nav className="sidebar-nav" aria-label="Main navigation">
          {navigation.map(({ label, to, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              title={collapsed ? label : undefined}
              className={({ isActive }) =>
                `nav-link ${isActive ? 'nav-link-active' : ''}`
              }
            >
              <Icon size={19} strokeWidth={1.9} />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        {!collapsed && (
          <div className="sidebar-bottom">
            <div className="sidebar-note">
              <span className="sidebar-note-icon">
                <CircleHelp size={17} />
              </span>
              <strong>Need a hand?</strong>
              <p>Browse the knowledge base for guided troubleshooting.</p>
              <NavLink to="/knowledge">Explore articles <span>→</span></NavLink>
            </div>
            <div className="demo-user">
              <span className="user-avatar">DE</span>
              <span>
                <strong>Demo operator</strong>
                <small>Demo workspace</small>
              </span>
              <span className="demo-pill">DEMO</span>
            </div>
          </div>
        )}
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="icon-button sidebar-toggle"
              onClick={() => setCollapsed((value) => !value)}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
            </button>
            <div className="breadcrumb">
              <span>Workspace</span>
              <span className="breadcrumb-slash">/</span>
              <strong>{pageTitle}</strong>
            </div>
          </div>
          <div className="topbar-actions">
            <button
              type="button"
              className={`connection-indicator connection-${apiState}`}
              onClick={() => void checkConnection()}
              title={healthError || 'Check backend connection'}
              aria-label="Check backend connection"
            >
              {checking ? (
                <RefreshCw className="animate-spin" size={14} />
              ) : apiState === 'online' ? (
                <CircleCheck size={15} />
              ) : apiState === 'offline' ? (
                <CircleX size={15} />
              ) : (
                <RefreshCw size={14} />
              )}
              <span>
                {checking
                  ? 'Checking'
                  : apiState === 'online'
                    ? 'API connected'
                    : apiState === 'offline'
                      ? 'API offline'
                      : 'API status'}
              </span>
            </button>
            <NavLink to="/tickets/new" className="button button-primary topbar-create">
              <Plus size={17} />
              <span>Create ticket</span>
            </NavLink>
          </div>
        </header>
        {apiState === 'offline' && healthError && (
          <div className="topbar-error">
            <ErrorInline message={healthError} />
            <button
              type="button"
              className="icon-button"
              aria-label="Dismiss API message"
              onClick={() => setHealthError('')}
            >
              <CircleX size={16} />
            </button>
          </div>
        )}
        <main className="page-content">
          <Suspense fallback={<LoadingState label="Loading workspace" />}>
            <Outlet />
          </Suspense>
        </main>
        <footer className="app-footer">
          <span>ResolveIQ support workspace</span>
          <span>AI recommendations use synthetic demo data</span>
        </footer>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="tickets" element={<TicketsPage />} />
          <Route path="tickets/new" element={<NewTicketPage />} />
          <Route path="tickets/:id" element={<TicketDetailsPage />} />
          <Route path="knowledge" element={<KnowledgePage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
