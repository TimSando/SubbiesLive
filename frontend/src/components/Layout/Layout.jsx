import { Outlet, Link, useLocation } from 'react-router-dom'
import NotificationToggle from '../NotificationToggle/NotificationToggle.jsx'
import './Layout.css'

const navLinks = [
  { path: '/', label: 'Home' },
  { path: '/clubs', label: 'Clubs' },
  { path: '/competitions', label: 'Competitions' },
  { path: '/stats', label: 'Stats' },
  { path: '/refzone', label: 'RefZone' },
]


export default function Layout() {
  const location = useLocation()

  return (
    <div className="layout">
      <nav className="nav" id="main-nav">
        <div className="container nav__inner">
          <Link to="/" className="nav__brand">
            <span className="nav__brand-icon">🏉</span>
            <span className="nav__brand-text">SubbiesStats</span>
          </Link>
          <div className="nav__links">
            {navLinks.map(link => (
              <Link
                key={link.path}
                to={link.path}
                className={`nav__link ${location.pathname === link.path ? 'nav__link--active' : ''}`}
              >
                {link.label}
              </Link>
            ))}
            <NotificationToggle />
          </div>
        </div>
      </nav>

      <main>
        <Outlet />
      </main>

      <footer className="footer" id="main-footer">
        <div className="container footer__inner">
          <p className="footer__text">
            SubbiesStats — Sydney Suburban Rugby Union Statistics
          </p>
          <p className="footer__text footer__text--muted">
            Data sourced from FuseSport. Not affiliated with any rugby union body.
          </p>
        </div>
      </footer>
    </div>
  )
}
