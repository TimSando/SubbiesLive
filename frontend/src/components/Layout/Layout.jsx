import { useState, useEffect } from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import NotificationToggle from '../NotificationToggle/NotificationToggle.jsx'
import WalkthroughModal from '../Walkthrough/WalkthroughModal.jsx'
import ReloadPrompt from '../ReloadPrompt/ReloadPrompt.jsx'
import { api } from '../../api/client.js'
import './Layout.css'

const primaryLinks = [
  {
    path: '/',
    label: 'Home',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="nav-bottom-link__icon-svg">
        <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
        <polyline points="9 22 9 12 15 12 15 22"/>
      </svg>
    )
  },
  {
    path: '/clubs',
    label: 'Clubs',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="nav-bottom-link__icon-svg">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
    )
  },
  {
    path: '/competitions',
    label: 'Competitions',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="nav-bottom-link__icon-svg">
        <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>
        <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>
        <path d="M4 22h16"/>
        <path d="M10 14.66V17c0 .55-.45 1-1 1H4v2h16v-2h-5c-.55 0-1-.45-1-1v-2.34"/>
        <path d="M12 2a6 6 0 0 0-6 6v1c0 2.2 1.8 4 4 4h4c2.2 0 4-1.8 4-4V8a6 6 0 0 0-6-6z"/>
      </svg>
    )
  },
  {
    path: '/stats',
    label: 'Stats',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="nav-bottom-link__icon-svg">
        <line x1="18" y1="20" x2="18" y2="10"/>
        <line x1="12" y1="20" x2="12" y2="4"/>
        <line x1="6" y1="20" x2="6" y2="14"/>
      </svg>
    )
  }
]

