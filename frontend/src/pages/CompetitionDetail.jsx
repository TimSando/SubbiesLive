import { useParams, Link } from 'react-router-dom'
import { useState } from 'react'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'

function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric', month: 'short' })
}

function StandingsTable({ standings }) {
  if (!standings?.standings?.length) return null

  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Team</th>
            <th>P</th>
            <th>W</th>
            <th>D</th>
            <th>L</th>
            <th>PF</th>
            <th>PA</th>
            <th>PD</th>
            <th>Pts</th>
          </tr>
        </thead>
        <tbody>
          {standings.standings.map((row, i) => (
            <tr key={row.team_id} className={i < 4 ? 'standings-row--top' : ''}>
              <td style={{ fontWeight: 600, color: i < 4 ? 'var(--color-text-accent)' : 'var(--color-text-secondary)' }}>
                {row.position}
              </td>
              <td>
                <Link to={`/clubs/${row.club_id}`} className="standings-team-link">
                  {row.club_name || row.team_name}
                </Link>
              </td>
              <td>{row.played}</td>
              <td style={{ color: row.won > 0 ? 'var(--color-win)' : undefined }}>{row.won}</td>
              <td>{row.drawn}</td>
              <td style={{ color: row.lost > 0 ? 'var(--color-loss)' : undefined }}>{row.lost}</td>
              <td>{row.points_for}</td>
              <td>{row.points_against}</td>
              <td style={{
                color: row.points_diff > 0 ? 'var(--color-win)' : row.points_diff < 0 ? 'var(--color-loss)' : undefined,
                fontWeight: 500
              }}>
                {row.points_diff > 0 ? '+' : ''}{row.points_diff}
              </td>
              <td style={{ fontWeight: 700, color: 'var(--color-text-primary)' }}>{row.competition_points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function GamesForRound({ competitionId, round }) {
  const { data: games, loading } = useApi(
    () => api.getGames({ competition_id: competitionId, round_id: round.id, limit: 20 }),
    [round.id]
  )

  if (loading) return <div className="skeleton" style={{ height: '60px', marginBottom: 'var(--space-2)' }} />

  if (!games?.length) return <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>No games</p>

  return (
    <div className="round-games">
      {games.map(game => {
        const isCompleted = game.status === 'completed'
        const homeWin = isCompleted && game.home_score > game.away_score
        const awayWin = isCompleted && game.away_score > game.home_score

        return (
          <Link to={`/games/${game.id}`} key={game.id} className="fixture-row" id={`fixture-${game.id}`}>
            <span className="fixture-row__date">{formatDate(game.game_date)}</span>
            <span className={`fixture-row__team fixture-row__team--home ${homeWin ? 'fixture-row__team--winner' : ''}`}>
              {game.home_team.club_name || game.home_team.name}
            </span>
            <span className="fixture-row__score--home">
              {isCompleted ? (
                <span className={homeWin ? 'score--winner' : ''}>{game.home_score}</span>
              ) : <span style={{ color: 'var(--color-text-muted)' }}>-</span>}
            </span>
            <span className="fixture-row__score--dash">—</span>
            <span className="fixture-row__score--away">
              {isCompleted ? (
                <span className={awayWin ? 'score--winner' : ''}>{game.away_score}</span>
              ) : <span style={{ color: 'var(--color-text-muted)' }}>-</span>}
            </span>
            <span className={`fixture-row__team fixture-row__team--away ${awayWin ? 'fixture-row__team--winner' : ''}`}>
              {game.away_team.club_name || game.away_team.name}
            </span>
            <span className="fixture-row__location">
              {game.location ? `📍 ${game.location}` : ''}
            </span>
          </Link>
        )
      })}
    </div>
  )
}

export default function CompetitionDetail() {
  const { id } = useParams()
  const [activeTab, setActiveTab] = useState('standings')
  const [selectedRound, setSelectedRound] = useState(null)

  const { data: competition, loading: loadingComp } = useApi(
    () => api.getCompetition(id), [id]
  )
  const { data: standings, loading: loadingStandings } = useApi(
    () => api.getStandings(id), [id]
  )

  if (loadingComp) {
    return (
      <div className="page">
        <div className="container">
          <div className="skeleton" style={{ height: '40px', width: '300px', marginBottom: 'var(--space-4)' }} />
          <div className="skeleton" style={{ height: '400px' }} />
        </div>
      </div>
    )
  }

  if (!competition) {
    return (
      <div className="page">
        <div className="container">
          <h1>Competition not found</h1>
          <Link to="/competitions" className="btn btn--ghost" style={{ marginTop: 'var(--space-4)' }}>
            ← Back to Competitions
          </Link>
        </div>
      </div>
    )
  }

  const now = new Date()
  const allRounds = competition.rounds?.filter(r => r.game_count > 0) || []
  const completedRounds = allRounds.filter(r => r.completed_game_count > 0)

  // Among those, find the one whose latest_game_date is closest to (but not after) today
  const lastCompletedRound = completedRounds.reduce((best, round) => {
    const roundDate = round.latest_game_date ? new Date(round.latest_game_date) : null
    if (!roundDate || roundDate > now) return best
    if (!best) return round
    const bestDate = new Date(best.latest_game_date)
    return roundDate > bestDate ? round : best
  }, null)

  // Use lastCompletedRound as default if no round is selected
  const currentRound = selectedRound || lastCompletedRound

  return (
    <div className="page">
      <div className="container animate-in">
        <Link to="/competitions" className="breadcrumb">← All Competitions</Link>

        <header style={{ marginBottom: 'var(--space-8)' }}>
          <h1 style={{ marginBottom: 'var(--space-2)' }}>{competition.name}</h1>
          <p style={{ color: 'var(--color-text-secondary)' }}>
            {competition.team_count} teams · {competition.rounds?.length} rounds
          </p>
        </header>

        {/* Tab bar */}
        <div className="tab-bar">
          <button
            className={`tab-bar__tab ${activeTab === 'standings' ? 'tab-bar__tab--active' : ''}`}
            onClick={() => setActiveTab('standings')}
          >
            Standings
          </button>
          <button
            className={`tab-bar__tab ${activeTab === 'fixtures' ? 'tab-bar__tab--active' : ''}`}
            onClick={() => {
              setActiveTab('fixtures')
              if (!selectedRound && lastCompletedRound) {
                setSelectedRound(lastCompletedRound)
              }
            }}
          >
            Fixtures & Results
          </button>
        </div>

        {/* Standings Tab */}
        {activeTab === 'standings' && (
          <section className="comp-section">
            {loadingStandings ? (
              <div className="skeleton" style={{ height: '400px' }} />
            ) : (
              <StandingsTable standings={standings} />
            )}
          </section>
        )}

        {/* Fixtures Tab */}
        {activeTab === 'fixtures' && (
          <section className="comp-section">
            {/* Round selector */}
            <div className="round-selector">
              {allRounds.map(round => (
                <button
                  key={round.id}
                  className={`round-selector__btn ${currentRound?.id === round.id ? 'round-selector__btn--active' : ''}`}
                  onClick={() => setSelectedRound(round)}
                >
                  {round.name}
                </button>
              ))}
            </div>

            {currentRound && (
              <div style={{ marginTop: 'var(--space-6)' }}>
                <h3 style={{ marginBottom: 'var(--space-4)' }}>{currentRound.name}</h3>
                <GamesForRound competitionId={id} round={currentRound} />
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  )
}
