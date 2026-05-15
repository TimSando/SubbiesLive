import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'

function ClubCard({ club }) {
  const totalGames = club.wins + club.losses + club.draws

  return (
    <Link to={`/clubs/${club.id}`} className="card card--clickable club-card" id={`club-${club.id}`}>
      <div className="club-card__header">
        {club.logo_url ? (
          <img
            src={club.logo_url}
            alt={`${club.name} logo`}
            className="club-card__logo"
            onError={(e) => { e.target.style.display = 'none' }}
          />
        ) : (
          <div className="club-card__logo-placeholder">🏉</div>
        )}
        <h3 className="club-card__name">{club.name}</h3>
      </div>
      {totalGames > 0 && (
        <div className="club-card__record">
          <span className="club-card__stat club-card__stat--win">{club.wins}W</span>
          <span className="club-card__stat club-card__stat--loss">{club.losses}L</span>
          {club.draws > 0 && (
            <span className="club-card__stat club-card__stat--draw">{club.draws}D</span>
          )}
        </div>
      )}
      <div className="club-card__footer">
        <span className="club-card__teams">{club.team_count} {club.team_count === 1 ? 'team' : 'teams'}</span>
      </div>
    </Link>
  )
}

export default function Clubs() {
  const { data: clubs, loading, error } = useApi(() => api.getClubs(), [])

  // Group clubs by parent_competition + division
  const grouped = {}
  if (clubs) {
    for (const club of clubs) {
      const mapping = club.competition_mapping
      const parent = mapping?.parent_competition || 'Other'
      const div = mapping?.division ? `Division ${mapping.division}` : null
      const key = div ? `${parent} — ${div}` : parent

      if (!grouped[key]) {
        grouped[key] = { parent, division: mapping?.division, clubs: [] }
      }
      grouped[key].clubs.push(club)
    }
  }

  // Sort groups: Shute Shield first, then Suburban by division, then Other
  const sortedKeys = Object.keys(grouped).sort((a, b) => {
    const ga = grouped[a]
    const gb = grouped[b]
    if (ga.parent === 'Shute Shield' && gb.parent !== 'Shute Shield') return -1
    if (gb.parent === 'Shute Shield' && ga.parent !== 'Shute Shield') return 1
    if (ga.parent === 'Other') return 1
    if (gb.parent === 'Other') return -1
    const da = ga.division ? parseInt(ga.division) : 99
    const db_ = gb.division ? parseInt(gb.division) : 99
    return da - db_
  })

  return (
    <div className="page">
      <div className="container animate-in">
        <header style={{ marginBottom: 'var(--space-8)' }}>
          <h1 style={{ marginBottom: 'var(--space-2)' }}>Clubs</h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-lg)' }}>
            All {clubs?.length || ''} clubs across competitions
          </p>
        </header>

        {loading && (
          <div className="grid grid--3">
            {[1,2,3,4,5,6].map(i => (
              <div key={i} className="skeleton" style={{ height: '120px' }} />
            ))}
          </div>
        )}

        {error && (
          <div className="card" style={{ color: 'var(--color-loss)' }}>
            Failed to load clubs: {error}
          </div>
        )}

        {clubs && sortedKeys.map(key => (
          <section key={key} className="clubs-section">
            <h2 className="clubs-section__title">{key}</h2>
            <div className="grid grid--3">
              {grouped[key].clubs.map(club => (
                <ClubCard key={club.id} club={club} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  )
}
