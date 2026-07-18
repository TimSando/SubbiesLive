import { useState, useEffect, useMemo, Fragment, useRef } from 'react'
import { api } from '../api/client.js'
import { Link } from 'react-router-dom'
import './Notifications.css'
import { formatDivisionName } from '../utils/format.js'

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/')

  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

export default function Notifications() {
  const [isSupported, setIsSupported] = useState(false)
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [loading, setLoading] = useState(true)
  
  const [mySubscriptions, setMySubscriptions] = useState([])
  const [clubs, setClubs] = useState([])
  const [competitions, setCompetitions] = useState([])
  
  const [selectedClubId, setSelectedClubId] = useState('')
  const [selectedCompId, setSelectedCompId] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [clubSearch, setClubSearch] = useState('')
  const [compSearch, setCompSearch] = useState('')

  const [clubDropdownOpen, setClubDropdownOpen] = useState(false)
  const [compDropdownOpen, setCompDropdownOpen] = useState(false)

  const clubSearchRef = useRef(null)
  const compSearchRef = useRef(null)

  // Click outside to close dropdowns
  useEffect(() => {
    function handleClickOutside(event) {
      if (clubSearchRef.current && !clubSearchRef.current.contains(event.target)) {
        setClubDropdownOpen(false)
      }
      if (compSearchRef.current && !compSearchRef.current.contains(event.target)) {
        setCompDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Filter and group clubs visually by parent competition and division
  const filteredClubs = useMemo(() => {
    return clubs
      .filter(club => club.team_count > 0)
      .filter(club => !mySubscriptions.some(sub => sub.topic_type === 'club' && sub.topic_id === club.id))
  }, [clubs, mySubscriptions])

  const groupedClubs = useMemo(() => {
    return filteredClubs
      .filter(club => club.name.toLowerCase().includes(clubSearch.toLowerCase()))
      .reduce((acc, club) => {
        const mapping = club.competition_mapping
        const parent = mapping?.parent_competition || 'Other'
        if (!acc[parent]) acc[parent] = { clubs: [], divisions: {} }
        
        const division = mapping?.division
        if (division) {
          if (!acc[parent].divisions[division]) acc[parent].divisions[division] = []
          acc[parent].divisions[division].push(club)
        } else {
          acc[parent].clubs.push(club)
        }
        return acc
      }, {})
  }, [filteredClubs, clubSearch])

  // Filter and group competitions visually by parent competition and division
  const filteredComps = useMemo(() => {
    return competitions.filter(comp => !mySubscriptions.some(sub => sub.topic_type === 'competition' && sub.topic_id === comp.id))
  }, [competitions, mySubscriptions])

  const groupedComps = useMemo(() => {
    return filteredComps
      .filter(comp => comp.name.toLowerCase().includes(compSearch.toLowerCase()))
      .reduce((acc, c) => {
        const parent = c.parent_competition || 'Other'
        if (!acc[parent]) acc[parent] = { competitions: [], divisions: {} }
        
        if (c.division) {
          if (!acc[parent].divisions[c.division]) acc[parent].divisions[c.division] = []
          acc[parent].divisions[c.division].push(c)
        } else {
          acc[parent].competitions.push(c)
        }
        return acc
      }, {})
  }, [filteredComps, compSearch])

  const subClubs = useMemo(() => mySubscriptions.filter(sub => sub.topic_type === 'club'), [mySubscriptions])
  const subComps = useMemo(() => mySubscriptions.filter(sub => sub.topic_type === 'competition'), [mySubscriptions])
  const subGames = useMemo(() => mySubscriptions.filter(sub => sub.topic_type === 'game'), [mySubscriptions])


  useEffect(() => {
    const supported =
      'serviceWorker' in navigator &&
      'PushManager' in window &&
      'Notification' in window
    setIsSupported(supported)

    if (supported) {
      checkDeviceSubscription()
    } else {
      setLoading(false)
    }
  }, [])

  const checkDeviceSubscription = async () => {
    try {
      const registration = await navigator.serviceWorker.ready
      let subscription = await registration.pushManager.getSubscription()

      const { publicKey } = await api.getVapidPublicKey()
      const serverKeyUint8 = urlBase64ToUint8Array(publicKey)

      if (subscription) {
        // Verify VAPID Key to handle key mismatch (e.g. server keys changed)
        const subKey = subscription.options.applicationServerKey
        let keyMismatch = false
        if (subKey) {
          const subKeyUint8 = new Uint8Array(subKey)
          if (
            subKeyUint8.length !== serverKeyUint8.length ||
            !subKeyUint8.every((val, i) => val === serverKeyUint8[i])
          ) {
            keyMismatch = true
          }
        } else {
          keyMismatch = true
        }

        if (keyMismatch) {
          console.warn(
            "VAPID key mismatch detected. Re-subscribing with the new server key..."
          )
          try {
            await subscription.unsubscribe()
            subscription = await registration.pushManager.subscribe({
              userVisibleOnly: true,
              applicationServerKey: serverKeyUint8,
            })
          } catch (subscribeErr) {
            console.error(
              "Failed to automatically re-subscribe after VAPID key mismatch:",
              subscribeErr
            )
            subscription = null
          }
        }
      }

      if (subscription) {
        // Always register/refresh the subscription with the backend
        try {
          await api.subscribeNotifications(subscription.toJSON())
        } catch (apiErr) {
          console.error("Failed to sync PWA subscription with server:", apiErr)
        }
        setIsSubscribed(true)
        await Promise.all([
          loadMySubscriptions(subscription.endpoint),
          loadClubsAndCompetitions(),
        ])
      } else {
        setIsSubscribed(false)
        await loadClubsAndCompetitions()
      }
    } catch (err) {
      console.error("Error loading push details:", err)
      try {
        await loadClubsAndCompetitions()
      } catch (e) {}
    } finally {
      setLoading(false)
    }
  }

  const loadMySubscriptions = async (endpoint) => {
    try {
      const res = await api.getMySubscriptions(endpoint)
      setMySubscriptions(res.subscriptions || [])
    } catch (err) {
      console.error('Error fetching topic subscriptions:', err)
    }
  }

  const loadClubsAndCompetitions = async () => {
    try {
      const currentYear = new Date().getFullYear()
      const [clubsRes, compsRes] = await Promise.all([
        api.getClubs({ year: currentYear }),
        api.getCompetitions({ year: currentYear })
      ])
      setClubs(clubsRes || [])
      setCompetitions(compsRes || [])
    } catch (err) {
      console.error('Error loading metadata lists:', err)
    }
  }

  const handleEnablePush = async () => {
    setActionLoading(true)
    try {
      const perm = await Notification.requestPermission()
      if (perm !== 'granted') {
        alert('Permission denied. Please enable system notifications in browser settings.')
        setActionLoading(false)
        return
      }

      const { publicKey } = await api.getVapidPublicKey()
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey)
      })

      await api.subscribeNotifications(subscription.toJSON())
      setIsSubscribed(true)
      
      // Load tables
      await Promise.all([
        loadMySubscriptions(subscription.endpoint),
        loadClubsAndCompetitions()
      ])
    } catch (err) {
      console.error('Failed to enable push:', err)
      alert('Failed to register device. Make sure you are running over localhost or HTTPS.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleSubscribeTopic = async (type, topicId) => {
    if (!topicId) return
    
    setActionLoading(true)
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      if (!subscription) return

      await api.toggleSubscriptionTopic({
        endpoint: subscription.endpoint,
        topic_type: type,
        topic_id: parseInt(topicId),
        subscribe: true,
        notify_outcome: true,
        notify_events: false
      })

      // Reload list
      await loadMySubscriptions(subscription.endpoint)
      
      // Reset inputs
      if (type === 'club') {
        setSelectedClubId('')
        setClubSearch('')
        setClubDropdownOpen(false)
      }
      if (type === 'competition') {
        setSelectedCompId('')
        setCompSearch('')
        setCompDropdownOpen(false)
      }
      
      // Dismiss mobile keyboard
      if (document.activeElement instanceof HTMLElement) {
        document.activeElement.blur()
      }
    } catch (err) {
      console.error('Error subscribing to topic:', err)
      alert('Failed to add subscription.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleToggleOption = async (subCard, optionName, checked) => {
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      if (!subscription) return

      const payload = {
        endpoint: subscription.endpoint,
        topic_type: subCard.topic_type,
        topic_id: subCard.topic_id,
        subscribe: true,
        notify_outcome: optionName === 'outcome' ? checked : subCard.notify_outcome,
        notify_events: optionName === 'events' ? checked : subCard.notify_events
      }

      await api.toggleSubscriptionTopic(payload)
      
      // Local optimistic update
      setMySubscriptions(prev => prev.map(item => {
        if (item.topic_type === subCard.topic_type && item.topic_id === subCard.topic_id) {
          return {
            ...item,
            notify_outcome: payload.notify_outcome,
            notify_events: payload.notify_events
          }
        }
        return item
      }))
    } catch (err) {
      console.error('Error toggling option:', err)
      alert('Failed to update option.')
    }
  }

  const handleUnsubscribe = async (subCard) => {
    if (!confirm(`Are you sure you want to stop receiving notifications for ${subCard.topic_name}?`)) return
    
    setActionLoading(true)
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      if (!subscription) return

      await api.toggleSubscriptionTopic({
        endpoint: subscription.endpoint,
        topic_type: subCard.topic_type,
        topic_id: subCard.topic_id,
        subscribe: false
      })

      setMySubscriptions(prev => prev.filter(item => 
        !(item.topic_type === subCard.topic_type && item.topic_id === subCard.topic_id)
      ))
    } catch (err) {
      console.error('Error unsubscribing:', err)
      alert('Failed to remove subscription.')
    } finally {
      setActionLoading(false)
    }
  }

  const renderSubCard = (sub) => (
    <article className="subscription-card" key={`${sub.topic_type}-${sub.topic_id}`}>
      <div className="subscription-card__info">
        <span className="subscription-card__name">{sub.topic_name}</span>
        <span className="subscription-card__type">{sub.topic_type === 'competition' ? 'division' : sub.topic_type}</span>
      </div>
      
      <div className="subscription-card__actions">
        <div className="subscription-card__options">
          <label className="subscription-card__option" htmlFor={`sub-${sub.topic_type}-${sub.topic_id}-outcome`}>
            <input 
              id={`sub-${sub.topic_type}-${sub.topic_id}-outcome`}
              type="checkbox" 
              checked={sub.notify_outcome} 
              onChange={(e) => handleToggleOption(sub, 'outcome', e.target.checked)}
              className="subscription-card__checkbox"
            />
            Game Outcome
          </label>
          <label className="subscription-card__option" htmlFor={`sub-${sub.topic_type}-${sub.topic_id}-events`}>
            <input 
              id={`sub-${sub.topic_type}-${sub.topic_id}-events`}
              type="checkbox" 
              checked={sub.notify_events} 
              onChange={(e) => handleToggleOption(sub, 'events', e.target.checked)}
              className="subscription-card__checkbox"
            />
            Live Events
          </label>
        </div>
        
        <button 
          className="subscription-card__delete-btn"
          onClick={() => handleUnsubscribe(sub)}
          disabled={actionLoading}
          title="Unsubscribe"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      </div>
    </article>
  )

  if (!isSupported) {
    return (
      <div className="page page--centered">
        <div className="container text-center" style={{ maxWidth: '500px' }}>
          <h2>Unsupported Browser</h2>
          <p style={{ color: 'var(--color-text-secondary)' }}>
            Push notifications are not supported by this browser. Please try using a modern browser like Chrome, Edge, or Safari on a mobile device or desktop.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="container animate-in notifications-container">
        <header className="notifications-header">
          <h1 className="notifications-header__title">Notifications</h1>
          <p className="notifications-header__desc">
            Manage your alerts for Sydney Suburban Rugby Union matches.
          </p>
        </header>

        {loading ? (
          <div className="skeleton" style={{ height: '200px', borderRadius: 'var(--radius-lg)' }} />
        ) : !isSubscribed ? (
          <section className="notifications-enable-card">
            <div className="notifications-enable-card__icon">🔔</div>
            <h2 className="notifications-enable-card__title">Enable Push Notifications</h2>
            <p className="notifications-enable-card__desc">
              Subscribe to matches, divisions, or clubs to get real-time score updates directly on your device.
            </p>
            <button 
              onClick={handleEnablePush} 
              disabled={actionLoading}
              className="btn btn--primary btn--lg"
            >
              {actionLoading ? 'Connecting...' : 'Allow Alerts on This Device'}
            </button>
          </section>
        ) : (
          <>
            {/* 1. Add Subscriptions Panel */}
            <section className="notifications-add-section">
              <h2 className="notifications-add-section__title">Add Alerts</h2>
              <div className="notifications-add-grid">
                {/* Clubs Combobox */}
                <div className="notifications-add-form" ref={clubSearchRef}>
                  <label className="notifications-add-label" htmlFor="club-search-input">Follow a Club</label>
                  <div className="search-select-input-wrapper">
                    <input
                      id="club-search-input"
                      type="text"
                      placeholder="Choose a Club..."
                      value={clubSearch}
                      onChange={(e) => {
                        setClubSearch(e.target.value)
                        setClubDropdownOpen(true)
                      }}
                      onFocus={() => setClubDropdownOpen(true)}
                      className="notifications-search-input"
                      disabled={actionLoading}
                      autoComplete="off"
                    />
                    <span className="search-select-arrow" onClick={() => setClubDropdownOpen(!clubDropdownOpen)}>▼</span>
                  </div>
                  {clubDropdownOpen && (
                    <div className="search-select-dropdown">
                      {Object.keys(groupedClubs).length === 0 ? (
                        <div className="search-select-option search-select-option--disabled">No matching clubs found</div>
                      ) : (
                        Object.entries(groupedClubs).map(([parent, data]) => (
                          <Fragment key={parent}>
                            <div className="search-select-group-header">{parent}</div>
                            
                            {/* Divisions */}
                            {Object.entries(data.divisions).sort().map(([div, clubsList]) => (
                              <Fragment key={`${parent}-${div}`}>
                                <div className="search-select-subgroup-header">{formatDivisionName(div)}</div>
                                {clubsList.map(club => (
                                  <div
                                    key={club.id}
                                    className="search-select-option"
                                    onPointerDown={(e) => e.preventDefault()}
                                    onClick={() => handleSubscribeTopic('club', club.id)}
                                  >
                                    {club.name}
                                  </div>
                                ))}
                              </Fragment>
                            ))}

                            {/* Clubs without division */}
                            {data.clubs.map(club => (
                              <div
                                key={club.id}
                                className="search-select-option"
                                onPointerDown={(e) => e.preventDefault()}
                                onClick={() => handleSubscribeTopic('club', club.id)}
                              >
                                {club.name}
                              </div>
                            ))}
                          </Fragment>
                        ))
                      )}
                    </div>
                  )}
                </div>

                {/* Competitions Combobox */}
                <div className="notifications-add-form" ref={compSearchRef}>
                  <label className="notifications-add-label" htmlFor="comp-search-input">Follow a Division</label>
                  <div className="search-select-input-wrapper">
                    <input
                      id="comp-search-input"
                      type="text"
                      placeholder="Choose a Division..."
                      value={compSearch}
                      onChange={(e) => {
                        setCompSearch(e.target.value)
                        setCompDropdownOpen(true)
                      }}
                      onFocus={() => setCompDropdownOpen(true)}
                      className="notifications-search-input"
                      disabled={actionLoading}
                      autoComplete="off"
                    />
                    <span className="search-select-arrow" onClick={() => setCompDropdownOpen(!compDropdownOpen)}>▼</span>
                  </div>
                  {compDropdownOpen && (
                    <div className="search-select-dropdown">
                      {Object.keys(groupedComps).length === 0 ? (
                        <div className="search-select-option search-select-option--disabled">No matching divisions found</div>
                      ) : (
                        Object.entries(groupedComps).map(([parent, data]) => (
                          <Fragment key={parent}>
                            <div className="search-select-group-header">{parent}</div>
                            
                            {/* Divisions */}
                            {Object.entries(data.divisions).sort().map(([div, comps]) => (
                              <Fragment key={`${parent}-${div}`}>
                                <div className="search-select-subgroup-header">{formatDivisionName(div)}</div>
                                {comps.map(c => (
                                  <div
                                    key={c.id}
                                    className="search-select-option"
                                    onPointerDown={(e) => e.preventDefault()}
                                    onClick={() => handleSubscribeTopic('competition', c.id)}
                                  >
                                    {c.name}
                                  </div>
                                ))}
                              </Fragment>
                            ))}

                            {/* Competitions without division */}
                            {data.competitions.map(c => (
                              <div
                                key={c.id}
                                className="search-select-option"
                                onPointerDown={(e) => e.preventDefault()}
                                onClick={() => handleSubscribeTopic('competition', c.id)}
                              >
                                {c.name}
                              </div>
                            ))}
                          </Fragment>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>
          
          <div style={{ 
            marginTop: 'var(--space-4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 'var(--space-4)'
          }}>
            <p className="notifications-tip" style={{ 
              fontSize: 'var(--font-size-sm)', 
              color: 'var(--color-text-secondary)', 
              display: 'flex', 
              alignItems: 'center', 
              gap: 'var(--space-2)', 
              opacity: 0.8,
              margin: 0
            }}>
              💡 <strong>Tip:</strong> You can also follow specific matches by selecting the notification bell icon (🔔) on the Game details page.
            </p>
            <Link to="/competitions" className="btn btn--ghost" style={{ border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '8px', padding: '8px 16px', fontWeight: 600 }}>
              View Competitions
            </Link>
          </div>
            </section>

            {/* 2. Active Subscriptions List */}
            <section>
              <h2 className="subscriptions-list-title">Your Subscriptions</h2>
              {mySubscriptions.length === 0 ? (
                <p style={{ color: 'var(--color-text-secondary)' }}>
                  You are not currently subscribed to any alerts. Choose a club or division above to start!
                </p>
              ) : (
                <div className="subscriptions-grouped-container" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
                  {subClubs.length > 0 && (
                    <div className="subscription-group">
                      <h3 className="subscription-group-title" style={{ fontSize: 'var(--font-size-md)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Clubs</h3>
                      <div className="subscriptions-list">
                        {subClubs.map(sub => renderSubCard(sub))}
                      </div>
                    </div>
                  )}

                  {subComps.length > 0 && (
                    <div className="subscription-group">
                      <h3 className="subscription-group-title" style={{ fontSize: 'var(--font-size-md)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Competitions</h3>
                      <div className="subscriptions-list">
                        {subComps.map(sub => renderSubCard(sub))}
                      </div>
                    </div>
                  )}

                  {subGames.length > 0 && (
                    <div className="subscription-group">
                      <h3 className="subscription-group-title" style={{ fontSize: 'var(--font-size-md)', color: 'var(--color-text-secondary)', marginBottom: 'var(--space-2)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Matches</h3>
                      <div className="subscriptions-list">
                        {subGames.map(sub => renderSubCard(sub))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  )
}
