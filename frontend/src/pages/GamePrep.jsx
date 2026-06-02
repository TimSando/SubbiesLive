import { useParams, Link, useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'

export default function GamePrep() {
  const { id } = useParams()
  const navigate = useNavigate()

  // 1. Fetch upcoming game details
  const { data: game, loading: gameLoading } = useApi(() => api.getGame(id), [id])

  // 2. Fetch recent matches (Scores) for both teams
  const { data: homeGames } = useApi(
    () => game ? api.getGames({ team_id: game.home_team.id, status: 'completed', limit: 5 }) : Promise.resolve([]),
    [game?.home_team?.id]
  )
  const { data: awayGames } = useApi(
    () => game ? api.getGames({ team_id: game.away_team.id, status: 'completed', limit: 5 }) : Promise.resolve([]),
    [game?.away_team?.id]
  )

  // 3. Fetch detailed form stats (Tries, Cards) for both teams
  const { data: homeStats } = useApi(
    () => game ? api.getTeamFormStats(game.home_team.id) : Promise.resolve(null),
    [game?.home_team?.id]
  )
  const { data: awayStats } = useApi(
    () => game ? api.getTeamFormStats(game.away_team.id) : Promise.resolve(null),
    [game?.away_team?.id]
  )

  // 4. Fetch standings/ladder for competition to get team ranks
  const { data: standings } = useApi(
    () => game ? api.getStandings(game.competition_id) : Promise.resolve(null),
    [game?.competition_id]
  )

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

  if (gameLoading) {
    return (
      <div className="page">
        <div className="container">
          <div className="skeleton" style={{ height: '400px', borderRadius: 'var(--radius-xl)' }} />
        </div>
      </div>
    )
  }

  if (!game) {
    return (
      <div className="page">
        <div className="container" style={{ textAlign: 'center', paddingTop: 'var(--space-12)' }}>
          <h1 style={{ marginBottom: 'var(--space-4)' }}>Game not found</h1>
          <Link to="/refzone" className="btn btn--ghost">← Back to RefZone</Link>
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

  const matchDate = new Date(game.game_date)
  const timeStr = matchDate.toLocaleTimeString('en-AU', {
    timeZone: 'Australia/Sydney',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })

  const dateStr = matchDate.toLocaleDateString('en-AU', {
    timeZone: 'Australia/Sydney',
    weekday: 'short',
    day: 'numeric',
    month: 'short'
  })

  return (
    <div className="page">
      <div className="container animate-in">
        <Link to="/refzone" className="breadcrumb" onClick={(e) => { e.preventDefault(); navigate(-1); }}>
          ← Back to RefZone
        </Link>
        
        <div className="match-header card" style={{ marginBottom: 'var(--space-8)', position: 'relative', overflow: 'hidden' }}>
          {/* Top subtle green accent line */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '3px',
            background: 'linear-gradient(90deg, transparent, var(--color-accent-primary), transparent)'
          }} />

          <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-extrabold)', marginBottom: 'var(--space-2)' }}>
            Match Preparation Dashboard
          </h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-base)', margin: 0 }}>
            {game.competition_name} • {game.round_name}
          </p>
          
          <div style={{ display: 'inline-flex', flexWrap: 'wrap', gap: 'var(--space-4)', marginTop: 'var(--space-4)', padding: 'var(--space-2) var(--space-4)', background: 'var(--color-bg-glass)', borderRadius: 'var(--radius-full)', border: '1px solid var(--color-border)' }}>
             <span style={{ color: 'var(--color-text-accent)', fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', display: 'flex', alignItems: 'center', gap: '4px' }}>
               📍 {game.location || 'TBD Venue'}
             </span>
             <span style={{ color: 'var(--color-text-primary)', fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', display: 'flex', alignItems: 'center', gap: '4px' }}>
               📅 {dateStr}
             </span>
             <span style={{ color: 'var(--color-text-primary)', fontSize: 'var(--font-size-xs)', fontWeight: 'var(--font-weight-semibold)', display: 'flex', alignItems: 'center', gap: '4px' }}>
               ⏰ {timeStr}
             </span>
          </div>
        </div>

        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--space-6)' }}>
          {renderTeamDashboard(game.home_team, homeGames, homeStats, getTeamRank(game.home_team.id))}
          {renderTeamDashboard(game.away_team, awayGames, awayStats, getTeamRank(game.away_team.id))}
        </div>
      </div>
    </div>
  )
}
