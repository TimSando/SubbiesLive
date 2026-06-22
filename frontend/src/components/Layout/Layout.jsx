import { useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import NotificationToggle from '../NotificationToggle/NotificationToggle.jsx'
import WalkthroughModal from '../Walkthrough/WalkthroughModal.jsx'
import ReloadPrompt from '../ReloadPrompt/ReloadPrompt.jsx'
import './Layout.css'

const navLinks = [
  { path: '/', label: 'Home' },
  { path: '/clubs', label: 'Clubs' },
  { path: '/competitions', label: 'Competitions' },
  { path: '/stats', label: 'Stats' },
  { path: '/refzone', label: 'RefZone' },
  { path: '/notifications', label: 'Notifications' },
]

export default function Layout() {
  const location = useLocation()
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen)
  const closeMenu = () => setIsMenuOpen(false)

  return (
    <div className="layout">
      <WalkthroughModal />
      <ReloadPrompt />
      <nav className="nav" id="main-nav">
        <div className="container nav__inner">
          {/* Top Left: Burger Menu Button */}
          <button 
            className={`nav__burger ${isMenuOpen ? 'nav__burger--open' : ''}`}
            onClick={toggleMenu}
            aria-label="Toggle navigation menu"
            id="nav-burger-button"
          >
            <span className="nav__burger-bar" />
            <span className="nav__burger-bar" />
            <span className="nav__burger-bar" />
          </button>

          {/* Top Right: Brand Logo and Title */}
          <Link to="/" className="nav__brand" onClick={closeMenu}>
            <span className="nav__brand-icon">🏉</span>
            <span className="nav__brand-text">SubbiesStats</span>
          </Link>
        </div>
      </nav>

      {/* Slide-out Left Side Drawer */}
      <div 
        className={`nav__drawer-backdrop ${isMenuOpen ? 'nav__drawer-backdrop--open' : ''}`} 
        onClick={closeMenu} 
      />
      
      <aside className={`nav__drawer ${isMenuOpen ? 'nav__drawer--open' : ''}`}>
        <div className="nav__drawer-header">
          <span className="nav__drawer-title">Menu</span>
        </div>
        <div className="nav__drawer-links">
          {navLinks.map(link => (
            <Link
              key={link.path}
              to={link.path}
              className={`nav__drawer-link ${location.pathname === link.path ? 'nav__drawer-link--active' : ''}`}
              onClick={closeMenu}
            >
              {link.label}
            </Link>
          ))}
        </div>
        <div className="nav__drawer-footer">
          <span className="nav__drawer-footer-label">Push Alerts</span>
          <NotificationToggle />
        </div>
      </aside>

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
