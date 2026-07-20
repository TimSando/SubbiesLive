import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useGoBack } from '../hooks/useGoBack.js'
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

function EventRow({ event, playerImpact }) {
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
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-1.5)' }}>
              <Link to={`/players/${event.player_id}`} style={{ color: 'var(--color-accent-primary)', textDecoration: 'none' }}>
                {event.player_name}
              </Link>
              {playerImpact !== undefined && playerImpact !== null && (
                <span className="badge" style={{
                  fontSize: '9px',
                  padding: '1px 4px',
                  background: 'rgba(255,255,255,0.04)',
                  borderColor: 'rgba(255,255,255,0.1)',
                  color: playerImpact > 15 ? 'var(--color-win)' : (playerImpact > 5 ? 'var(--color-text-accent)' : 'var(--color-text-secondary)')
                }}>
                  +{playerImpact.toFixed(1)}
                </span>
              )}
            </span>
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
  const fallbackUrl = game?.competition_id ? `/competitions/${game.competition_id}` : '/competitions'
  const goBack = useGoBack(fallbackUrl)

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

  const isCompleted = game?.status === 'completed'
  const isLive = game?.status === 'in_progress'
  const isScheduled = game?.status === 'scheduled'
  const showScore = isCompleted || isLive

  // Fetch prediction data for scheduled games
  const { data: prediction } = useApi(
    () => isScheduled && game ? api.getGamePrediction(game.id).catch(() => null) : Promise.resolve(null),
    [isScheduled, game?.id]
  )

  // Fetch recent matches (Scores) for both teams
  const { data: homeGames } = useApi(
    () => game && !showScore ? api.getGames({ team_id: game.home_team.id, status: 'completed', limit: 5 }) : Promise.resolve([]),
    [game?.home_team?.id, showScore]
  )
  const { data: awayGames } = useApi(
    () => game && !showScore ? api.getGames({ team_id: game.away_team.id, status: 'completed', limit: 5 }) : Promise.resolve([]),
    [game?.away_team?.id, showScore]
  )

  // Fetch detailed form stats (Tries, Cards) for both teams
  const { data: homeStats } = useApi(
    () => game && !showScore ? api.getTeamFormStats(game.home_team.id) : Promise.resolve(null),
    [game?.home_team?.id, showScore]
  )
  const { data: awayStats } = useApi(
    () => game && !showScore ? api.getTeamFormStats(game.away_team.id) : Promise.resolve(null),
    [game?.away_team?.id, showScore]
  )

  // Fetch standings/ladder for competition to get team ranks
  const { data: standings } = useApi(
    () => game && !showScore ? api.getStandings(game.competition_id) : Promise.resolve(null),
    [game?.competition_id, showScore]
  )

  // Fetch impact scores for completed games events lookup
  const { data: homeImpact } = useApi(
    () => game && showScore ? api.getTeamImpactRankings(game.home_team.id) : Promise.resolve(null),
    [game?.home_team?.id, showScore]
  )
  const { data: awayImpact } = useApi(
    () => game && showScore ? api.getTeamImpactRankings(game.away_team.id) : Promise.resolve(null),
    [game?.away_team?.id, showScore]
  )

  const getPlayerImpactScore = (event) => {
    const impactData = event.team_id === game.home_team.id ? homeImpact : awayImpact
    const player = impactData?.players?.find(p => p.player_id === event.player_id)
    return player ? player.impact_score : null
  }

  const getTeamRank = (teamId) => {
    if (!standings || !standings.standings) return null
    const row = standings.standings.find(s => s.team_id === teamId)
    return row ? row.position : null
  }

  const formatRank = (rank) => {
    if (rank === 1) return '1st'
    if (rank === 2) return '2nd'
    if (rank === 3) return '3rd'
    return `${rank}th`
  }

  const renderKeyPlayers = (team, insights) => {
    if (!insights) return null
    const { key_players, squad_modifier, squad_modifier_source } = insights

    return (
      <div className="card" style={{ padding: 'var(--space-5)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)', borderBottom: '1px solid var(--color-border)', paddingBottom: 'var(--space-3)' }}>
          <h3 style={{ fontSize: 'var(--font-size-base)', fontWeight: 'var(--font-weight-bold)', margin: 0 }}>
            {team.club_name || team.name} Key Players
          </h3>
          {squad_modifier !== null && squad_modifier_source === 'game_squads' ? (
            <span className="badge" style={{
              background: squad_modifier >= 0 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              color: squad_modifier >= 0 ? 'var(--color-win)' : 'var(--color-loss)',
              borderColor: squad_modifier >= 0 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
            }}>
              Squad: {squad_modifier >= 0 ? '+' : ''}{squad_modifier.toFixed(1)} Elo
            </span>
          ) : (
            <span className="badge" style={{ background: 'rgba(255,255,255,0.03)', color: 'var(--color-text-muted)' }}>
              No Squad Named
            </span>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {key_players.map((p) => {
            const isMissing = p.weeks_since_last_game !== null && p.weeks_since_last_game >= 3
            const scoreColor = p.impact_score > 15 ? 'var(--color-win)' : (p.impact_score > 5 ? 'var(--color-text-accent)' : 'var(--color-text-secondary)')

            return (
              <div key={p.player_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 'var(--font-weight-semibold)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <Link to={`/players/${p.player_id}`} style={{ textDecoration: 'none', color: 'var(--color-text-primary)' }}>
                      {p.player_name}
                    </Link>
                    {isMissing && (
                      <span className="badge" style={{ fontSize: '9px', padding: '1px 4px', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--color-loss)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
                        Missing {p.weeks_since_last_game}w
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                    {p.games_this_season} games this season • Last: {p.last_played_round || 'N/A'}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-bold)', color: scoreColor }}>
                    +{p.impact_score.toFixed(1)}
                  </span>
                  {p.impact_score_season !== null && (
                    <div style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>
                      Season: +{p.impact_score_season.toFixed(1)}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
          {key_players.length === 0 && (
            <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)', margin: 0 }}>No impact ratings available for this team yet.</p>
          )}
        </div>
      </div>
    )
  }

  const renderTeamDashboard = (team, recentGames, stats, rank) => (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', paddingBottom: 'var(--space-4)', borderBottom: '1px solid var(--color-border)' }}>
         {team.logo_url ? (
           <img src={team.logo_url} alt={`${team.club_name || team.name} Logo`} className="club-card__logo" style={{ width: '40px', height: '40px', objectFit: 'contain' }} />
         ) : (
           <div className="club-card__logo-placeholder">🏉</div>
         )}
         <h2 style={{ fontSize: 'var(--font-size-xl)', color: 'var(--color-text-primary)', margin: 0, display: 'flex', alignItems: 'baseline', gap: 'var(--space-2)' }}>
           <span>{team.club_name || team.name}</span>
           {rank !== null && (
             <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-accent)', fontWeight: 'var(--font-weight-semibold)' }}>
               ({formatRank(rank)})
             </span>
           )}
         </h2>
      </div>

      <div>
        <h3 style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-3)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 'var(--font-weight-bold)' }}>
          Recent Form (Last 5 Games)
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
          {recentGames?.map(g => {
            const isHome = g.home_team.id === team.id
            const ourScore = isHome ? g.home_score : g.away_score
            const oppScore = isHome ? g.away_score : g.home_score
            const opponent = isHome ? g.away_team.name : g.home_team.name
            
            let resultClass = 'badge--draw'
            let resultText = 'D'
            if (ourScore > oppScore) { resultClass = 'badge--win'; resultText = 'W' }
            if (ourScore < oppScore) { resultClass = 'badge--loss'; resultText = 'L' }

            return (
              <Link
                key={g.id}
                to={`/games/${g.id}`}
                className="form-game-link"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: 'var(--space-3)',
                  background: 'var(--color-bg-glass)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  color: 'inherit',
                  textDecoration: 'none'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                  <span className={`badge ${resultClass}`} style={{ width: '32px', justifyContent: 'center', fontWeight: 'bold' }}>{resultText}</span>
                  <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>vs {opponent}</span>
                </div>
                <span style={{ fontWeight: 'var(--font-weight-bold)', fontVariantNumeric: 'tabular-nums', color: 'var(--color-text-primary)', fontSize: 'var(--font-size-sm)' }}>
                  {ourScore} - {oppScore}
                </span>
              </Link>
            )
          })}
          {(!recentGames || recentGames.length === 0) && (
            <p style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', fontStyle: 'italic', margin: 0 }}>
              No completed matches found in database.
            </p>
          )}
        </div>
      </div>

      <div>
        <h3 style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-3)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 'var(--font-weight-bold)' }}>
          Discipline & Scoring Summary (Last 5)
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
          <div style={{ background: 'var(--color-bg-glass)', padding: 'var(--space-4) var(--space-3)', borderRadius: 'var(--radius-md)', textAlign: 'center', border: '1px solid var(--color-border)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ display: 'block', fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-extrabold)', color: 'var(--color-text-accent)' }}>
              {stats?.total_tries || 0}
            </span>
            <span style={{ fontSize: '9px', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 'var(--font-weight-semibold)' }}>
              TRIES SCORED
            </span>
          </div>
          <div style={{ background: 'rgba(239, 68, 68, 0.05)', padding: 'var(--space-4) var(--space-3)', borderRadius: 'var(--radius-md)', textAlign: 'center', border: '1px solid rgba(239, 68, 68, 0.15)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{ display: 'block', fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-extrabold)', color: 'var(--color-loss)' }}>
              {stats?.total_yellow_cards || 0} <span style={{ color: 'var(--color-text-muted)', fontWeight: 'var(--font-weight-normal)', fontSize: 'var(--font-size-lg)' }}>/</span> {stats?.total_red_cards || 0}
            </span>
            <span style={{ fontSize: '9px', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 'var(--font-weight-semibold)' }}>
              YELLOW / RED CARDS
            </span>
          </div>
        </div>
      </div>
    </div>
  )

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
        <Link to="/competitions" className="btn btn--ghost" onClick={(e) => { e.preventDefault(); goBack(); }}>← Back</Link>
      </div></div>
    )
  }

  const homeWin = isCompleted && game.home_score > game.away_score
  const awayWin = isCompleted && game.away_score > game.home_score
  const homeEvents = game.events?.filter(e => e.team_id === game.home_team.id && !e.event_type.includes('coach')) || []
  const awayEvents = game.events?.filter(e => e.team_id === game.away_team.id && !e.event_type.includes('coach')) || []

  return (
    <div className="page">
      <div className="container animate-in">
        {game.competition_id && (
          <Link to={`/competitions/${game.competition_id}`} className="breadcrumb" onClick={(e) => { e.preventDefault(); goBack(); }}>
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
                {homeEvents.map((e, i) => <EventRow key={i} event={e} playerImpact={getPlayerImpactScore(e)} />)}
                {homeEvents.length === 0 && (
                  <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>No events</p>
                )}
              </div>
              <div className="events-col">
                <h3 className="events-col__title">
                  {game.away_team.club_name} ({game.away_score ?? 0})
                </h3>
                {awayEvents.map((e, i) => <EventRow key={i} event={e} playerImpact={getPlayerImpactScore(e)} />)}
                {awayEvents.length === 0 && (
                  <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>No events</p>
                )}
              </div>
            </div>
          </section>
        )}

        {!showScore && (
          <>
            {prediction && (
              <>
                <div className="card" style={{ marginTop: 'var(--space-8)', textAlign: 'center' }}>
                  <h3 style={{ fontSize: 'var(--font-size-sm)', textTransform: 'uppercase', color: 'var(--color-text-muted)', letterSpacing: '0.05em', marginBottom: 'var(--space-4)' }}>Match Prediction</h3>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
                    <div style={{ flex: 1, textAlign: 'left' }}>
                      <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)' }}>{Math.round(prediction.home_win_probability * 100)}%</div>
                    </div>
                    <div style={{ padding: '0 var(--space-4)', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                      <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'var(--font-weight-medium)' }}>Draw {Math.round(prediction.draw_probability * 100)}%</div>
                    </div>
                    <div style={{ flex: 1, textAlign: 'right' }}>
                      <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)' }}>{Math.round(prediction.away_win_probability * 100)}%</div>
                    </div>
                  </div>
                  {/* Visual bar */}
                  <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden', background: 'var(--color-bg-subtle)' }}>
                    <div style={{ width: `${prediction.home_win_probability * 100}%`, background: 'var(--color-accent-primary)' }} />
                    <div style={{ width: `${prediction.draw_probability * 100}%`, background: 'var(--color-border)' }} />
                    <div style={{ width: `${prediction.away_win_probability * 100}%`, background: 'var(--color-accent-secondary)' }} />
                  </div>
                  <div style={{ marginTop: 'var(--space-3)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                    Confidence: <span style={{ textTransform: 'capitalize', fontWeight: 'var(--font-weight-medium)', color: prediction.confidence === 'high' ? 'var(--color-win)' : 'var(--color-text-secondary)' }}>{prediction.confidence}</span>
                  </div>
                </div>

                {prediction.player_insights && (
                  <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--space-6)', marginTop: 'var(--space-6)' }}>
                    {renderKeyPlayers(game.home_team, prediction.player_insights.home_team)}
                    {renderKeyPlayers(game.away_team, prediction.player_insights.away_team)}
                  </div>
                )}
              </>
            )}
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--space-6)', marginTop: 'var(--space-8)' }}>
              {renderTeamDashboard(game.home_team, homeGames, homeStats, getTeamRank(game.home_team.id))}
              {renderTeamDashboard(game.away_team, awayGames, awayStats, getTeamRank(game.away_team.id))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
