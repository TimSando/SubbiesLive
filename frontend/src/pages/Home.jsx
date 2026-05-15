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

function GameCard({ game }) {
  const isCompleted = game.status === 'completed'
  const homeWin = isCompleted && game.home_score > game.away_score
  const awayWin = isCompleted && game.away_score > game.home_score

  return (
    <Link to={`/games/${game.id}`} className="card card--clickable game-card" id={`game-${game.id}`}>
      <div className="game-card__meta">
        <span className="game-card__comp">{game.competition_name}</span>
        <span className="game-card__round">{game.round_name}</span>
      </div>
      <div className="game-card__teams">
        <div className={`game-card__team ${homeWin ? 'game-card__team--winner' : ''}`}>
          <span className="game-card__team-name">{game.home_team.club_name || game.home_team.name}</span>
          {isCompleted && <span className={`score ${homeWin ? 'score--winner' : ''}`}>{game.home_score}</span>}
        </div>
        <div className="game-card__vs">{isCompleted ? '—' : 'vs'}</div>
        <div className={`game-card__team ${awayWin ? 'game-card__team--winner' : ''}`}>
          <span className="game-card__team-name">{game.away_team.club_name || game.away_team.name}</span>
          {isCompleted && <span className={`score ${awayWin ? 'score--winner' : ''}`}>{game.away_score}</span>}
        </div>
      </div>
      <div className="game-card__footer">
        <span className="game-card__date">{formatDate(game.game_date)}</span>
        {game.location && <span className="game-card__location">📍 {game.location}</span>}
        <span className={`badge badge--${game.status}`}>{game.status}</span>
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
  const { data: competitions, loading: loadingComps } = useApi(
    () => api.getCompetitions(), []
  )

  return (
    <div className="page">
      <div className="container animate-in">
        <header className="home-hero">
          <h1 className="home-hero__title">
            Sydney Suburban<br />
            <span className="home-hero__accent">Rugby Union</span>
          </h1>
          <p className="home-hero__subtitle">
            Live standings, results, and player statistics across all subbies competitions.
          </p>
          <div className="home-hero__actions">
            <Link to="/competitions" className="btn btn--primary" id="browse-competitions-btn">
              Browse Competitions →
            </Link>
          </div>
        </header>

        {/* Stats summary */}
        {competitions && (
          <section className="home-stats">
            <div className="stat-card">
              <span className="stat-card__value">{competitions.length}</span>
              <span className="stat-card__label">Competitions</span>
            </div>
            <div className="stat-card">
              <span className="stat-card__value">
                {competitions.reduce((sum, c) => sum + c.team_count, 0)}
              </span>
              <span className="stat-card__label">Teams</span>
            </div>
            <div className="stat-card">
              <span className="stat-card__value">
                {competitions.reduce((sum, c) => sum + c.round_count, 0)}
              </span>
              <span className="stat-card__label">Rounds</span>
            </div>
          </section>
        )}

        {/* Recent Results */}
        <section className="home-section">
          <div className="home-section__header">
            <h2>Recent Results</h2>
            <Link to="/competitions" className="btn btn--ghost">View All →</Link>
          </div>
          {loadingRecent ? (
            <div className="grid grid--3">
              {[1,2,3].map(i => <div key={i} className="skeleton" style={{height: '160px'}} />)}
            </div>
          ) : (
            <div className="grid grid--3">
              {recentGames?.map(game => <GameCard key={game.id} game={game} />)}
            </div>
          )}
        </section>

        {/* Upcoming Games */}
        <section className="home-section">
          <div className="home-section__header">
            <h2>Upcoming Fixtures</h2>
          </div>
          {loadingUpcoming ? (
            <div className="grid grid--3">
              {[1,2,3].map(i => <div key={i} className="skeleton" style={{height: '160px'}} />)}
            </div>
          ) : upcomingGames?.length === 0 ? (
            <p style={{ color: 'var(--color-text-secondary)' }}>No upcoming fixtures scheduled.</p>
          ) : (
            <div className="grid grid--3">
              {upcomingGames?.map(game => <GameCard key={game.id} game={game} />)}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
