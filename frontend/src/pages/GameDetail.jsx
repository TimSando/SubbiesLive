import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'
import PageSubscribeButton from '../components/NotificationToggle/PageSubscribeButton.jsx'

function formatDateTime(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-AU', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

function RugbyPosts() {
  return (
    <svg 
      width="16" 
      height="16" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2.5" 
      strokeLinecap="round" 
      strokeLinejoin="round"
      style={{ display: 'block' }}
    >
      <path d="M6 20V4M18 20V4M6 12h12" />
    </svg>
  )
}

function EventRow({ event }) {
  const icons = { 
    try: '🏉', 
    conversion: <RugbyPosts />, 
    penalty_goal: '🎯', 
    drop_goal: '💥', 
    yellow_card: '🟡', 
    red_card: '🔴',
    blue_card: '🚑',
    rugby_union_blue_card: '🚑',
    rugby_union_penalty_try: '🏉'
  }
  // Blue card is a welfare/HIA (Head Injury Assessment) event, not discipline
  const isCard = ['yellow_card', 'red_card'].includes(event.event_type)

  return (
    <div className="event-row" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        <span className="event-row__icon" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '20px' }}>
          {icons[event.event_type] || '📋'}
        </span>
        <span className="event-row__type">{event.event_type.replace('_', ' ')}</span>
        <span className="event-row__player">
          {event.player_id ? (
            <Link to={`/players/${event.player_id}`} style={{ color: 'var(--color-accent-primary)', textDecoration: 'none' }}>
              {event.player_name}
            </Link>
          ) : (
            event.player_name || `#${event.player_number || '?'}`
          )}
        </span>
        {!isCard && <span className="event-row__points">+{event.points}</span>}
      </div>
      {isCard && event.text && (
        <div style={{ 
          marginLeft: '32px', 
          fontSize: 'var(--font-size-xs)', 
          color: 'var(--color-text-muted)', 
          fontStyle: 'italic',
          marginTop: '-4px',
          paddingBottom: 'var(--space-2)'
        }}>
          "{event.text}"
        </div>
      )}
    </div>
  )
}

