export default function Players() {
  return (
    <div className="page">
      <div className="container animate-in">
        <header style={{ marginBottom: 'var(--space-8)' }}>
          <h1 style={{ marginBottom: 'var(--space-2)' }}>Players</h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-lg)' }}>
            Player profiles and statistics
          </p>
        </header>

        <div className="card" style={{ textAlign: 'center', padding: 'var(--space-16) var(--space-8)' }}>
          <span style={{ fontSize: '3rem', display: 'block', marginBottom: 'var(--space-4)' }}>🏉</span>
          <h2 style={{ marginBottom: 'var(--space-3)', color: 'var(--color-text-secondary)' }}>Coming Soon</h2>
          <p style={{ color: 'var(--color-text-muted)' }}>
            Player search, profiles, and season statistics are on the way.
          </p>
        </div>
      </div>
    </div>
  )
}
