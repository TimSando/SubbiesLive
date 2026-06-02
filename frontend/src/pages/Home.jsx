import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'
import { useRefZone } from './RefZone.jsx'
import { fetchAppointments } from '../api/refzone.js'
import AppointmentCard from '../components/RefZone/AppointmentCard.jsx'
import NotificationToggle from '../components/NotificationToggle/NotificationToggle.jsx'

function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric', month: 'short' })
}

function formatTime(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit' })
}

function GamePill({ game }) {
  const isCompleted = game.status === 'completed'
  const isLive = game.status === 'in_progress'
  const homeWin = isCompleted && game.home_score > game.away_score
  const awayWin = isCompleted && game.away_score > game.home_score
  const showScore = isCompleted || isLive

  return (
    <Link 
      to={`/games/${game.id}`} 
      className={`game-pill ${isLive ? 'game-pill--live' : ''}`} 
      id={`game-${game.id}`}
    >
      <div className="game-pill__meta">
        <span className="game-pill__comp">{game.competition_name}</span>
        <span className="game-pill__round">{game.round_name}</span>
      </div>
      <div className="game-pill__teams">
        <div className={`game-pill__team ${homeWin ? 'game-pill__team--winner' : ''}`}>
          <span className="game-pill__team-name">{game.home_team.club_name || game.home_team.name}</span>
          {showScore && (
            <span className={`game-pill__score ${homeWin ? 'game-pill__score--winner' : ''}`}>
              {game.home_score ?? 0}
            </span>
          )}
        </div>
        <div className={`game-pill__team ${awayWin ? 'game-pill__team--winner' : ''}`}>
          <span className="game-pill__team-name">{game.away_team.club_name || game.away_team.name}</span>
          {showScore && (
            <span className={`game-pill__score ${awayWin ? 'game-pill__score--winner' : ''}`}>
              {game.away_score ?? 0}
            </span>
          )}
        </div>
      </div>
      <div className="game-pill__footer">
        <span className="game-pill__date">
          {formatDate(game.game_date)} {!isCompleted && `at ${formatTime(game.game_date)}`}
        </span>
        {isLive ? (
          <span className="live-badge">
            <span className="live-dot" /> Live
          </span>
        ) : (
          <span className="game-pill__status">{game.status}</span>
        )}
      </div>
    </Link>
  )
}