const secondaryLinks = [
  { path: '/refzone', label: 'RefZone' },
  { path: '/notifications', label: 'Notifications' }
]

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [password, setPassword] = useState('')
  const [syncError, setSyncError] = useState('')
  const [syncSuccess, setSyncSuccess] = useState('')
  const [isFadingOut, setIsFadingOut] = useState(false)

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen)
  const closeMenu = () => setIsMenuOpen(false)

  // Handle PWA notification click message navigation
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      const handleServiceWorkerMessage = (event) => {
        if (event.data && event.data.type === 'NAVIGATE') {
          const url = new URL(event.data.url, window.location.origin)
          navigate(url.pathname + url.search)
        }
      }
      navigator.serviceWorker.addEventListener('message', handleServiceWorkerMessage)
      return () => {
        navigator.serviceWorker.removeEventListener('message', handleServiceWorkerMessage)
      }
    }
  }, [navigate])

  // Poll database status
  useEffect(() => {
    let active = true
    let intervalId

    async function checkStatus() {
      try {
        const res = await api.getIngestionStatus()
        if (active) {
          setIsSyncing(res.running)
          if (!res.running && intervalId) {
            clearInterval(intervalId)
            intervalId = null
          }
        }
      } catch (err) {
        console.error('Error checking ingestion status:', err)
      }
    }

    checkStatus()

    if (isSyncing) {
      intervalId = setInterval(checkStatus, 5000)
    }

    return () => {
      active = false
      if (intervalId) clearInterval(intervalId)
    }
  }, [isSyncing])

  const handleSyncSubmit = async (e) => {
    e.preventDefault()
    setSyncError('')
    setSyncSuccess('')
    try {
      const res = await api.triggerIngestion(password)
      if (res.status === 'started' || res.status === 'running') {
        setSyncSuccess(res.message)
        setIsSyncing(true)
        // Trigger fade out after 1 second of success display, close modal after fade-out finishes
        setTimeout(() => {
          setIsFadingOut(true)
          setTimeout(() => {
            setShowModal(false)
            setIsFadingOut(false)
            setPassword('')
            setSyncSuccess('')
          }, 300) // matches CSS animation duration
        }, 1000)
      } else {
        setSyncError(res.message || 'Unknown response')
      }
    } catch (err) {
      setSyncError('Unauthorized or invalid password')
    }
  }

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

          {/* Brand Logo and Title */}
          <Link to="/" className="nav__brand" onClick={closeMenu}>
            <span className="nav__brand-icon">🏉</span>
            <span className="nav__brand-text">SubbiesStats</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="nav__desktop-links">
            {[...primaryLinks, ...secondaryLinks].map((link) => (
              <Link 
                key={link.path} 
                to={link.path} 
                className={`nav__desktop-link ${location.pathname === link.path ? 'nav__desktop-link--active' : ''}`}
              >
                {link.label}
              </Link>
            ))}
            <button
              onClick={() => {
                if (!isSyncing) setShowModal(true)
              }}
              className="nav__desktop-link"
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontFamily: 'inherit',
                fontSize: 'inherit',
                fontWeight: 'inherit',
                padding: 0,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px'
              }}
              disabled={isSyncing}
            >
              <span>Force Refresh</span>
              {isSyncing && <span className="nav-desktop-sync-spinner">🔄</span>}
            </button>
          </div>
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
          {primaryLinks.map(link => (
            <Link
              key={link.path}
              to={link.path}
              className={`nav__drawer-link ${location.pathname === link.path ? 'nav__drawer-link--active' : ''}`}
              onClick={closeMenu}
            >
              {link.label}
            </Link>
          ))}

          <hr className="nav__drawer-divider" />
          <div className="nav__drawer-section-title">Tools & Settings</div>

          {secondaryLinks.map(link => (
            <Link
              key={link.path}
              to={link.path}
              className={`nav__drawer-link ${location.pathname === link.path ? 'nav__drawer-link--active' : ''}`}
              onClick={closeMenu}
            >
              {link.label}
            </Link>
          ))}

          <button
            onClick={() => {
              closeMenu()
              if (!isSyncing) setShowModal(true)
            }}
            className="nav__drawer-link"
            style={{
              background: 'none',
              border: 'none',
              textAlign: 'left',
              width: '100%',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontFamily: 'inherit',
              fontWeight: 'inherit',
              color: 'var(--color-text-secondary)',
              borderRadius: 'var(--radius-md)',
              transition: 'all var(--transition-fast)'
            }}
            disabled={isSyncing}
          >
            <span>Force Refresh</span>
            {isSyncing && <span className="nav__drawer-sync-spinner">🔄</span>}
          </button>
        </div>
        <div className="nav__drawer-footer">
          <span className="nav__drawer-footer-label">Push Alerts</span>
          <NotificationToggle />
        </div>
      </aside>

      {/* Mobile Bottom Tab Bar */}
      <nav className="nav-bottom-bar">
        {primaryLinks.map(link => (
          <Link 
            key={link.path} 
            to={link.path} 
            className={`nav-bottom-link ${location.pathname === link.path ? 'nav-bottom-link--active' : ''}`}
          >
            <span className="nav-bottom-link__icon">{link.icon}</span>
            <span className="nav-bottom-link__label">{link.label}</span>
          </Link>
        ))}
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

      {/* Ingestion Password Modal */}
      {showModal && (
        <div className={`ingestion-modal-overlay ${isFadingOut ? 'ingestion-modal-overlay--fade-out' : ''}`}>
          <div className="ingestion-modal">
            <h2 className="ingestion-modal__title">Database Sync</h2>
            <p className="ingestion-modal__desc">
              Trigger a full database refresh and scan. This will scrape the latest data from FuseSport.
            </p>
            <form onSubmit={handleSyncSubmit}>
              <input
                type="password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="ingestion-modal__input"
                autoFocus
                required
              />
              {syncError && <div className="ingestion-modal__error">⚠️ {syncError}</div>}
              {syncSuccess && <div className="ingestion-modal__success">✅ {syncSuccess}</div>}
              <div className="ingestion-modal__actions">
                <button 
                  type="button" 
                  className="btn btn--ghost" 
                  onClick={() => {
                    setShowModal(false)
                    setPassword('')
                    setSyncError('')
                    setSyncSuccess('')
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn--primary">
                  Start Sync
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
