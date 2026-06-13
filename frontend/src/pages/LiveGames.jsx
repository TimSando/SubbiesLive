import GamePill from '../components/GamePill/GamePill.jsx'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'
import { Link, useNavigate } from 'react-router-dom'

export default function LiveGames() {
  const navigate = useNavigate()
  const { data: liveGames, loading } = useApi(() => api.getLiveGames(), [])

  return (
    <div className="page">
      <div className="container animate-in">
        <Link to="/" className="breadcrumb" onClick={(e) => { e.preventDefault(); navigate(-1) }}>← Back</Link>
        <header style={{ marginBottom: 'var(--space-8)' }}>
          <h1>Live Matches</h1>
        </header>
        {loading ? (
          <div className="skeleton" style={{ height: '200px' }} />
        ) : liveGames?.length > 0 ? (
          <div className="grid grid--3">
            {liveGames.map(game => <GamePill key={game.id} game={game} />)}
          </div>
        ) : (
          <p style={{ color: 'var(--color-text-muted)' }}>There are no live matches right now.</p>
        )}
      </div>
    </div>
  )
}
