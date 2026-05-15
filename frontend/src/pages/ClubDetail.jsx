import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'

export default function ClubDetail() {
  const { id } = useParams()
  const { data: club, loading } = useApi(() => api.getClub(id), [id])

  if (loading) {
    return (
      <div className="page"><div className="container">
        <div className="skeleton" style={{ height: '40px', width: '250px', marginBottom: 'var(--space-4)' }} />
        <div className="skeleton" style={{ height: '200px' }} />
      </div></div>
    )
  }

  if (!club) {
    return (
      <div className="page"><div className="container">
        <h1>Club not found</h1>
        <Link to="/competitions" className="btn btn--ghost" style={{ marginTop: 'var(--space-4)' }}>← Back</Link>
      </div></div>
    )
  }

  return (
    <div className="page">
      <div className="container animate-in">
        <Link to="/competitions" className="breadcrumb">← Competitions</Link>
        <header className="club-header">
          {club.logo_url && (
            <img src={club.logo_url} alt={`${club.name} logo`} className="club-header__logo"
              onError={(e) => { e.target.style.display = 'none' }} />
          )}
          <div>
            <h1 style={{ marginBottom: 'var(--space-2)' }}>{club.name}</h1>
            <p style={{ color: 'var(--color-text-secondary)' }}>
              {club.teams?.length || 0} teams across competitions
            </p>
          </div>
        </header>
        <section style={{ marginTop: 'var(--space-8)' }}>
          <h2 style={{ marginBottom: 'var(--space-6)' }}>Teams</h2>
          <div className="grid grid--2">
            {club.teams?.map(team => (
              <div key={team.id} className="card" id={`team-${team.id}`}>
                <h3 style={{ marginBottom: 'var(--space-2)', fontSize: 'var(--font-size-lg)' }}>
                  {team.competition_name}
                </h3>
                <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                  {team.name}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