export default function Home() {
  const [liveGames, setLiveGames] = useState([])
  const [loadingLive, setLoadingLive] = useState(true)
  const [isSubscribed, setIsSubscribed] = useState(true)

  useEffect(() => {
    if ('serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window) {
      navigator.serviceWorker.ready
        .then((registration) => registration.pushManager.getSubscription())
        .then((subscription) => {
          setIsSubscribed(!!subscription)
        })
        .catch((err) => {
          console.error('Error checking subscription in Home:', err)
          setIsSubscribed(false)
        })
    } else {
      setIsSubscribed(false)
    }
  }, [])

  const [isSyncing, setIsSyncing] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [password, setPassword] = useState('')
  const [syncError, setSyncError] = useState('')
  const [syncSuccess, setSyncSuccess] = useState('')
  const [isFadingOut, setIsFadingOut] = useState(false)

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

  const { data: recentGames, loading: loadingRecent } = useApi(
    () => api.getGames({ status: 'completed', limit: 6 }), []
  )
  const { data: upcomingGames, loading: loadingUpcoming } = useApi(
    () => api.getGames({ status: 'scheduled', limit: 6 }), []
  )
  const { data: overview, loading: loadingOverview } = useApi(
    () => api.getSeasonOverview(), []
  )

  // 60-second polling effect for live games
  useEffect(() => {
    async function fetchLive() {
      try {
        const data = await api.getLiveGames()
        setLiveGames(data || [])
      } catch (err) {
        console.error('Error fetching live games:', err)
      } finally {
        setLoadingLive(false)
      }
    }

    fetchLive()
    const interval = setInterval(fetchLive, 60000)
    return () => clearInterval(interval)
  }, [])

  // RefZone context and next appointment
  const auth = useRefZone()
  const [nextAppointment, setNextAppointment] = useState(null)

  useEffect(() => {
    if (auth.userId) {
      fetchAppointments(auth)
        .then(appointments => {
          const upcoming = (appointments || [])
            .filter(app => app.match?.moment > Date.now())
            .sort((a, b) => (a.match?.moment || 0) - (b.match?.moment || 0))
          setNextAppointment(upcoming[0] || null)
        })
        .catch(err => console.error('Error fetching appointments for home dashboard:', err))
    }
  }, [auth])

  // Favourite Club personalization
  const [favouriteClubId] = useState(() => localStorage.getItem('subbies_fav_club_id'))
  const { data: favClub } = useApi(
    () => favouriteClubId ? api.getClub(favouriteClubId) : Promise.resolve(null),
    [favouriteClubId]
  )

  const favTeamId = useMemo(() => {
    return favClub?.teams && favClub.teams.length > 0 ? favClub.teams[0].id : null
  }, [favClub])

  const { data: favClubGames } = useApi(
    () => favTeamId ? api.getGames({ team_id: favTeamId, limit: 1 }) : Promise.resolve(null),
    [favTeamId]
  )
  const favClubGame = favClubGames?.[0] || null

  // Premier Competition Standings
  const { data: competitions } = useApi(() => api.getCompetitions(), [])
  const kentwellId = useMemo(() => {
    return competitions?.find(c => c.name.includes('Kentwell'))?.id
  }, [competitions])

  const { data: premierStandings } = useApi(
    () => kentwellId ? api.getStandings(kentwellId) : Promise.resolve(null),
    [kentwellId]
  )

  return (
    <div className="page">
      <div className="container animate-in">
        {/* 1. Hero / Brand Strip */}
        <header className="home-hero">
          <h1 className="home-hero__title">
            Sydney Suburban<br />
            <span className="home-hero__accent">Rugby Union</span>
          </h1>
          <p className="home-hero__subtitle">
            Live standings, fixtures, and player statistics across all subbies competitions.
          </p>
        </header>

        {/* B. Smart Alerts Banner */}
        {!isSubscribed && (
          <div className="smart-alert-banner card animate-in">
            <div className="smart-alert-banner__text">
              <h3>Enable Alerts</h3>
              <p>Never miss a try! Enable live score alerts for your favourite clubs.</p>
            </div>
            <div className="smart-alert-banner__actions">
              <NotificationToggle onSubscriptionChange={setIsSubscribed} />
              <Link to="/notifications" className="btn btn--ghost" title="Manage Alert Settings">
                Manage Alerts
              </Link>
            </div>
          </div>
        )}

        {/* C. Context-Aware RefZone Widget */}
        {auth.userId && nextAppointment && (
          <>
            <hr className="home-section-divider" />
            <section className="home-section">
              <div className="game-strip-header">
                <h2>Your Next Appointment</h2>
              </div>
              <div style={{ maxWidth: '600px', margin: '0 auto' }}>
                <AppointmentCard appointment={nextAppointment} />
              </div>
            </section>
          </>
        )}

        {/* D. Favourite Club Dashboard */}
        {favouriteClubId && favClub && (
          <>
            <hr className="home-section-divider" />
            <section className="home-section">
              <div className="game-strip-header" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                {favClub.logo_url && (
                  <img 
                    src={favClub.logo_url} 
                    alt={favClub.name} 
                    style={{ width: '40px', height: '40px', objectFit: 'contain' }} 
                  />
                )}
                <h2>Favourite Club: {favClub.name}</h2>
              </div>
              {favClubGame ? (
                <div style={{ maxWidth: '400px' }}>
                  <GamePill game={favClubGame} />
                </div>
              ) : (
                <p style={{ color: 'var(--color-text-secondary)' }}>No recent or upcoming games scheduled for your favourite club.</p>
              )}
            </section>
          </>
        )}

        {/* E. Live Games Strip */}
        {liveGames.length > 0 && (
          <>
            <hr className="home-section-divider" />
            <section className="home-section animate-fade-in">
              <div className="game-strip-header">
                <h2 style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                  <span className="live-dot" /> Live Games
                </h2>
              </div>
              <div className="game-strip">
                {liveGames.map(game => (
                  <GamePill key={game.id} game={game} />
                ))}
              </div>
            </section>
          </>
        )}

        {/* F. Premier Ladder Snippet */}
        {premierStandings && premierStandings.length > 0 && (
          <>
            <hr className="home-section-divider" />
            <section className="home-section mini-ladder-section">
              <div className="game-strip-header">
                <h2>Kentwell Cup Standings</h2>
                <Link to={`/competitions/${kentwellId}`} className="btn btn--ghost">View Full Standings →</Link>
              </div>
              <div className="table-container">
                <table className="standings-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Team</th>
                      <th>P</th>
                      <th>W</th>
                      <th>L</th>
                      <th>Pts</th>
                    </tr>
                  </thead>
                  <tbody>
                    {premierStandings.slice(0, 5).map((row, index) => (
                      <tr key={row.club_id}>
                        <td>{index + 1}</td>
                        <td>
                          <Link to={`/clubs/${row.club_id}`} className="standings-team-link">
                            {row.club_name}
                          </Link>
                        </td>
                        <td>{row.played}</td>
                        <td>{row.won}</td>
                        <td>{row.lost}</td>
                        <td><strong>{row.competition_points}</strong></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}

        {/* G. Stat Leaders Teaser */}
        {overview && (
          <>
            <hr className="home-section-divider" />
            <section className="home-section">
              <div className="game-strip-header">
                <h2>Season Stat Leaders</h2>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
                <div className="stat-card stat-teaser-card">
                  <span className="stat-card__label">Top Points Scorer</span>
                  <span className="stat-teaser-card__name">{overview.top_scorer_name || 'N/A'}</span>
                  <span className="stat-card__value">{overview.top_scorer_points} pts</span>
                </div>
                <div className="stat-card stat-teaser-card">
                  <span className="stat-card__label">Top Try Scorer</span>
                  <span className="stat-teaser-card__name">{overview.top_try_scorer_name || 'N/A'}</span>
                  <span className="stat-card__value">{overview.top_try_scorer_tries} tries</span>
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <Link to="/stats" className="btn btn--ghost">View Full Leaderboards →</Link>
              </div>
            </section>
          </>
        )}

        {/* H. Recent & Upcoming Fixtures */}
        <hr className="home-section-divider" />
        <section className="home-section">
          <div className="game-strip-header">
            <h2>Recent Results</h2>
            <Link to="/competitions" className="btn btn--ghost">View All →</Link>
          </div>
          {loadingRecent ? (
            <div className="game-strip">
              {[1, 2, 3].map(i => (
                <div key={i} className="skeleton" style={{ width: '280px', height: '140px', flexShrink: 0, borderRadius: 'var(--radius-lg)' }} />
              ))}
            </div>
          ) : !recentGames || recentGames.length === 0 ? (
            <p style={{ color: 'var(--color-text-secondary)', padding: 'var(--space-4) 0' }}>No recent games found.</p>
          ) : (
            <div className="game-strip">
              {recentGames.map(game => (
                <GamePill key={game.id} game={game} />
              ))}
            </div>
          )}
        </section>

        <hr className="home-section-divider" />
        <section className="home-section">
          <div className="game-strip-header">
            <h2>Upcoming Fixtures</h2>
            <Link to="/competitions" className="btn btn--ghost">View All →</Link>
          </div>
          {loadingUpcoming ? (
            <div className="game-strip">
              {[1, 2, 3].map(i => (
                <div key={i} className="skeleton" style={{ width: '280px', height: '140px', flexShrink: 0, borderRadius: 'var(--radius-lg)' }} />
              ))}
            </div>
          ) : !upcomingGames || upcomingGames.length === 0 ? (
            <p style={{ color: 'var(--color-text-secondary)', padding: 'var(--space-4) 0' }}>No upcoming fixtures scheduled.</p>
          ) : (
            <div className="game-strip">
              {upcomingGames.map(game => (
                <GamePill key={game.id} game={game} />
              ))}
            </div>
          )}
        </section>

        <hr className="home-section-divider" />

        {/* 5. Quick Stats Row */}
        {overview && (
          <section className="home-stats" style={{ marginTop: 'var(--space-8)' }}>
            <div className="stat-card">
              <span className="stat-card__value">31</span>
              <span className="stat-card__label">Competitions</span>
            </div>
            <div className="stat-card">
              <span className="stat-card__value">{overview.club_count || 60}</span>
              <span className="stat-card__label">Clubs</span>
            </div>
            <div className="stat-card">
              <span className="stat-card__value">
                {overview.player_count > 0 ? overview.player_count.toLocaleString() : '3,800+'}
              </span>
              <span className="stat-card__label">Players</span>
            </div>
          </section>
        )}
      </div>

      {/* Floating Database Ingestion Trigger Button */}
      <div className="ingestion-trigger-container">
        <button 
          onClick={() => {
            if (!isSyncing) {
              setShowModal(true)
            }
          }}
          className={`ingestion-trigger-btn ${isSyncing ? 'ingestion-trigger-btn--syncing' : ''}`}
          title={isSyncing ? "Database syncing is in progress..." : "Trigger Manual Ingestion"}
          disabled={isSyncing}
        >
          <svg 
            viewBox="0 0 24 24" 
            width="20" 
            height="20" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round"
            className={isSyncing ? 'spin' : ''}
          >
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
          </svg>
        </button>
      </div>

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
