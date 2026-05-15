import { useState, useMemo } from 'react'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import StatsTable from '../components/Stats/StatsTable'
import { Link } from 'react-router-dom'

export default function Stats() {
  const [activeTab, setActiveTab] = useState('players')
  const [compId, setCompId] = useState('')
  
  const { data: competitions } = useApi(api.getCompetitions)
  
  const { data: playerStats, loading: playersLoading } = useApi(
    () => api.getPlayerStats({ competition_id: compId || undefined }),
    [compId]
  )
  
  const { data: clubStats, loading: clubsLoading } = useApi(
    () => api.getClubStats({ competition_id: compId || undefined }),
    [compId]
  )
  
  const { data: overview, loading: overviewLoading } = useApi(
    () => api.getSeasonOverview({ competition_id: compId || undefined }),
    [compId]
  )

  // Group competitions by parent
  const groupedComps = useMemo(() => {
    if (!competitions) return {}
    return competitions.reduce((acc, c) => {
      const parent = c.parent_competition || 'Other'
      if (!acc[parent]) acc[parent] = []
      acc[parent].push(c)
      return acc
    }, {})
  }, [competitions])

  const renderPlayerRow = (player) => (
    <>
      <td>
        <div className="player-cell">
          <img 
            src={player.image_url || 'https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y'} 
            alt={player.player_name} 
            className="player-avatar"
          />
          <div className="player-info">
            <span className="player-name">{player.player_name}</span>
            <span className="player-club">{player.club_name}</span>
          </div>
        </div>
      </td>
      <td className="stat-value">{player.tries}</td>
      <td className="stat-value">{player.conversions}</td>
      <td className="stat-value">{player.penalties}</td>
      <td className="stat-value">{player.drop_goals}</td>
      <td className="stat-value stat-value--primary">{player.total_points}</td>
      <td className="stat-value" style={{ color: 'var(--color-draw)' }}>{player.yellow_cards}</td>
      <td className="stat-value" style={{ color: 'var(--color-loss)' }}>{player.red_cards}</td>
    </>
  )

  const renderClubRow = (club) => (
    <>
      <td>
        <Link to={`/clubs/${club.club_id}`} className="player-cell" style={{ textDecoration: 'none' }}>
          {club.logo_url ? (
            <img src={club.logo_url} alt={club.club_name} className="player-avatar" style={{ objectFit: 'contain', padding: '2px' }} />
          ) : (
            <div className="player-avatar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--color-bg-glass)', fontSize: '0.6rem' }}>🏉</div>
          )}
          <span className="player-name">{club.club_name}</span>
        </Link>
      </td>
      <td className="stat-value">{club.tries}</td>
      <td className="stat-value">{club.conversions}</td>
      <td className="stat-value">{club.penalties}</td>
      <td className="stat-value stat-value--primary">{club.total_points}</td>
      <td className="stat-value" style={{ color: 'var(--color-draw)' }}>{club.yellow_cards}</td>
      <td className="stat-value" style={{ color: 'var(--color-loss)' }}>{club.red_cards}</td>
    </>
  )

  return (
    <div className="page">
      <div className="container animate-in">
        <header className="stats-header">
          <div>
            <h1 style={{ marginBottom: 'var(--space-2)' }}>Season Stats</h1>
            <p style={{ color: 'var(--color-text-secondary)' }}>
              Top performers and season breakdowns
            </p>
          </div>

          <div className="stats-filter-group">
            <label className="stats-filter-label">Competition</label>
            <select 
              className="stats-select" 
              value={compId} 
              onChange={(e) => setCompId(e.target.value)}
            >
              <option value="">All Competitions</option>
              {Object.entries(groupedComps).map(([parent, comps]) => (
                <optgroup key={parent} label={parent}>
                  {comps.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
        </header>

        <div className="tab-bar">
          <button 
            className={`tab-bar__tab ${activeTab === 'players' ? 'tab-bar__tab--active' : ''}`}
            onClick={() => setActiveTab('players')}
          >
            Players
          </button>
          <button 
            className={`tab-bar__tab ${activeTab === 'clubs' ? 'tab-bar__tab--active' : ''}`}
            onClick={() => setActiveTab('clubs')}
          >
            Clubs
          </button>
          <button 
            className={`tab-bar__tab ${activeTab === 'season' ? 'tab-bar__tab--active' : ''}`}
            onClick={() => setActiveTab('season')}
          >
            Season
          </button>
        </div>

        {activeTab === 'players' && (
          playersLoading ? (
            <div className="skeleton" style={{ height: '500px' }} />
          ) : (
            <StatsTable 
              title="Player Leaderboard"
              headers={[
                { key: 'player', label: 'Player', style: { minWidth: '200px' } },
                { key: 'tries', label: 'Tries' },
                { key: 'conv', label: 'Conv' },
                { key: 'pen', label: 'Pen' },
                { key: 'dg', label: 'DG' },
                { key: 'pts', label: 'Pts' },
                { key: 'yc', label: 'YC' },
                { key: 'rc', label: 'RC' }
              ]}
              data={playerStats || []}
              renderRow={renderPlayerRow}
            />
          )
        )}

        {activeTab === 'clubs' && (
          clubsLoading ? (
            <div className="skeleton" style={{ height: '500px' }} />
          ) : (
            <StatsTable 
              title="Club Scoring & Discipline"
              headers={[
                { key: 'club', label: 'Club', style: { minWidth: '200px' } },
                { key: 'tries', label: 'Tries' },
                { key: 'conv', label: 'Conv' },
                { key: 'pen', label: 'Pen' },
                { key: 'pts', label: 'Pts' },
                { key: 'yc', label: 'YC' },
                { key: 'rc', label: 'RC' }
              ]}
              data={clubStats || []}
              renderRow={renderClubRow}
            />
          )
        )}

        {activeTab === 'season' && (
          overviewLoading ? (
            <div className="skeleton" style={{ height: '400px' }} />
          ) : (
            <div className="overview-grid animate-in">
              <div className="card overview-card">
                <span className="overview-card__icon">🏉</span>
                <span className="overview-card__value">{overview?.total_tries}</span>
                <span className="overview-card__label">Total Tries</span>
                <span className="overview-card__subtext">
                  Incl. penalty tries
                </span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">🔄</span>
                <span className="overview-card__value">{overview?.total_conversions}</span>
                <span className="overview-card__label">Conversions</span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">🎯</span>
                <span className="overview-card__value">{overview?.total_penalties}</span>
                <span className="overview-card__label">Penalty Goals</span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">🏆</span>
                <span className="overview-card__value">{overview?.top_scorer_points}</span>
                <span className="overview-card__label">Top Scorer pts</span>
                <span className="overview-card__subtext">
                  {overview?.top_scorer_name}
                </span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">🥇</span>
                <span className="overview-card__value">{overview?.top_try_scorer_tries}</span>
                <span className="overview-card__label">Most Tries</span>
                <span className="overview-card__subtext">
                  {overview?.top_try_scorer_name}
                </span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">🟡</span>
                <span className="overview-card__value">{overview?.total_yellow_cards}</span>
                <span className="overview-card__label">Yellow Cards</span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">🔴</span>
                <span className="overview-card__value">{overview?.total_red_cards}</span>
                <span className="overview-card__label">Red Cards</span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">📍</span>
                <span className="overview-card__value">{overview?.games_played}</span>
                <span className="overview-card__label">Games Played</span>
              </div>
            </div>
          )
        )}
      </div>
    </div>
  )
}
