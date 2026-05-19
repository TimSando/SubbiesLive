import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'

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
  const homeWin = isCompleted && game.home_score > game.away_score
  const awayWin = isCompleted && game.away_score > game.home_score

  return (
    <Link to={`/games/${game.id}`} className="game-pill" id={`game-${game.id}`}>
      <div className="game-pill__meta">
        <span className="game-pill__comp">{game.competition_name}</span>
        <span className="game-pill__round">{game.round_name}</span>
      </div>
      <div className="game-pill__teams">
        <div className={`game-pill__team ${homeWin ? 'game-pill__team--winner' : ''}`}>
          <span className="game-pill__team-name">{game.home_team.club_name || game.home_team.name}</span>
          {isCompleted && (
            <span className={`game-pill__score ${homeWin ? 'game-pill__score--winner' : ''}`}>
              {game.home_score}
            </span>
          )}
        </div>
        <div className={`game-pill__team ${awayWin ? 'game-pill__team--winner' : ''}`}>
          <span className="game-pill__team-name">{game.away_team.club_name || game.away_team.name}</span>
          {isCompleted && (
            <span className={`game-pill__score ${awayWin ? 'game-pill__score--winner' : ''}`}>
              {game.away_score}
            </span>
          )}
        </div>
      </div>
      <div className="game-pill__footer">
        <span className="game-pill__date">
          {formatDate(game.game_date)} {!isCompleted && `at ${formatTime(game.game_date)}`}
        </span>
        <span className="game-pill__status">{game.status}</span>
      </div>
    </Link>
  )
}

export default function Home() {
  const { data: recentGames, loading: loadingRecent } = useApi(
    () => api.getGames({ status: 'completed', limit: 6 }), []
  )
  const { data: upcomingGames, loading: loadingUpcoming } = useApi(
    () => api.getGames({ status: 'scheduled', limit: 6 }), []
  )
  const { data: overview, loading: loadingOverview } = useApi(
    () => api.getSeasonOverview(), []
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

        <hr className="home-section-divider" />

        {/* 2. Three Navigation Cards */}
        <section className="home-nav-cards">
          <Link to="/clubs" className="home-nav-card" id="nav-clubs-card">
            <div className="home-nav-card__icon">
              <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
            </div>
            <h2>
              Clubs
              <span className="home-nav-card__arrow">→</span>
            </h2>
            <p>Browse all subbies clubs, locate home grounds, check socials, training times, and active grades.</p>
          </Link>

          <Link to="/competitions" className="home-nav-card" id="nav-competitions-card">
            <div className="home-nav-card__icon">
              <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
                <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
                <path d="M4 22h16" />
                <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
                <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
                <path d="M18 2H6v7a6 6 0 0 0 12 0V2z" />
              </svg>
            </div>
            <h2>
              Competitions
              <span className="home-nav-card__arrow">→</span>
            </h2>
            <p>View division ladders, follow weekly fixture draws, check kick-off times, and follow live match results.</p>
          </Link>

          <Link to="/stats" className="home-nav-card" id="nav-stats-card">
            <div className="home-nav-card__icon">
              <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10" />
                <line x1="12" y1="20" x2="12" y2="4" />
                <line x1="6" y1="20" x2="6" y2="14" />
              </svg>
            </div>
            <h2>
              Statistics
              <span className="home-nav-card__arrow">→</span>
            </h2>
            <p>Deep-dive into player performance, leaderboard rankings, top try-scorers, conversions, and team stats.</p>
          </Link>
        </section>

        <hr className="home-section-divider" />

        {/* 3. Recent Results Strip */}
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

        {/* 4. Upcoming Fixtures Strip */}
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
    </div>
  )
}
