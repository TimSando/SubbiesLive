import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'
import { useRefZone } from './RefZone.jsx'
import { fetchAppointments } from '../api/refzone.js'
import AppointmentCard from '../components/RefZone/AppointmentCard.jsx'
import GamePill from '../components/GamePill/GamePill.jsx'

export default function Home() {
  const [followingClubs, setFollowingClubs] = useState(() => {
    const existing = JSON.parse(localStorage.getItem('subbies_following_clubs') || '[]')
    if (existing.length > 0) return existing

    // Migrate legacy single-favourite
    const legacyId = localStorage.getItem('subbies_fav_club_id')
    if (legacyId) {
      // We'll populate the full club data asynchronously; for now store just the ID
      return [{ id: parseInt(legacyId, 10), name: null, logo_url: null }]
    }
    return []
  })

  // Asynchronously backfill club names and logos if migrated from legacyFavouriteClubId
  useEffect(() => {
    const needsBackfill = followingClubs.some(c => c.name === null)
    if (needsBackfill) {
      Promise.all(
        followingClubs.map(async (club) => {
          if (club.name === null) {
            try {
               const fullClub = await api.getClub(club.id)
               return { id: club.id, name: fullClub.name, logo_url: fullClub.logo_url }
            } catch (err) {
               console.error(`Failed to backfill club ${club.id}:`, err)
               return { id: club.id, name: `Club ${club.id}`, logo_url: null }
            }
          }
          return club
        })
      ).then(updatedClubs => {
        localStorage.setItem('subbies_following_clubs', JSON.stringify(updatedClubs))
        setFollowingClubs(updatedClubs)
        // Clean up legacy fav club
        localStorage.removeItem('subbies_fav_club_id')
      })
    }
  }, [followingClubs])

  const [activeTab, setActiveTab] = useState(
    followingClubs.length > 0 ? followingClubs[0].id : null
  )
  const [isRefDismissed, setIsRefDismissed] = useState(
    () => localStorage.getItem('refzone_prompt_dismissed') === 'true'
  )



  // React to follow status updates from ClubDetail page
  useEffect(() => {
    const handleFollowUpdate = () => {
      const updated = JSON.parse(localStorage.getItem('subbies_following_clubs') || '[]')
      setFollowingClubs(updated)
      if (updated.length > 0) {
        if (!updated.some(c => c.id === activeTab)) {
          setActiveTab(updated[0].id)
        }
      } else {
        setActiveTab(null)
      }
    }
    window.addEventListener('followingUpdated', handleFollowUpdate)
    return () => window.removeEventListener('followingUpdated', handleFollowUpdate)
  }, [activeTab])



  // Data Fetching for Active Tab
  const { data: activeTabLiveGames, loading: loadingLive } = useApi(
    () => activeTab ? api.getGames({ club_id: activeTab, status: 'in_progress', limit: 10 }) : Promise.resolve([]),
    [activeTab]
  )
  const { data: activeTabRecentGames, loading: loadingRecent } = useApi(
    () => activeTab ? api.getGames({ club_id: activeTab, status: 'completed', limit: 6 }) : Promise.resolve([]),
    [activeTab]
  )
  const { data: activeTabUpcomingGames, loading: loadingUpcoming } = useApi(
    () => activeTab ? api.getGames({ club_id: activeTab, status: 'scheduled', limit: 6 }) : Promise.resolve([]),
    [activeTab]
  )

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

        {/* RefZone Section */}
        {auth.userId ? (
          <section className="home-section animate-fade-in">
            <div className="game-strip-header">
              <h2>Your Next Referee Appointment</h2>
              <Link to="/refzone" className="btn btn--ghost">View RefZone →</Link>
            </div>
            <div style={{ maxWidth: '600px', margin: '0 auto' }}>
              {nextAppointment ? (
                <AppointmentCard appointment={nextAppointment} />
              ) : (
                <p style={{ color: 'var(--color-text-muted)', textAlign: 'center', padding: 'var(--space-6)' }}>
                  No upcoming referee appointments found.
                </p>
              )}
            </div>
            <hr className="home-section-divider" style={{ marginTop: 'var(--space-8)', marginBottom: '0' }} />
          </section>
        ) : (
          !isRefDismissed && (
            <section className="home-section animate-fade-in">
              <div className="card refzone-prompt-card" style={{ padding: 'var(--space-6)', position: 'relative' }}>
                <button
                  onClick={() => {
                    localStorage.setItem('refzone_prompt_dismissed', 'true')
                    setIsRefDismissed(true)
                  }}
                  style={{
                    position: 'absolute',
                    top: 'var(--space-4)',
                    right: 'var(--space-4)',
                    background: 'none',
                    border: 'none',
                    color: 'var(--color-text-muted)',
                    cursor: 'pointer',
                    fontSize: '1.2rem',
                  }}
                  title="Dismiss prompt"
                >
                  ✕
                </button>
                <h3 style={{ marginBottom: 'var(--space-2)' }}>Referee Hub</h3>
                <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-4)', fontSize: 'var(--font-size-sm)' }}>
                  Sign in to RugbyXplorer to see your upcoming referee appointments and manage match preparation.
                </p>
                <Link to="/refzone" className="btn btn--primary">
                  Sign in to RefZone
                </Link>
              </div>
              <hr className="home-section-divider" style={{ marginTop: 'var(--space-8)', marginBottom: '0' }} />
            </section>
          )
        )}

        {/* Following Section */}
        <section className="home-section">
          {followingClubs.length === 0 ? (
            <div className="card" style={{ padding: 'var(--space-8)', textAlign: 'center', marginTop: 'var(--space-4)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-4)' }}>
              <span style={{ fontSize: '3rem' }}>⭐</span>
              <h2>Personalize Your Dashboard</h2>
              <p style={{ color: 'var(--color-text-secondary)', maxWidth: '500px', margin: '0 auto' }}>
                Follow your favourite clubs to get quick access to their live games, recent results, and upcoming fixtures right here.
              </p>
              <Link to="/clubs" className="btn btn--primary">
                Browse Clubs
              </Link>
            </div>
          ) : (
            <>
              <div className="tab-bar">
                {followingClubs.map(club => (
                  <button
                    key={club.id}
                    className={`tab-bar__tab ${activeTab === club.id ? 'tab-bar__tab--active' : ''}`}
                    onClick={() => setActiveTab(club.id)}
                    style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}
                  >
                    {club.logo_url && (
                      <img src={club.logo_url} alt="" style={{ width: '20px', height: '20px', objectFit: 'contain' }} />
                    )}
                    <span>{club.name || `Club ${club.id}`}</span>
                  </button>
                ))}
              </div>

              {/* Sub-sections for selected club */}
              {activeTab && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
                  
                  {/* Live Games */}
                  <div>
                    <div className="section-subtitle">Live Games</div>
                    {loadingLive ? (
                      <div className="game-strip">
                        <div className="skeleton" style={{ width: '280px', height: '140px', borderRadius: 'var(--radius-lg)' }} />
                      </div>
                    ) : activeTabLiveGames && activeTabLiveGames.length > 0 ? (
                      <div className="game-strip">
                        {activeTabLiveGames.map(game => (
                          <GamePill key={game.id} game={game} />
                        ))}
                      </div>
                    ) : (
                      <div className="empty-state-banner">
                        <p>No live matches right now for this club.</p>
                        <Link to="/live" className="btn btn--ghost" style={{ padding: 'var(--space-1) var(--space-3)', fontSize: 'var(--font-size-xs)' }}>
                          View All Live Matches →
                        </Link>
                      </div>
                    )}
                  </div>

                  {/* Recent Results */}
                  <div>
                    <div className="section-subtitle">Recent Results</div>
                    {loadingRecent ? (
                      <div className="game-strip">
                        {[1, 2].map(i => (
                          <div key={i} className="skeleton" style={{ width: '280px', height: '140px', flexShrink: 0, borderRadius: 'var(--radius-lg)' }} />
                        ))}
                      </div>
                    ) : activeTabRecentGames && activeTabRecentGames.length > 0 ? (
                      <div className="game-strip">
                        {activeTabRecentGames.map(game => (
                          <GamePill key={game.id} game={game} />
                        ))}
                      </div>
                    ) : (
                      <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', margin: 'var(--space-2) 0' }}>
                        No recent results found.
                      </p>
                    )}
                  </div>

                  {/* Upcoming Fixtures */}
                  <div>
                    <div className="section-subtitle">Upcoming Fixtures</div>
                    {loadingUpcoming ? (
                      <div className="game-strip">
                        {[1, 2].map(i => (
                          <div key={i} className="skeleton" style={{ width: '280px', height: '140px', flexShrink: 0, borderRadius: 'var(--radius-lg)' }} />
                        ))}
                      </div>
                    ) : activeTabUpcomingGames && activeTabUpcomingGames.length > 0 ? (
                      <div className="game-strip">
                        {activeTabUpcomingGames.map(game => (
                          <GamePill key={game.id} game={game} />
                        ))}
                      </div>
                    ) : (
                      <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', margin: 'var(--space-2) 0' }}>
                        No upcoming fixtures scheduled.
                      </p>
                    )}
                  </div>

                </div>
              )}
            </>
          )}
        </section>
      </div>


    </div>
  )
}
