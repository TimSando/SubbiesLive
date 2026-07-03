import { useRegisterSW } from 'virtual:pwa-register/react'
import './ReloadPrompt.css'

export default function ReloadPrompt() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegistered(r) {
      console.log('PWA Service Worker registered:', r)
    },
    onRegisterError(error) {
      console.error('PWA Service Worker registration error:', error)
    }
  })

  const close = () => setNeedRefresh(false)

  if (!needRefresh) return null

  return (
    <div className="pwa-toast animate-in" id="pwa-update-toast">
      <div className="pwa-toast__message">
        <span className="pwa-toast__icon">✨</span>
        <div>
          <h4 className="pwa-toast__title">Update Available</h4>
          <p className="pwa-toast__description">A new version of Subbies Live is ready.</p>
        </div>
      </div>
      <div className="pwa-toast__actions">
        <button 
          className="btn btn--primary btn--sm" 
          onClick={() => updateServiceWorker(true)}
          id="pwa-update-reload-button"
        >
          Reload
        </button>
        <button 
          className="btn btn--ghost btn--sm" 
          onClick={close}
          id="pwa-update-close-button"
        >
          Dismiss
        </button>
      </div>
    </div>
  )
}
