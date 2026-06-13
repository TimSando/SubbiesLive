import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'
import PageSubscribeButton from '../components/NotificationToggle/PageSubscribeButton.jsx'

export default function ClubDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: club, loading } = useApi(() => api.getClub(id), [id])

  const [isFollowing, setIsFollowing] = useState(false)

  useEffect(() => {
    if (club) {
      const clubs = JSON.parse(localStorage.getItem('subbies_following_clubs') || '[]')
      setIsFollowing(clubs.some(c => c.id === club.id))
    }
  }, [club])

  function toggleFollow() {
    if (!club) return
    const clubs = JSON.parse(localStorage.getItem('subbies_following_clubs') || '[]')
    let updated
    if (isFollowing) {
      updated = clubs.filter(c => c.id !== club.id)
    } else {
      updated = [...clubs, { id: club.id, name: club.name, logo_url: club.logo_url }]
    }
    localStorage.setItem('subbies_following_clubs', JSON.stringify(updated))
    setIsFollowing(!isFollowing)
    window.dispatchEvent(new Event('followingUpdated'))
  }

  if (loading) {
    return (
      <div className="page">
        <div className="container" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', marginTop: 'var(--space-6)' }}>
          <div className="skeleton" style={{ height: '40px', width: '250px' }} />
          <div className="club-dashboard">
            <div className="skeleton" style={{ height: '550px', borderRadius: 'var(--radius-xl)' }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
              <div className="skeleton" style={{ height: '140px', borderRadius: 'var(--radius-xl)' }} />
              <div className="skeleton" style={{ height: '240px', borderRadius: 'var(--radius-xl)' }} />
              <div className="skeleton" style={{ height: '240px', borderRadius: 'var(--radius-xl)' }} />
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!club) {
    return (
      <div className="page">
        <div className="container" style={{ textAlign: 'center', paddingTop: 'var(--space-12)' }}>
          <h1 style={{ marginBottom: 'var(--space-4)' }}>Club not found</h1>
          <p style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-6)' }}>
            We couldn't locate the rugby club you are looking for.
          </p>
          <Link to="/competitions" className="btn btn--primary" onClick={(e) => { e.preventDefault(); navigate(-1); }}>← Back</Link>
        </div>
      </div>
    )
  }

  // Formatting date for fixtures
  const formatFixtureDate = (dateStr) => {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric', month: 'short' })
  }

  // Formatting time for fixtures
  const formatFixtureTime = (dateStr) => {
    const d = new Date(dateStr)
    return d.toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit', hour12: true }).toUpperCase()
  }

  // Win/Loss/Draw highlight logic for our club in fixtures
  const getGameOutcome = (game) => {
    if (game.status === 'in_progress') return 'in_progress'
    if (game.status === 'not_completed') return 'not_completed'
    if (game.status !== 'completed' || game.home_score === null || game.away_score === null) return 'scheduled'
    const isHome = game.home_team.club_id === club.id
    const ourScore = isHome ? game.home_score : game.away_score
    const oppScore = isHome ? game.away_score : game.home_score
    if (ourScore > oppScore) return 'win'
    if (ourScore < oppScore) return 'loss'
    return 'draw'
  }

  return (
    <div className="page">
      <div className="container animate-in" style={{ maxWidth: '1280px' }}>
        <Link to="/competitions" className="breadcrumb" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', marginBottom: 'var(--space-6)' }} onClick={(e) => { e.preventDefault(); navigate(-1); }}>
          ← Back
        </Link>

        {/* Dashboard Grid Container */}
        <div className="club-dashboard">
          
          {/* LEFT COLUMN: CLUB METADATA & ABOUT CARD */}
          <aside style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
            <div className="card" style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              textAlign: 'center',
              position: 'relative',
              overflow: 'hidden',
              padding: 'var(--space-8) var(--space-6) var(--space-6)'
            }}>
              {/* Top ambient green accent bar */}
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '4px',
                background: 'linear-gradient(90deg, transparent, var(--color-accent-primary), transparent)'
              }} />

              {/* Logo / Placeholder */}
              {club.logo_url ? (
                <img 
                  src={club.logo_url} 
                  alt={`${club.name} logo`} 
                  style={{
                    width: '96px',
                    height: '96px',
                    objectFit: 'contain',
                    borderRadius: 'var(--radius-xl)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    padding: 'var(--space-3)',
                    marginBottom: 'var(--space-4)',
                    boxShadow: 'var(--shadow-md)',
                    border: '1px solid var(--color-border)'
                  }} 
                  onError={(e) => { e.target.style.display = 'none' }}
                />
              ) : (
                <div style={{
                  width: '96px',
                  height: '96px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '3rem',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-xl)',
                  marginBottom: 'var(--space-4)',
                  color: 'var(--color-text-accent)',
                  fontWeight: 'bold'
                }}>
                  🏉
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-1)' }}>
                <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-extrabold)', color: 'var(--color-text-primary)', margin: 0 }}>
                  {club.name}
                </h1>
                <PageSubscribeButton topicType="club" topicId={club.id} topicName={club.name} />
                <button
                  onClick={toggleFollow}
                  title={isFollowing ? 'Unfollow club' : 'Follow club'}
                  className={`page-subscribe-btn ${isFollowing ? 'page-subscribe-btn--active' : ''}`}
                >
                  <svg
                    viewBox="0 0 24 24"
                    width="18"
                    height="18"
                    fill={isFollowing ? 'currentColor' : 'none'}
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                  </svg>
                </button>
              </div>

              {club.division_info && (
                <span className="badge" style={{ marginTop: 'var(--space-2)', marginBottom: 'var(--space-5)', fontSize: 'var(--font-size-xs)' }}>
                  {club.division_info}
                </span>
              )}

              {/* High Contrast sleek button above the About Section */}
              {club.website_url && (
                <a 
                  href={club.website_url} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="btn btn--primary" 
                  style={{
                    width: '100%',
                    marginBottom: (club.facebook_url || club.instagram_url || club.tiktok_url) ? 'var(--space-4)' : 'var(--space-6)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 'var(--space-2)',
                    boxShadow: '0 4px 12px rgba(34, 197, 94, 0.2)'
                  }}
                >
                  <span>🔗 Visit Club Website</span>
                </a>
              )}

              {/* Sleek, Premium Glassmorphic Social Media Bar */}
              {(club.facebook_url || club.instagram_url || club.tiktok_url) && (
                <div style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  gap: 'var(--space-4)',
                  width: '100%',
                  marginBottom: 'var(--space-6)',
                  paddingTop: '2px'
                }}>
                  {club.facebook_url && (
                    <a 
                      href={club.facebook_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      title="Facebook"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#1877F2',
                        fontSize: '1.2rem',
                        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                        boxShadow: 'var(--shadow-sm)'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'scale(1.15) translateY(-3px)'
                        e.currentTarget.style.background = 'rgba(24, 119, 242, 0.15)'
                        e.currentTarget.style.borderColor = 'rgba(24, 119, 242, 0.4)'
                        e.currentTarget.style.boxShadow = '0 6px 16px rgba(24, 119, 242, 0.3)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'none'
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                        e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
                      }}
                    >
                      <svg width="20" height="20" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M22 12c0-5.52-4.48-10-10-10S2 6.48 2 12c0 4.84 3.44 8.87 8 9.8V15H8v-3h2V9.5C10 7.57 11.57 6 13.5 6H16v3h-2c-.55 0-1 .45-1 1v2h3v3h-3v6.95c4.56-.93 8-4.96 8-9.75z"/>
                      </svg>
                    </a>
                  )}

                  {club.instagram_url && (
                    <a 
                      href={club.instagram_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      title="Instagram"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#E4405F',
                        fontSize: '1.2rem',
                        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                        boxShadow: 'var(--shadow-sm)'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'scale(1.15) translateY(-3px)'
                        e.currentTarget.style.background = 'rgba(228, 64, 95, 0.15)'
                        e.currentTarget.style.borderColor = 'rgba(228, 64, 95, 0.4)'
                        e.currentTarget.style.boxShadow = '0 6px 16px rgba(228, 64, 95, 0.3)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'none'
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                        e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
                      }}
                    >
                      <svg width="20" height="20" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.051.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/>
                      </svg>
                    </a>
                  )}

                  {club.tiktok_url && (
                    <a 
                      href={club.tiktok_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      title="TikTok"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '40px',
                        height: '40px',
                        borderRadius: '50%',
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        color: '#FE2C55',
                        fontSize: '1.2rem',
                        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                        boxShadow: 'var(--shadow-sm)'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'scale(1.15) translateY(-3px)'
                        e.currentTarget.style.background = 'rgba(254, 44, 85, 0.15)'
                        e.currentTarget.style.borderColor = 'rgba(254, 44, 85, 0.4)'
                        e.currentTarget.style.boxShadow = '0 6px 16px rgba(254, 44, 85, 0.3)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'none'
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                        e.currentTarget.style.boxShadow = 'var(--shadow-sm)'
                      }}
                    >
                      <svg width="18" height="18" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.02 1.59 4.18.94 1.13 2.26 1.86 3.69 2.05v3.91c-.9-.05-1.79-.27-2.62-.64-.81-.36-1.54-.88-2.13-1.54v6.86c0 1.25-.26 2.49-.78 3.63-.52 1.13-1.28 2.12-2.22 2.9-.96.79-2.09 1.36-3.3 1.68-1.25.33-2.56.36-3.83.08-1.25-.27-2.43-.88-3.41-1.78-1-.9-1.71-2.07-2.09-3.36-.38-1.29-.4-2.66-.07-3.95.33-1.26.99-2.41 1.93-3.32.96-.92 2.16-1.54 3.46-1.79.88-.17 1.79-.18 2.67-.02v3.96c-.46-.09-.93-.11-1.39-.07-.46.04-.9.2-1.3.44-.39.24-.71.58-.92.98-.22.4-.33.86-.33 1.32 0 .46.11.92.33 1.32.21.4.53.74.92.98.39.24.84.4 1.3.44.46.04.93.02 1.39-.07.45-.09.87-.29 1.22-.58.38-.32.67-.74.83-1.21.18-.51.27-1.05.27-1.59V.02z"/>
                      </svg>
                    </a>
                  )}
                </div>
              )}

              {/* About Section */}
              <div style={{ textAlign: 'left', width: '100%', borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-4)' }}>
                <h3 style={{ fontSize: 'var(--font-size-xs)', textTransform: 'uppercase', color: 'var(--color-text-muted)', letterSpacing: '0.08em', marginBottom: 'var(--space-2)', fontWeight: 'var(--font-weight-bold)' }}>
                  About the Club
                </h3>
                <p style={{
                  fontSize: 'var(--font-size-sm)',
                  color: 'var(--color-text-secondary)',
                  lineHeight: 'var(--line-height-relaxed)',
                  marginBottom: 'var(--space-4)'
                }}>
                  {club.about_text || `Proud community rugby union club fielding senior and junior teams in the local Sydney Suburban Rugby competitions.`}
                </p>
              </div>

              {/* Quick Info Grid */}
              <div style={{ textAlign: 'left', width: '100%', borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-4)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                {club.training_info && (
                  <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'flex-start' }}>
                    <span style={{ fontSize: '1.2rem', filter: 'grayscale(30%)' }}>⏱</span>
                    <div>
                      <h4 style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Training Schedule</h4>
                      <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', marginTop: '2px' }}>{club.training_info}</p>
                    </div>
                  </div>
                )}

                <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'flex-start' }}>
                  <span style={{ fontSize: '1.2rem', filter: 'grayscale(30%)' }}>🚺</span>
                  <div>
                    <h4 style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Women's Rugby</h4>
                    <p style={{ fontSize: 'var(--font-size-sm)', marginTop: '4px', lineHeight: '1' }}>
                      {club.has_womens_team ? '✅' : '❌'}
                    </p>
                  </div>
                </div>

                {club.home_ground_name && (
                  <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'flex-start' }}>
                    <span style={{ fontSize: '1.2rem', filter: 'grayscale(30%)' }}>📍</span>
                    <div style={{ width: '100%' }}>
                      <h4 style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Home Ground</h4>
                      <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)', fontWeight: 'var(--font-weight-medium)', marginTop: '2px' }}>
                        {club.home_ground_name}
                      </p>
                      {club.home_ground_map_url && (
                        <a 
                          href={club.home_ground_map_url} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          style={{
                            fontSize: 'var(--font-size-xs)',
                            color: 'var(--color-text-accent)',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontWeight: 'var(--font-weight-semibold)',
                            marginTop: '4px'
                          }}
                        >
                          Navigate on Google Maps 🗺
                        </a>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </aside>

          {/* RIGHT COLUMN: ACTIVE TEAMS & HORIZONTAL SCROLL MATCH CAROUSELS */}
          <main style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)', overflow: 'hidden' }}>
            
            {/* 1. TEAMS SECTION */}
            <section>
              <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', marginBottom: 'var(--space-4)', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <span>🏉</span> Active Grade Teams
              </h2>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
                gap: 'var(--space-4)'
              }}>
                {club.teams?.map(team => {
                  const totalGames = (team.wins || 0) + (team.losses || 0) + (team.draws || 0)
                  return (
                    <div key={team.id} className="card" style={{
                      padding: 'var(--space-4) var(--space-5)',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      minHeight: '120px',
                      background: 'rgba(17, 24, 39, 0.4)'
                    }}>
                      <div>
                        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-accent)', fontWeight: 'var(--font-weight-semibold)', display: 'block', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '2px' }}>
                          {team.competition_name}
                        </span>
                        <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-text-primary)' }}>
                          {team.name}
                        </h3>
                      </div>
                      
                      {/* Record Badge Pill */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'var(--space-4)', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 'var(--space-3)' }}>
                        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                          {totalGames} games played
                        </span>
                        <span className="badge" style={{
                          background: 'rgba(255, 255, 255, 0.02)',
                          borderColor: 'var(--color-border)',
                          color: 'var(--color-text-primary)',
                          fontVariantNumeric: 'tabular-nums',
                          padding: 'var(--space-1) var(--space-2)'
                        }}>
                          <strong style={{ color: 'var(--color-win)' }}>{team.wins || 0}W</strong>
                          <span style={{ color: 'var(--color-text-muted)', margin: '0 3px' }}>-</span>
                          <strong style={{ color: 'var(--color-loss)' }}>{team.losses || 0}L</strong>
                          <span style={{ color: 'var(--color-text-muted)', margin: '0 3px' }}>-</span>
                          <strong style={{ color: 'var(--color-draw)' }}>{team.draws || 0}D</strong>
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>

            {/* 2. RECENT RESULTS CAROUSEL */}
            <section>
              <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', marginBottom: 'var(--space-4)', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <span>✅</span> Recent Results
              </h2>
              {club.recent_fixtures && club.recent_fixtures.length > 0 ? (
                <div style={{
                  display: 'flex',
                  flexDirection: 'row',
                  gap: 'var(--space-4)',
                  overflowX: 'auto',
                  paddingBottom: 'var(--space-4)',
                  scrollbarWidth: 'thin',
                  WebkitOverflowScrolling: 'touch'
                }}>
                  {club.recent_fixtures.map(game => {
                    const outcome = getGameOutcome(game)
                    const isWin = outcome === 'win'
                    const isLoss = outcome === 'loss'
                    const outcomeColor = isWin ? 'var(--color-win)' : isLoss ? 'var(--color-loss)' : 'var(--color-draw)'
                    const outcomeLabel = isWin ? 'W' : isLoss ? 'L' : 'D'

                    return (
                      <Link 
                        to={`/games/${game.id}`} 
                        key={game.id} 
                        className="card" 
                        style={{
                          flex: '0 0 290px',
                          padding: 'var(--space-4)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 'var(--space-3)',
                          textDecoration: 'none',
                          color: 'inherit',
                          borderLeft: `3px solid ${outcomeColor}`,
                          background: 'rgba(17, 24, 39, 0.4)'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                            {game.round_name}
                          </span>
                          <span className="badge" style={{
                            background: `rgba(${isWin ? '34, 197, 94' : isLoss ? '239, 68, 68' : '245, 158, 11'}, 0.15)`,
                            color: outcomeColor,
                            borderColor: `rgba(${isWin ? '34, 197, 94' : isLoss ? '239, 68, 68' : '245, 158, 11'}, 0.25)`,
                            padding: '2px var(--space-2)'
                          }}>
                            {outcomeLabel}
                          </span>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ 
                              fontSize: 'var(--font-size-sm)', 
                              fontWeight: game.home_team.club_id === club.id ? 'var(--font-weight-bold)' : 'var(--font-weight-medium)',
                              color: game.home_team.club_id === club.id ? 'var(--color-text-accent)' : 'var(--color-text-primary)',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              maxWidth: '180px'
                            }}>
                              {game.home_team.name}
                            </span>
                            <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-bold)', color: game.home_team.club_id === club.id ? 'var(--color-text-accent)' : 'var(--color-text-primary)' }}>
                              {game.home_score}
                            </span>
                          </div>
                          
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ 
                              fontSize: 'var(--font-size-sm)', 
                              fontWeight: game.away_team.club_id === club.id ? 'var(--font-weight-bold)' : 'var(--font-weight-medium)',
                              color: game.away_team.club_id === club.id ? 'var(--color-text-accent)' : 'var(--color-text-primary)',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              maxWidth: '180px'
                            }}>
                              {game.away_team.name}
                            </span>
                            <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-bold)', color: game.away_team.club_id === club.id ? 'var(--color-text-accent)' : 'var(--color-text-primary)' }}>
                              {game.away_score}
                            </span>
                          </div>
                        </div>

                        <div style={{ marginTop: 'auto', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 'var(--space-2)', display: 'flex', flexDirection: 'column', gap: '2px', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                          <span>📅 {formatFixtureDate(game.game_date)}</span>
                          {game.location && <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>📍 {game.location}</span>}
                        </div>
                      </Link>
                    )
                  })}
                </div>
              ) : (
                <div className="card" style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                  No recent fixtures played.
                </div>
              )}
            </section>

            {/* 3. UPCOMING & LIVE GAMES CAROUSEL */}
            <section style={{ marginBottom: 'var(--space-6)' }}>
              <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-bold)', marginBottom: 'var(--space-4)', color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <span>📅</span> Upcoming & Live Games
              </h2>
              {club.upcoming_fixtures && club.upcoming_fixtures.length > 0 ? (
                <div style={{
                  display: 'flex',
                  flexDirection: 'row',
                  gap: 'var(--space-4)',
                  overflowX: 'auto',
                  paddingBottom: 'var(--space-4)',
                  scrollbarWidth: 'thin',
                  WebkitOverflowScrolling: 'touch'
                }}>
                  {club.upcoming_fixtures.map(game => {
                    const isLive = game.status === 'in_progress'
                    const isNotCompleted = game.status === 'not_completed'
                    
                    let cardBorderColor = 'var(--color-border)'
                    let cardBackground = 'rgba(17, 24, 39, 0.4)'
                    let cardOpacity = 1

                    if (isLive) {
                      cardBorderColor = 'var(--color-live)'
                      cardBackground = 'var(--color-live-bg)'
                    } else if (isNotCompleted) {
                      cardOpacity = 0.55
                    }

                    return (
                      <Link 
                        to={`/games/${game.id}`} 
                        key={game.id} 
                        className="card" 
                        style={{
                          flex: '0 0 290px',
                          padding: 'var(--space-4)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 'var(--space-3)',
                          textDecoration: 'none',
                          color: 'inherit',
                          borderLeft: `3px solid ${cardBorderColor}`,
                          background: cardBackground,
                          opacity: cardOpacity
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                            {game.round_name}
                          </span>
                          {isLive ? (
                            <span className="live-badge" style={{ fontSize: '0.65rem', padding: '2px var(--space-2)' }}>
                              <span className="live-dot" /> LIVE
                            </span>
                          ) : isNotCompleted ? (
                            <span className="badge" style={{
                              background: 'rgba(255, 255, 255, 0.05)',
                              color: 'var(--color-text-muted)',
                              borderColor: 'var(--color-border)',
                              fontSize: '0.65rem',
                              padding: '2px var(--space-2)'
                            }}>
                              NO RESULT
                            </span>
                          ) : (
                            <span className="badge" style={{
                              background: 'rgba(34, 197, 94, 0.1)',
                              color: 'var(--color-text-accent)',
                              borderColor: 'rgba(34, 197, 94, 0.2)',
                              fontSize: '0.65rem',
                              padding: '2px var(--space-2)'
                            }}>
                              FIXTURE
                            </span>
                          )}
                        </div>

                        {isLive ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ 
                                fontSize: 'var(--font-size-sm)', 
                                fontWeight: game.home_team.club_id === club.id ? 'var(--font-weight-bold)' : 'var(--font-weight-medium)',
                                color: game.home_team.club_id === club.id ? 'var(--color-text-accent)' : 'var(--color-text-primary)',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                maxWidth: '180px'
                              }}>
                                {game.home_team.name}
                              </span>
                              <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-bold)', color: game.home_team.club_id === club.id ? 'var(--color-text-accent)' : 'var(--color-text-primary)' }}>
                                {game.home_score}
                              </span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <span style={{ 
                                fontSize: 'var(--font-size-sm)', 
                                fontWeight: game.away_team.club_id === club.id ? 'var(--font-weight-bold)' : 'var(--font-weight-medium)',
                                color: game.away_team.club_id === club.id ? 'var(--color-text-accent)' : 'var(--color-text-primary)',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                maxWidth: '180px'
                              }}>
                                {game.away_team.name}
                              </span>
                              <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-bold)', color: game.away_team.club_id === club.id ? 'var(--color-text-accent)' : 'var(--color-text-primary)' }}>
                                {game.away_score}
                              </span>
                            </div>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                            <div>
                              <span style={{ 
                                fontSize: 'var(--font-size-sm)', 
                                fontWeight: game.home_team.club_id === club.id ? 'var(--font-weight-bold)' : 'var(--font-weight-medium)',
                                color: game.home_team.club_id === club.id ? 'var(--color-text-accent)' : 'var(--color-text-primary)',
                                display: 'block',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis'
                              }}>
                                {game.home_team.name}
                              </span>
                            </div>
                            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', textAlign: 'left', paddingLeft: 'var(--space-2)' }}>
                              vs
                            </div>
                            <div>
                              <span style={{ 
                                fontSize: 'var(--font-size-sm)', 
                                fontWeight: game.away_team.club_id === club.id ? 'var(--font-weight-bold)' : 'var(--font-weight-medium)',
                                color: game.away_team.club_id === club.id ? 'var(--color-text-accent)' : 'var(--color-text-primary)',
                                display: 'block',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis'
                              }}>
                                {game.away_team.name}
                              </span>
                            </div>
                          </div>
                        )}

                        <div style={{ marginTop: 'auto', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 'var(--space-2)', display: 'flex', flexDirection: 'column', gap: '2px', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                          <span>📅 {formatFixtureDate(game.game_date)} {!isLive && `at ${formatFixtureTime(game.game_date)}`}</span>
                          {game.location && <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>📍 {game.location}</span>}
                        </div>
                      </Link>
                    )
                  })}
                </div>
              ) : (
                <div className="card" style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                  No upcoming games scheduled.
                </div>
              )}
            </section>

          </main>
        </div>
      </div>
    </div>
  )
}