export default function GameDetail() {
  const { id } = useParams()
  const { data: game, loading } = useApi(() => api.getGame(id), [id])

  const [weather, setWeather] = useState(null)
  const [loadingWeather, setLoadingWeather] = useState(false)
  const [venueCoords, setVenueCoords] = useState({ latitude: null, longitude: null })

  useEffect(() => {
    let isMounted = true
    if (game?.location && game?.game_date) {
      const gameDate = new Date(game.game_date)
      const now = new Date()
      const diffTime = gameDate - now
      const diffDays = diffTime / (1000 * 60 * 60 * 24)
      const isWithinSevenDaysFuture = diffDays > 0 && diffDays < 7

      if (isWithinSevenDaysFuture) {
        setLoadingWeather(true)
        api.getVenueWeather(game.location, game.game_date, game.id)
          .then((data) => {
            if (isMounted && data) {
              setVenueCoords({
                latitude: data.latitude,
                longitude: data.longitude
              })
              setWeather(data.weather)
              setLoadingWeather(false)
            }
          })
          .catch((err) => {
            console.warn('Failed to load venue/weather for game:', err)
            if (isMounted) {
              setLoadingWeather(false)
            }
          })
      }
    }
    return () => {
      isMounted = false
    }
  }, [game?.location, game?.game_date, game?.id])

  if (loading) {
    return (
      <div className="page"><div className="container">
        <div className="skeleton" style={{ height: '300px' }} />
      </div></div>
    )
  }

  if (!game) {
    return (
      <div className="page"><div className="container">
        <h1>Game not found</h1>
        <Link to="/competitions" className="btn btn--ghost">← Back</Link>
      </div></div>
    )
  }

  const isCompleted = game.status === 'completed'
  const isLive = game.status === 'in_progress'
  const showScore = isCompleted || isLive
  const homeWin = isCompleted && game.home_score > game.away_score
  const awayWin = isCompleted && game.away_score > game.home_score
  const homeEvents = game.events?.filter(e => e.team_id === game.home_team.id && !e.event_type.includes('coach')) || []
  const awayEvents = game.events?.filter(e => e.team_id === game.away_team.id && !e.event_type.includes('coach')) || []

  return (
    <div className="page">
      <div className="container animate-in">
        {game.competition_id && (
          <Link to={`/competitions/${game.competition_id}`} className="breadcrumb">
            ← {game.competition_name}
          </Link>
        )}

        <div className="match-header card">
          <div className="match-header__meta" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <span className="badge">{game.competition_name}</span>
              {isLive && (
                <span className="live-badge">
                  <span className="live-dot" /> Live
                </span>
              )}
              <span style={{ color: 'var(--color-text-muted)' }}>{game.round_name}</span>
            </div>
            <PageSubscribeButton 
              topicType="game" 
              topicId={game.id} 
              topicName={`${game.home_team.club_name || game.home_team.name} vs ${game.away_team.club_name || game.away_team.name}`} 
            />
          </div>

          <div className="match-header__teams">
            <div className={`match-header__team ${homeWin ? 'match-header__team--winner' : ''}`}>
              <Link to={`/teams/${game.home_team.id}`} className="match-header__team-name">
                {game.home_team.club_name || game.home_team.name}
              </Link>
              <span className="match-header__label">Home</span>
            </div>

            <div className="match-header__score">
              {showScore ? (
                <>
                  <span className={`score ${homeWin ? 'score--winner' : ''}`}>{game.home_score ?? 0}</span>
                  <span className="match-header__divider">—</span>
                  <span className={`score ${awayWin ? 'score--winner' : ''}`}>{game.away_score ?? 0}</span>
                </>
              ) : (
                <span className="badge badge--scheduled">vs</span>
              )}
            </div>

            <div className={`match-header__team ${awayWin ? 'match-header__team--winner' : ''}`}>
              <Link to={`/teams/${game.away_team.id}`} className="match-header__team-name">
                {game.away_team.club_name || game.away_team.name}
              </Link>
              <span className="match-header__label">Away</span>
            </div>
          </div>

          <div className="match-header__info" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-4)' }}>
              <span>📅 {formatDateTime(game.game_date)}</span>
              {game.location && (
                <span>
                  📍{' '}
                  <a
                    href={
                      venueCoords.latitude !== null && venueCoords.longitude !== null
                        ? `https://www.google.com/maps/search/?api=1&query=${venueCoords.latitude},${venueCoords.longitude}`
                        : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                            game.location + ' Sydney'
                          )}`
                    }
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: 'var(--color-text-accent)', textDecoration: 'none' }}
                  >
                    {game.location} ↗
                  </a>
                </span>
              )}
            </div>
            {loadingWeather && (
              <div className="weather-strip">
                <span style={{ fontWeight: 'var(--font-weight-semibold)' }}>Weather Forecast:</span>
                <span>🌡️ Loading...</span>
              </div>
            )}
            {!loadingWeather && weather && weather.temperature !== undefined && (
              <div className="weather-strip">
                <span style={{ fontWeight: 'var(--font-weight-semibold)' }}>Weather Forecast:</span>
                <span>🌡️ {weather.temperature !== null && weather.temperature !== undefined ? `${weather.temperature}°C` : 'N/A'}</span>
                <span>🌧️ {weather.precipitation_probability !== null && weather.precipitation_probability !== undefined ? `${weather.precipitation_probability}%` : '0%'}</span>
                <span>💨 {weather.wind_speed !== null && weather.wind_speed !== undefined ? `${weather.wind_speed} km/h` : 'N/A'}</span>
              </div>
            )}
          </div>

          {game.video_url && (
            <div style={{ 
              marginTop: 'var(--space-6)', 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              gap: 'var(--space-3)' 
              }}>
              <a 
                href={game.video_url} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="btn"
                style={{ 
                  background: 'linear-gradient(135deg, #1e40af, #1e3a8a)', 
                  color: 'white',
                  borderColor: '#3b82f6',
                  gap: 'var(--space-2)',
                  fontWeight: 'var(--font-weight-semibold)',
                  boxShadow: '0 0 15px rgba(59, 130, 246, 0.2)'
                }}
              >
                {isCompleted ? '📺 Watch Replay on NSW Rugby TV' : '📺 Watch Live on NSW Rugby TV'}
              </a>
              {game.video_url_needs_review && (
                <span className="badge" style={{ 
                  backgroundColor: 'rgba(245, 158, 11, 0.15)', 
                  color: 'var(--color-draw)', 
                  borderColor: 'rgba(245, 158, 11, 0.25)',
                  textTransform: 'none',
                  letterSpacing: 'normal'
                }}>
                  ⚠️ Unverified Stream Link (Pending Review)
                </span>
              )}
            </div>
          )}
        </div>

        {showScore && game.events?.length > 0 && (
          <section style={{ marginTop: 'var(--space-8)' }}>
            <h2 style={{ marginBottom: 'var(--space-6)' }}>Match Events</h2>
            <div className="events-grid">
              <div className="events-col">
                <h3 className="events-col__title">
                  {game.home_team.club_name} ({game.home_score ?? 0})
                </h3>
                {homeEvents.map((e, i) => <EventRow key={i} event={e} />)}
                {homeEvents.length === 0 && (
                  <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>No events</p>
                )}
              </div>
              <div className="events-col">
                <h3 className="events-col__title">
                  {game.away_team.club_name} ({game.away_score ?? 0})
                </h3>
                {awayEvents.map((e, i) => <EventRow key={i} event={e} />)}
                {awayEvents.length === 0 && (
                  <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>No events</p>
                )}
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
