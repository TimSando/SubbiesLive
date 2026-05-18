import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'

export default function Competitions() {
  const { data: competitions, loading, error } = useApi(() => api.getCompetitions(), [])

  // Filter states preserved in sessionStorage
  const [searchQuery, setSearchQuery] = useState(() => sessionStorage.getItem('competitions_clubQuery') || '')

  useEffect(() => {
    sessionStorage.setItem('competitions_clubQuery', searchQuery)
  }, [searchQuery])

  // Sorting helper for divisions
  const sortDivs = (divs) => Object.keys(divs).sort((a, b) => {
    if (a === 'General') return -1
    if (b === 'General') return 1
    const na = parseInt(a), nb = parseInt(b)
    if (!isNaN(na) && !isNaN(nb)) return na - nb
    return a.localeCompare(b)
  })

  // Sorting helper for grades within a division
  const sortGrades = (comps) => comps.sort((a, b) => {
    const ga = a.grade || '99', gb = b.grade || '99'
    if (ga === 'Colts' && gb !== 'Colts') return 1
    if (gb === 'Colts' && ga !== 'Colts') return -1
    return ga.localeCompare(gb)
  })

  // Client-side filtering logic (matches club involvement or competition names)
  const filteredComps = (competitions || []).filter(comp => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    
    const matchesClub = comp.club_names?.toLowerCase().includes(q)
    const matchesCompName = comp.name?.toLowerCase().includes(q)
    
    return matchesClub || matchesCompName
  })

  // Build grouped structures
  const grouped = {}
  for (const comp of filteredComps) {
    const parent = comp.parent_competition || 'Other'
    const div = comp.division ? `${comp.division}` : 'General'
    
    if (!grouped[parent]) {
      grouped[parent] = {}
    }
    if (!grouped[parent][div]) {
      grouped[parent][div] = []
    }
    grouped[parent][div].push(comp)
  }

  // Define parent sort order
  const parentOrder = ['Shute Shield', 'Suburban Rugby Union', 'Other']
  const existingParents = Object.keys(grouped).sort((a, b) => {
    const idxA = parentOrder.indexOf(a)
    const idxB = parentOrder.indexOf(b)
    if (idxA !== -1 && idxB !== -1) return idxA - idxB
    if (idxA !== -1) return -1
    if (idxB !== -1) return 1
    return a.localeCompare(b)
  })

  return (
    <div className="page">
      <div className="container animate-in" style={{ maxWidth: '1000px' }}>
        <header style={{ marginBottom: 'var(--space-8)' }}>
          <h1 style={{ marginBottom: 'var(--space-2)' }}>Competitions</h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-lg)' }}>
            Browse match series, active standings, and fixtures across all leagues
          </p>
        </header>

        {/* Sleek Filter & Search Bar */}
        <div className="clubs-filter-bar" style={{ marginBottom: 'var(--space-8)' }}>
          <div className="clubs-search-input" style={{ flex: 1 }}>
            <span className="clubs-search-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.6 }}>
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </span>
            <input
              type="text"
              placeholder="Search by club name or competition name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{
                  position: 'absolute',
                  right: '14px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: 'var(--color-text-muted)',
                  cursor: 'pointer',
                  fontSize: 'var(--font-size-lg)',
                }}
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {loading && (
          <div className="comp-rows-container">
            <div className="skeleton" style={{ height: '80px', borderRadius: 'var(--radius-xl)', marginBottom: 'var(--space-3)' }} />
            <div className="skeleton" style={{ height: '80px', borderRadius: 'var(--radius-xl)', marginBottom: 'var(--space-3)' }} />
            <div className="skeleton" style={{ height: '80px', borderRadius: 'var(--radius-xl)' }} />
          </div>
        )}

        {error && (
          <div className="card" style={{ color: 'var(--color-loss)', padding: 'var(--space-6)', borderRadius: 'var(--radius-xl)', border: '1px solid rgba(239, 68, 68, 0.2)', background: 'rgba(239, 68, 68, 0.05)' }}>
            Failed to load competitions: {error}
          </div>
        )}

        {competitions && filteredComps.length === 0 && (
          <div className="card" style={{ textAlign: 'center', padding: 'var(--space-12)', color: 'var(--color-text-secondary)', background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: 'var(--radius-xl)' }}>
            <div style={{ fontSize: '3rem', marginBottom: 'var(--space-4)' }}>🔍</div>
            <h3>No competitions match your search</h3>
            <p style={{ marginTop: 'var(--space-2)' }}>Try clearing your filters or typing a different club name.</p>
          </div>
        )}

        {competitions && filteredComps.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-10)' }}>
            {existingParents.map(parent => (
              <div key={parent} className="parent-section">
                {/* Parent Comp Heading */}
                <h2 style={{
                  fontSize: 'var(--font-size-2xl)',
                  fontWeight: 700,
                  color: 'var(--color-accent-primary)',
                  marginBottom: 'var(--space-6)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  {parent}
                </h2>

                {/* Division sub-groupings */}
                {sortDivs(grouped[parent]).map(divStr => {
                  const comps = grouped[parent][divStr]
                  const cleanDiv = divStr === 'General' ? 'General' : `Division ${divStr}`

                  return (
                    <div key={divStr} className="division-block" style={{ marginBottom: 'var(--space-8)' }}>
                      <h3 style={{
                        fontSize: 'var(--font-size-sm)',
                        fontWeight: 600,
                        color: 'var(--color-text-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        marginBottom: 'var(--space-4)',
                        paddingBottom: 'var(--space-2)',
                        borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
                      }}>
                        {cleanDiv}
                      </h3>

                      <div className="comp-rows-container">
                        {sortGrades(comps).map(comp => (
                          <div key={comp.id} className="comp-row">
                            <div className="comp-row__info">
                              <div className="comp-row__logo-placeholder">🏆</div>
                              <div className="comp-row__meta">
                                <div className="comp-row__name">{comp.name}</div>
                                <div className="comp-row__details">
                                  <span>👥 {comp.club_count} {comp.club_count === 1 ? 'club' : 'clubs'}</span>
                                  <span style={{ opacity: 0.3 }}>·</span>
                                  <span>📅 {comp.round_count} {comp.round_count === 1 ? 'round' : 'rounds'}</span>
                                </div>
                              </div>
                            </div>

                            <div className="comp-row__actions">
                              <Link
                                to={`/competitions/${comp.id}?tab=standings`}
                                className="btn btn--primary"
                                style={{
                                  padding: '8px 16px',
                                  borderRadius: '8px',
                                  fontSize: 'var(--font-size-sm)',
                                  fontWeight: 600
                                }}
                              >
                                Standings
                              </Link>
                              <Link
                                to={`/competitions/${comp.id}?tab=fixtures`}
                                className="btn btn--ghost"
                                style={{
                                  padding: '8px 16px',
                                  borderRadius: '8px',
                                  fontSize: 'var(--font-size-sm)',
                                  fontWeight: 600,
                                  border: '1px solid rgba(255, 255, 255, 0.1)'
                                }}
                              >
                                Fixtures & Results
                              </Link>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
