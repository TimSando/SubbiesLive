import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'

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
          {event.player_name || `#${event.player_number || '?'}`}
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
  const homeWin = isCompleted && game.home_score > game.away_score
  const awayWin = isCompleted && game.away_score > game.home_score
  const homeEvents = game.events?.filter(e => e.team_id === game.home_team.id) || []
  const awayEvents = game.events?.filter(e => e.team_id === game.away_team.id) || []

  return (
    <div className="page">
      <div className="container animate-in">
        {game.competition_id && (
          <Link to={`/competitions/${game.competition_id}`} className="breadcrumb">
            ← {game.competition_name}
          </Link>
        )}

        <div className="match-header card">
          <div className="match-header__meta">
            <span className="badge">{game.competition_name}</span>
            <span style={{ color: 'var(--color-text-muted)' }}>{game.round_name}</span>
          </div>

          <div className="match-header__teams">
            <div className={`match-header__team ${homeWin ? 'match-header__team--winner' : ''}`}>
              <Link to={`/clubs/${game.home_team.club_id}`} className="match-header__team-name">
                {game.home_team.club_name || game.home_team.name}
              </Link>
              <span className="match-header__label">Home</span>
            </div>

            <div className="match-header__score">
              {isCompleted ? (
                <>
                  <span className={`score ${homeWin ? 'score--winner' : ''}`}>{game.home_score}</span>
                  <span className="match-header__divider">—</span>
                  <span className={`score ${awayWin ? 'score--winner' : ''}`}>{game.away_score}</span>
                </>
              ) : (
                <span className="badge badge--scheduled">vs</span>
              )}
            </div>

            <div className={`match-header__team ${awayWin ? 'match-header__team--winner' : ''}`}>
              <Link to={`/clubs/${game.away_team.club_id}`} className="match-header__team-name">
                {game.away_team.club_name || game.away_team.name}
              </Link>
              <span className="match-header__label">Away</span>
            </div>
          </div>

          <div className="match-header__info">
            <span>📅 {formatDateTime(game.game_date)}</span>
            {game.location && <span>📍 {game.location}</span>}
          </div>
        </div>

        {isCompleted && game.events?.length > 0 && (
          <section style={{ marginTop: 'var(--space-8)' }}>
            <h2 style={{ marginBottom: 'var(--space-6)' }}>Match Events</h2>
            <div className="events-grid">
              <div className="events-col">
                <h3 className="events-col__title">
                  {game.home_team.club_name} ({game.home_score})
                </h3>
                {homeEvents.map((e, i) => <EventRow key={i} event={e} />)}
                {homeEvents.length === 0 && (
                  <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>No events</p>
                )}
              </div>
              <div className="events-col">
                <h3 className="events-col__title">
                  {game.away_team.club_name} ({game.away_score})
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
