import { useParams, Link, useNavigate } from 'react-router-dom'
import { useState, useMemo } from 'react'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'
import ToggleSwitch from '../components/Stats/ToggleSwitch.jsx'

function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric', month: 'short' })
}

function calculateAge(dobStr) {
  if (!dobStr) return 'N/A'
  const dob = new Date(dobStr)
  if (isNaN(dob.getTime())) return 'N/A'
  const today = new Date()
  let age = today.getFullYear() - dob.getFullYear()
  const m = today.getMonth() - dob.getMonth()
  if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) {
    age--
  }
  return age
}

export default function PlayerDetail() {
  const navigate = useNavigate()
  const { id } = useParams()
  const [viewMode, setViewMode] = useState('total')

  const { data: player, loading: loadingPlayer } = useApi(
    () => api.getPlayer(id),
    [id]
  )

  const { data: games, loading: loadingGames } = useApi(
    () => api.getGames({ player_id: id, limit: 20 }),
    [id]
  )

  const uniqueClubs = useMemo(() => {
    if (!player?.teams) return []
    return Array.from(new Set(player.teams.map(t => t.club_name).filter(Boolean)))
  }, [player])

  const getStatValue = (key) => {
    if (!player?.stats) return '0'
    const val = player.stats[key] || 0
    if (viewMode === 'total') return val.toString()
    
    const gp = player.stats.games_played || 1
    return gp > 0 ? (val / gp).toFixed(2) : '0.00'
  }

  if (loadingPlayer) {
    return (
      <div className="page">
        <div className="container">
          <div className="skeleton" style={{ height: '300px', marginBottom: 'var(--space-6)' }} />
          <div className="skeleton" style={{ height: '400px' }} />
        </div>
      </div>
    )
  }

  if (!player) {
    return (
      <div className="page">
        <div className="container">
          <h1>Player not found</h1>
          <Link to="/stats" className="btn btn--ghost" style={{ marginTop: 'var(--space-4)' }} onClick={(e) => { e.preventDefault(); navigate(-1); }}>
            ← Back
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="container animate-in">
        <Link to="/stats" className="breadcrumb" onClick={(e) => { e.preventDefault(); navigate(-1); }}>← Back</Link>

        {/* Player Profile Header Card */}
        <div className="card" style={{ display: 'flex', gap: 'var(--space-6)', padding: 'var(--space-6)', marginBottom: 'var(--space-8)', flexWrap: 'wrap', alignItems: 'center' }}>
          {/* Avatar Placeholder */}
          <img 
            src="https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y" 
            alt={player.name} 
            style={{
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              objectFit: 'cover',
              border: '2px solid rgba(255,255,255,0.1)'
            }}
          />

          <div style={{ flex: '1', minWidth: '200px' }}>
            <h1 style={{ margin: '0 0 var(--space-1) 0', fontSize: '2rem' }}>{player.name}</h1>
            {player.recent_club && (
              <div style={{ fontSize: '1.1rem', fontWeight: '500', color: 'var(--color-accent-primary)', marginBottom: 'var(--space-2)' }}>
                {player.recent_club}
              </div>
            )}
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
              {uniqueClubs.length > 0 && (
                <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>Clubs:</span>
                  {uniqueClubs.map((club, idx) => (
                    <span key={idx} className="badge" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--color-accent-primary)' }}>
                      {club}
                    </span>
                  ))}
                </div>
              )}
              <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', marginTop: 'var(--space-1)' }}>
                <span>Age: {calculateAge(player.dob)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Statistics Section */}
        <section style={{ marginBottom: 'var(--space-10)' }}>
          <header className="stats-header" style={{ marginBottom: 'var(--space-6)', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ margin: 0 }}>Career Stats Summary</h2>
            <ToggleSwitch value={viewMode} onChange={setViewMode} />
          </header>

          <div className="overview-grid">
            <div className="card overview-card">
              <span className="overview-card__icon">📍</span>
              <span className="overview-card__value">{player.stats.games_played}</span>
              <span className="overview-card__label">Games Played</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">🏉</span>
              <span className="overview-card__value">{getStatValue('total_tries')}</span>
              <span className="overview-card__label">{viewMode === 'total' ? 'Total Tries' : 'Avg Tries/Game'}</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">🔄</span>
              <span className="overview-card__value">{getStatValue('total_conversions')}</span>
              <span className="overview-card__label">{viewMode === 'total' ? 'Conversions' : 'Avg Conversions/Game'}</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">🎯</span>
              <span className="overview-card__value">{getStatValue('total_penalty_goals')}</span>
              <span className="overview-card__label">{viewMode === 'total' ? 'Penalty Goals' : 'Avg Penalty Goals/Game'}</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">💥</span>
              <span className="overview-card__value">{getStatValue('total_drop_goals')}</span>
              <span className="overview-card__label">{viewMode === 'total' ? 'Drop Goals' : 'Avg Drop Goals/Game'}</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">🏆</span>
              <span className="overview-card__value" style={{ color: 'var(--color-accent-primary)' }}>{getStatValue('total_points')}</span>
              <span className="overview-card__label">{viewMode === 'total' ? 'Total Points' : 'Avg Points/Game'}</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">🟡</span>
              <span className="overview-card__value" style={{ color: 'var(--color-draw)' }}>{getStatValue('total_yellow_cards')}</span>
              <span className="overview-card__label">{viewMode === 'total' ? 'Yellow Cards' : 'Avg Yellow Cards/Game'}</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">🔴</span>
              <span className="overview-card__value" style={{ color: 'var(--color-loss)' }}>{getStatValue('total_red_cards')}</span>
              <span className="overview-card__label">{viewMode === 'total' ? 'Red Cards' : 'Avg Red Cards/Game'}</span>
            </div>
          </div>
        </section>

        {/* Recent Games Played Section */}
        <section>
          <h2 style={{ marginBottom: 'var(--space-6)' }}>Recent Matches</h2>

          {loadingGames ? (
            <div className="skeleton" style={{ height: '300px' }} />
          ) : !games || games.length === 0 ? (
            <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>No recent games logged for this player.</p>
          ) : (
            <div className="round-games animate-in">
              {games.map(game => {
                const isCompleted = game.status === 'completed'
                const isLive = game.status === 'in_progress'
                const isNotCompleted = game.status === 'not_completed'
                const homeWin = isCompleted && game.home_score > game.away_score
                const awayWin = isCompleted && game.away_score > game.home_score
                const showScore = isCompleted || isLive

                let rowClass = 'fixture-row'
                if (isLive) rowClass += ' fixture-row--live'
                if (isNotCompleted) rowClass += ' fixture-row--not-completed'

                return (
                  <Link to={`/games/${game.id}`} key={game.id} className={rowClass} id={`fixture-${game.id}`}>
                    <span className="fixture-row__date">{formatDate(game.game_date)}</span>
                    <span className={`fixture-row__team fixture-row__team--home ${homeWin ? 'fixture-row__team--winner' : ''}`}>
                      {game.home_team.club_name || game.home_team.name}
                    </span>
                    
                    {isNotCompleted ? (
                      <>
                        <span className="fixture-row__score--home"></span>
                        <span className="fixture-row__score--dash">
                          <span className="not-completed-label">No result</span>
                        </span>
                        <span className="fixture-row__score--away"></span>
                      </>
                    ) : (
                      <>
                        <span className="fixture-row__score--home">
                          {showScore ? (
                            <span className={homeWin ? 'score--winner' : ''}>{game.home_score}</span>
                          ) : <span style={{ color: 'var(--color-text-muted)' }}>-</span>}
                        </span>
                        <span className="fixture-row__score--dash">—</span>
                        <span className="fixture-row__score--away">
                          {showScore ? (
                            <span className={awayWin ? 'score--winner' : ''}>{game.away_score}</span>
                          ) : <span style={{ color: 'var(--color-text-muted)' }}>-</span>}
                        </span>
                      </>
                    )}

                    <span className={`fixture-row__team fixture-row__team--away ${awayWin ? 'fixture-row__team--winner' : ''}`}>
                      {game.away_team.club_name || game.away_team.name}
                    </span>
                    <span className="fixture-row__location">
                      {isLive ? (
                        <span className="live-badge">
                          <span className="live-dot" /> Live
                        </span>
                      ) : (
                        game.location ? `📍 ${game.location}` : ''
                      )}
                    </span>
                  </Link>
                )
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
