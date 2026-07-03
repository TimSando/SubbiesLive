import { useState, useMemo, Fragment, useEffect, useRef } from 'react'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import StatsTable from '../components/Stats/StatsTable'
import ToggleSwitch from '../components/Stats/ToggleSwitch'
import { Link } from 'react-router-dom'
import { formatDivisionName } from '../utils/format.js'

export default function Stats() {
  const [hasLiveGames, setHasLiveGames] = useState(false)
  const [activeTab, setActiveTab] = useState(() => sessionStorage.getItem('stats_activeTab') || 'players')
  const [filter, setFilter] = useState(() => {
    const cached = sessionStorage.getItem('stats_filter')
    return cached ? JSON.parse(cached) : { type: 'all', value: '' }
  })
  const [viewMode, setViewMode] = useState(() => sessionStorage.getItem('stats_viewMode') || 'total')
  
  const [searchQuery, setSearchQuery] = useState(() => sessionStorage.getItem('stats_searchQuery') || '')

  useEffect(() => {
    async function checkLive() {
      try {
        const live = await api.getLiveGames()
        setHasLiveGames(live && live.length > 0)
      } catch (e) {
        console.error('Failed to fetch live games for stats page:', e)
      }
    }
    checkLive()
  }, [])

  useEffect(() => {
    sessionStorage.setItem('stats_activeTab', activeTab)
  }, [activeTab])

  useEffect(() => {
    sessionStorage.setItem('stats_filter', JSON.stringify(filter))
  }, [filter])

  useEffect(() => {
    sessionStorage.setItem('stats_viewMode', viewMode)
  }, [viewMode])

  useEffect(() => {
    sessionStorage.setItem('stats_searchQuery', searchQuery)
  }, [searchQuery])
  const [searchResults, setSearchResults] = useState([])
  const searchRef = useRef(null)

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      return
    }

    const timer = setTimeout(async () => {
      try {
        const res = await api.getPlayers({ search: searchQuery })
        setSearchResults(res || [])
      } catch (err) {
        console.error('Error searching players:', err)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [searchQuery])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setSearchResults([])
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])
  
  const { data: competitions } = useApi(api.getCompetitions)
  
  const filterParams = useMemo(() => {
    const params = {}
    if (filter.type === 'comp') params.competition_id = filter.value
    if (filter.type === 'parent') params.parent_competition = filter.value
    if (filter.type === 'division') params.division = filter.value
    return params
  }, [filter])

  const { data: playerStats, loading: playersLoading, error: playersError } = useApi(
    () => api.getPlayerStats(filterParams),
    [filterParams]
  )
  
  const { data: clubStats, loading: clubsLoading, error: clubsError } = useApi(
    () => api.getClubStats(filterParams),
    [filterParams]
  )

  const { data: clubDepthStats, loading: clubDepthLoading, error: clubDepthError } = useApi(
    () => api.getClubDepthStats(filterParams),
    [filterParams]
  )
  
  const { data: overview, loading: overviewLoading, error: overviewError } = useApi(
    () => api.getSeasonOverview(filterParams),
    [filterParams]
  )

  const statsError = playersError || clubsError || clubDepthError || overviewError

  // Group competitions by parent then division
  const groupedHierarchy = useMemo(() => {
    if (!competitions) return {}
    return competitions.reduce((acc, c) => {
      const parent = c.parent_competition || 'Other'
      if (!acc[parent]) acc[parent] = { competitions: [], divisions: {} }
      
      if (c.division) {
        if (!acc[parent].divisions[c.division]) acc[parent].divisions[c.division] = []
        acc[parent].divisions[c.division].push(c)
      } else {
        acc[parent].competitions.push(c)
      }
      return acc
    }, {})
  }, [competitions])

  const handleFilterChange = (e) => {
    const [type, ...rest] = e.target.value.split(':')
    const value = rest.join(':')
    setFilter({ type, value })
  }

  const NUMERIC_STAT_KEYS = ['tries', 'conversions', 'penalties', 'drop_goals', 'total_points', 'yellow_cards', 'red_cards']

  const applyViewMode = useMemo(() => (rows) => {
    if (viewMode === 'total') return rows
    return rows
      .map(row => {
        const gp = row.games_played || 1
        const avg = {}
        NUMERIC_STAT_KEYS.forEach(k => {
          avg[k] = row[k] / gp
        })
        return { ...row, ...avg }
      })
      .sort((a, b) => b.total_points - a.total_points)
      .map((row, i) => ({ ...row, rank: i + 1 }))
  }, [viewMode])

  const displayedPlayerStats = useMemo(() => 
    applyViewMode(playerStats || []), [playerStats, applyViewMode])

  const displayedClubStats = useMemo(() => 
    applyViewMode(clubStats || []), [clubStats, applyViewMode])

  const displayedClubDepthStats = useMemo(() => 
    (clubDepthStats || []).map((row, i) => ({ ...row, rank: i + 1 })), [clubDepthStats])

  const formatStat = (val) => {
    if (viewMode === 'total') return val
    return val.toFixed(2)
  }

  const getSeasonValue = (totalValue) => {
    if (!overview || overview.games_played === 0) return 0
    if (viewMode === 'total') return totalValue
    return (totalValue / overview.games_played).toFixed(2)
  }

  const topAveragePerformers = useMemo(() => {
    if (!playerStats || playerStats.length === 0) return null

    const playersWithAvg = playerStats.map(p => ({
      ...p,
      avgPoints: p.games_played > 0 ? p.total_points / p.games_played : 0,
      avgTries: p.games_played > 0 ? p.tries / p.games_played : 0
    }))

    const topScorer = [...playersWithAvg].sort((a, b) => b.avgPoints - a.avgPoints)[0]
    const topTryScorer = [...playersWithAvg].sort((a, b) => b.avgTries - a.avgTries)[0]

    return { topScorer, topTryScorer }
  }, [playerStats])

  const renderPlayerRow = (player) => (
    <>
      <td>
        <Link to={`/players/${player.player_id}`} className="player-cell" style={{ textDecoration: 'none' }}>
          <img 
            src="https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y" 
            alt={player.player_name} 
            className="player-avatar"
          />
          <div className="player-info">
            <span className="player-name" style={{ color: 'var(--color-accent-primary)' }}>{player.player_name}</span>
            <span className="player-club">{player.club_name}</span>
          </div>
        </Link>
      </td>
      <td className="stat-value">{player.games_played}</td>
      <td className="stat-value">{formatStat(player.tries)}</td>
      <td className="stat-value">{formatStat(player.conversions)}</td>
      <td className="stat-value">{formatStat(player.penalties)}</td>
      <td className="stat-value">{formatStat(player.drop_goals)}</td>
      <td className="stat-value stat-value--primary">{formatStat(player.total_points)}</td>
      <td className="stat-value" style={{ color: 'var(--color-draw)' }}>{formatStat(player.yellow_cards)}</td>
      <td className="stat-value" style={{ color: 'var(--color-loss)' }}>{formatStat(player.red_cards)}</td>
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
      <td className="stat-value">{club.games_played}</td>
      <td className="stat-value">{formatStat(club.tries)}</td>
      <td className="stat-value">{formatStat(club.conversions)}</td>
      <td className="stat-value">{formatStat(club.penalties)}</td>
      <td className="stat-value">{formatStat(club.drop_goals)}</td>
      <td className="stat-value stat-value--primary">{formatStat(club.total_points)}</td>
      <td className="stat-value" style={{ color: 'var(--color-draw)' }}>{formatStat(club.yellow_cards)}</td>
      <td className="stat-value" style={{ color: 'var(--color-loss)' }}>{formatStat(club.red_cards)}</td>
    </>
  )

  const renderClubDepthRow = (club) => (
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
      <td className="stat-value">{club.total_players}</td>
      <td className="stat-value">{club.core_players}</td>
      <td className="stat-value">{club.dedicated_players}</td>
      <td className="stat-value">{club.swing_players}</td>
      <td className="stat-value stat-value--primary">{club.avg_games.toFixed(2)}</td>
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
            <label className="stats-filter-label" htmlFor="stats-filter-select">Filter By</label>
            <select 
              id="stats-filter-select"
              className="stats-select" 
              value={`${filter.type}:${filter.value}`} 
              onChange={handleFilterChange}
              style={{ minWidth: '280px' }}
            >
              <option value="all:">All Competitions</option>
              {Object.entries(groupedHierarchy).map(([parent, data]) => (
                <Fragment key={parent}>
                  <option value={`parent:${parent}`} style={{ fontWeight: 'bold', background: 'rgba(255,255,255,0.05)' }}>
                    {parent} (All)
                  </option>
                  
                  {/* Divisions */}
                  {Object.entries(data.divisions).sort().map(([div, comps]) => (
                    <Fragment key={`${parent}-${div}`}>
                      <option value={`division:${div}`}>
                        &nbsp;&nbsp;{formatDivisionName(div)} (All)
                      </option>
                      {comps.map(c => (
                        <option key={c.id} value={`comp:${c.id}`}>
                          &nbsp;&nbsp;&nbsp;&nbsp;{c.name}
                        </option>
                      ))}
                    </Fragment>
                  ))}

                  {/* Competitions without division */}
                  {data.competitions.map(c => (
                    <option key={c.id} value={`comp:${c.id}`}>
                      &nbsp;&nbsp;{c.name}
                    </option>
                  ))}
                </Fragment>
              ))}
            </select>
          </div>

          <div className="stats-filter-group">
            <label className="stats-filter-label">View Mode</label>
            <ToggleSwitch value={viewMode} onChange={setViewMode} />
          </div>
        </header>

        {statsError && (
          <div className="alert-danger" style={{ marginBottom: 'var(--space-4)' }}>
            Failed to load stats: {statsError}
          </div>
        )}

        {hasLiveGames && (
          <div style={{
            background: 'var(--color-live-bg)',
            border: '1px solid var(--color-live)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-3) var(--space-4)',
            marginBottom: 'var(--space-4)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)',
            color: 'var(--color-text-primary)',
            fontSize: 'var(--font-size-sm)'
          }}>
            <span className="live-dot" />
            <span>
              <strong>Live updates active:</strong> Stats include live, in-progress game data and will update as matches progress.
            </span>
          </div>
        )}

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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <div ref={searchRef} className="player-search-container" style={{ position: 'relative', width: '100%', maxWidth: '400px' }}>
              <input
                type="text"
                placeholder="🔍 Search for any player..."
                className="stats-select"
                style={{ width: '100%', padding: '10px 16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', background: 'var(--color-bg-glass)' }}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchResults.length > 0 && (
                <div 
                  className="autocomplete-dropdown card"
                  style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    width: '100%',
                    zIndex: 10,
                    marginTop: '4px',
                    maxHeight: '300px',
                    overflowY: 'auto',
                    background: 'rgba(20, 20, 20, 0.95)',
                    backdropFilter: 'blur(20px)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '8px',
                    padding: 'var(--space-2)'
                  }}
                >
                  {searchResults.map(p => (
                    <Link 
                      key={p.id} 
                      to={`/players/${p.id}`} 
                      className="player-cell"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '8px 12px',
                        textDecoration: 'none',
                        borderRadius: '6px',
                        transition: 'background 0.2s',
                        cursor: 'pointer'
                      }}
                      onClick={() => {
                        setSearchQuery('')
                        setSearchResults([])
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <img 
                        src="https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y" 
                        alt={p.name} 
                        className="player-avatar"
                        style={{ marginRight: '12px' }}
                      />
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span className="player-name" style={{ color: 'var(--color-text-primary)', fontSize: '0.95rem' }}>{p.name}</span>
                        {p.current_team && <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>{p.current_team}</span>}
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {playersLoading ? (
              <div className="skeleton" style={{ height: '500px' }} />
            ) : (
              <StatsTable 
                title="Player Leaderboard"
                headers={[
                  { key: 'player_name', label: 'Player', style: { minWidth: '200px' } },
                  { key: 'games_played', label: 'Games' },
                  { key: 'tries', label: 'Tries' },
                  { key: 'conversions', label: 'Conv' },
                  { key: 'penalties', label: 'Pen' },
                  { key: 'drop_goals', label: 'DG' },
                  { key: 'total_points', label: 'Pts' },
                  { key: 'yellow_cards', label: 'YC' },
                  { key: 'red_cards', label: viewMode === 'total' ? 'RC' : 'Avg RC' }
                ]}
                data={displayedPlayerStats}
                renderRow={renderPlayerRow}
                viewMode={viewMode}
                paged={true}
                pageSize={10}
              />
            )}
          </div>
        )}

        {activeTab === 'clubs' && (
          clubsLoading || clubDepthLoading ? (
            <div className="skeleton" style={{ height: '500px' }} />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
              <StatsTable 
                title="Club Scoring & Discipline"
                headers={[
                  { key: 'club_name', label: 'Club', style: { minWidth: '200px' } },
                  { key: 'games_played', label: 'Games' },
                  { key: 'tries', label: 'Tries' },
                  { key: 'conversions', label: 'Conv' },
                  { key: 'penalties', label: 'Pen' },
                  { key: 'drop_goals', label: 'DG' },
                  { key: 'total_points', label: 'Pts' },
                  { key: 'yellow_cards', label: 'YC' },
                  { key: 'red_cards', label: viewMode === 'total' ? 'RC' : 'Avg RC' }
                ]}
                data={displayedClubStats}
                renderRow={renderClubRow}
                viewMode={viewMode}
                paged={true}
                pageSize={10}
              />

              <StatsTable 
                title="Squad Depth & Participation"
                headers={[
                  { key: 'club_name', label: 'Club', style: { minWidth: '200px' } },
                  { key: 'total_players', label: 'Active Players' },
                  { key: 'core_players', label: 'Core (>=5 Games)' },
                  { key: 'dedicated_players', label: 'Dedicated (1 Grade)' },
                  { key: 'swing_players', label: 'Swing (>=2 Grades)' },
                  { key: 'avg_games', label: 'Avg Games/Player' }
                ]}
                data={displayedClubDepthStats}
                renderRow={renderClubDepthRow}
                viewMode="total"
                paged={true}
                pageSize={10}
              />
            </div>
          )
        )}

        {activeTab === 'season' && (
          overviewLoading ? (
            <div className="skeleton" style={{ height: '400px' }} />
          ) : (
            <div className="overview-grid animate-in">
              <div className="card overview-card">
                <span className="overview-card__icon">🏉</span>
                <span className="overview-card__value">{getSeasonValue(overview?.total_tries)}</span>
                <span className="overview-card__label">
                  {viewMode === 'total' ? 'Total Tries' : 'Avg Tries/Game'}
                </span>
                <span className="overview-card__subtext">
                  Incl. penalty tries
                </span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">🔄</span>
                <span className="overview-card__value">{getSeasonValue(overview?.total_conversions)}</span>
                <span className="overview-card__label">
                  {viewMode === 'total' ? 'Conversions' : 'Avg Conversions/Game'}
                </span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">🎯</span>
                <span className="overview-card__value">{getSeasonValue(overview?.total_penalties)}</span>
                <span className="overview-card__label">
                  {viewMode === 'total' ? 'Penalty Goals' : 'Avg Penalty Goals/Game'}
                </span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">🏆</span>
                <span className="overview-card__value">
                  {viewMode === 'total' 
                    ? overview?.top_scorer_points 
                    : (playersLoading ? '...' : topAveragePerformers?.topScorer?.avgPoints?.toFixed(2))}
                </span>
                <span className="overview-card__label">
                  {viewMode === 'total' ? 'Top Scorer pts' : 'Top Avg Pts/Game'}
                </span>
                <span className="overview-card__subtext">
                  {viewMode === 'total' 
                    ? overview?.top_scorer_name 
                    : (playersLoading ? 'Loading...' : (topAveragePerformers?.topScorer?.player_name ? `${topAveragePerformers.topScorer.player_name} (${topAveragePerformers.topScorer.club_name})` : 'N/A'))}
                </span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">🥇</span>
                <span className="overview-card__value">
                  {viewMode === 'total' 
                    ? overview?.top_try_scorer_tries 
                    : (playersLoading ? '...' : topAveragePerformers?.topTryScorer?.avgTries?.toFixed(2))}
                </span>
                <span className="overview-card__label">
                  {viewMode === 'total' ? 'Most Tries' : 'Most Tries/Game'}
                </span>
                <span className="overview-card__subtext">
                  {viewMode === 'total' 
                    ? overview?.top_try_scorer_name 
                    : (playersLoading ? 'Loading...' : (topAveragePerformers?.topTryScorer?.player_name ? `${topAveragePerformers.topTryScorer.player_name} (${topAveragePerformers.topTryScorer.club_name})` : 'N/A'))}
                </span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">🟡</span>
                <span className="overview-card__value">{getSeasonValue(overview?.total_yellow_cards)}</span>
                <span className="overview-card__label">
                  {viewMode === 'total' ? 'Yellow Cards' : 'Avg Yellow Cards/Game'}
                </span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">🔴</span>
                <span className="overview-card__value">{getSeasonValue(overview?.total_red_cards)}</span>
                <span className="overview-card__label">
                  {viewMode === 'total' ? 'Red Cards' : 'Avg Red Cards/Game'}
                </span>
              </div>
              <div className="card overview-card">
                <span className="overview-card__icon">📍</span>
                <span className="overview-card__value">{overview?.games_played}</span>
                <span className="overview-card__label">Games Played</span>
                {viewMode !== 'total' && (
                  <span className="overview-card__subtext">
                    Total games in selection
                  </span>
                )}
              </div>
            </div>
          )
        )}
      </div>
    </div>
  )
}
