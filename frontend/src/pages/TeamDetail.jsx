import { useParams, Link } from 'react-router-dom'
import { useState } from 'react'
import { useApi } from '../hooks/useApi.js'
import { useGoBack } from '../hooks/useGoBack.js'
import { api } from '../api/client.js'

function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric', month: 'short' })
}

export default function TeamDetail() {
  const goBack = useGoBack('/clubs')
  const { id } = useParams()

  const { data: team, loading: loadingTeam } = useApi(
    () => api.getTeam(id),
    [id]
  )

  const { data: games, loading: loadingGames } = useApi(
    () => team ? api.getGames({ team_id: id, year: team.year, limit: 50 }) : Promise.resolve([]),
    [id, team?.year]
  )


  if (loadingTeam) {
    return (
      <div className="page">
        <div className="container">
          <div className="skeleton" style={{ height: '300px', marginBottom: 'var(--space-6)' }} />
          <div className="skeleton" style={{ height: '400px' }} />
        </div>
      </div>
    )
  }

  if (!team) {
    return (
      <div className="page">
        <div className="container">
          <h1>Team not found</h1>
          <Link to="/clubs" className="btn btn--ghost" style={{ marginTop: 'var(--space-4)' }} onClick={(e) => { e.preventDefault(); goBack(); }}>
            ← Back
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="container animate-in">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-6)' }}>
          <Link to="/clubs" className="breadcrumb" style={{ margin: 0 }} onClick={(e) => { e.preventDefault(); goBack(); }}>
            ← Back
          </Link>
        </div>

        {/* Team Profile Header Card */}
        <div className="card" style={{ display: 'flex', gap: 'var(--space-6)', padding: 'var(--space-6)', marginBottom: 'var(--space-8)', flexWrap: 'wrap', alignItems: 'center' }}>
          {team.club_logo_url ? (
            <img 
              src={team.club_logo_url} 
              alt={`${team.club_name} logo`} 
              style={{
                width: '80px',
                height: '80px',
                objectFit: 'contain',
                borderRadius: 'var(--radius-xl)',
                background: 'rgba(255, 255, 255, 0.05)',
                padding: 'var(--space-2)',
                border: '1px solid var(--color-border)'
              }}
            />
          ) : (
            <div style={{
              width: '80px',
              height: '80px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '2.5rem',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-xl)',
              color: 'var(--color-text-accent)'
            }}>
              🏉
            </div>
          )}

          <div style={{ flex: '1', minWidth: '200px' }}>
            <h1 style={{ margin: '0 0 var(--space-1) 0', fontSize: '2rem' }}>{team.name}</h1>
            <div style={{ fontSize: '1.1rem', fontWeight: '500', color: 'var(--color-accent-primary)', marginBottom: 'var(--space-2)' }}>
              <Link to={`/clubs/${team.club_id}`} style={{ color: 'inherit', textDecoration: 'none' }}>
                {team.club_name}
              </Link>
            </div>
            
            <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', alignItems: 'center' }}>
              <span className="badge" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--color-accent-primary)' }}>
                {team.competition_name}
              </span>
            </div>
          </div>
        </div>

        {/* Statistics Section */}
        <section style={{ marginBottom: 'var(--space-10)' }}>
          <header className="stats-header" style={{ marginBottom: 'var(--space-6)' }}>
            <h2 style={{ margin: 0 }}>{team.year} Season Stats Summary</h2>
          </header>

          <div className="overview-grid">
            <div className="card overview-card">
              <span className="overview-card__icon">📍</span>
              <span className="overview-card__value">{team.stats.games_played}</span>
              <span className="overview-card__label">Games Played</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">🏆</span>
              <span className="overview-card__value" style={{ color: 'var(--color-win)' }}>{team.stats.wins}</span>
              <span className="overview-card__label">Wins</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">❌</span>
              <span className="overview-card__value" style={{ color: 'var(--color-loss)' }}>{team.stats.losses}</span>
              <span className="overview-card__label">Losses</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">🤝</span>
              <span className="overview-card__value" style={{ color: 'var(--color-draw)' }}>{team.stats.draws}</span>
              <span className="overview-card__label">Draws</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">🏉</span>
              <span className="overview-card__value">{team.stats.total_tries}</span>
              <span className="overview-card__label">Total Tries</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">🎯</span>
              <span className="overview-card__value">{team.stats.total_conversions}</span>
              <span className="overview-card__label">Conversions</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">➕</span>
              <span className="overview-card__value" style={{ color: 'var(--color-accent-primary)' }}>{team.stats.points_for}</span>
              <span className="overview-card__label">Points For</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">➖</span>
              <span className="overview-card__value" style={{ color: 'var(--color-text-secondary)' }}>{team.stats.points_against}</span>
              <span className="overview-card__label">Points Against</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">🟡</span>
              <span className="overview-card__value" style={{ color: 'var(--color-draw)' }}>{team.stats.total_yellow_cards}</span>
              <span className="overview-card__label">Yellow Cards</span>
            </div>
            <div className="card overview-card">
              <span className="overview-card__icon">🔴</span>
              <span className="overview-card__value" style={{ color: 'var(--color-loss)' }}>{team.stats.total_red_cards}</span>
              <span className="overview-card__label">Red Cards</span>
            </div>
          </div>
        </section>

        {/* Matches Section */}
        <section>
          <h2 style={{ marginBottom: 'var(--space-6)' }}>{team.year} Matches</h2>

          {loadingGames ? (
            <div className="skeleton" style={{ height: '300px' }} />
          ) : !games || games.length === 0 ? (
            <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>No matches logged for this team in {team.year}.</p>
          ) : (
            <div className="round-games animate-in">
              {games.map(game => {
                const isCompleted = game.status === 'completed'
                const isLive = game.status === 'in_progress'
                const isNotCompleted = game.status === 'not_completed'
                const homeWin = isCompleted && game.home_score > game.away_score
                const awayWin = isCompleted && game.away_score > game.home_score
                const showScore = isCompleted || isLive

                // Calculate win/loss/draw outcome for the team
                const isHome = Number(game.home_team.id) === Number(team.id)
                const ourScore = isHome ? game.home_score : game.away_score
                const oppScore = isHome ? game.away_score : game.home_score
                const isWin = isCompleted && ourScore > oppScore
                const isLoss = isCompleted && ourScore < oppScore
                const isDraw = isCompleted && ourScore === oppScore
                const outcomeColor = isWin ? 'var(--color-win)' : isLoss ? 'var(--color-loss)' : isDraw ? 'var(--color-draw)' : 'transparent'

                let rowClass = 'fixture-row'
                if (isLive) rowClass += ' fixture-row--live'
                if (isNotCompleted) rowClass += ' fixture-row--not-completed'

                return (
                  <Link 
                    to={`/games/${game.id}`} 
                    key={game.id} 
                    className={rowClass} 
                    id={`fixture-${game.id}`}
                    style={{ borderLeft: isCompleted ? `4px solid ${outcomeColor}` : '4px solid transparent' }}
                  >
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
