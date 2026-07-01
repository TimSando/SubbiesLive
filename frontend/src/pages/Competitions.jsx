import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'

export default function Competitions() {
  const { data: competitions, loading, error } = useApi(() => api.getCompetitions(), [])

  // Filter states preserved in sessionStorage
  const [searchQuery, setSearchQuery] = useState(() => sessionStorage.getItem('competitions_searchQuery') || '')
  const [parentComp, setParentComp] = useState(() => sessionStorage.getItem('competitions_parentComp') || 'All')
  const [division, setDivision] = useState(() => sessionStorage.getItem('competitions_division') || 'All')
  const [onlyWomens, setOnlyWomens] = useState(() => sessionStorage.getItem('competitions_onlyWomens') === 'true')

  useEffect(() => {
    sessionStorage.setItem('competitions_searchQuery', searchQuery)
  }, [searchQuery])

  useEffect(() => {
    sessionStorage.setItem('competitions_parentComp', parentComp)
  }, [parentComp])

  useEffect(() => {
    sessionStorage.setItem('competitions_division', division)
  }, [division])

  useEffect(() => {
    sessionStorage.setItem('competitions_onlyWomens', onlyWomens ? 'true' : 'false')
  }, [onlyWomens])

  // Dynamically extract divisions based on selected competition
  const activeDivisions = Array.from(new Set(
    (competitions || [])
      .filter(c => parentComp === 'All' || c.parent_competition === parentComp)
      .map(c => c.division)
      .filter(Boolean)
  )).sort((a, b) => {
    const na = parseInt(a), nb = parseInt(b)
    if (!isNaN(na) && !isNaN(nb)) return na - nb
    return a.localeCompare(b)
  })

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

  // Client-side filtering logic
  const filteredComps = (competitions || []).filter(comp => {
    // 1. Search query filter
    const matchesSearch = !searchQuery ||
      comp.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (comp.club_names && comp.club_names.toLowerCase().includes(searchQuery.toLowerCase()))

    // 2. Parent Competition filter
    const matchesParent = parentComp === 'All' || comp.parent_competition === parentComp

    // 3. Division filter
    const matchesDivision = division === 'All' || comp.division === division

    // 4. Women's competition filter
    const name = comp.name?.toLowerCase() || ''
    const grade = comp.grade?.toLowerCase() || ''
    const isWomens = name.includes('women') || name.includes('womens') || name.includes('lass') || grade.includes('women') || grade.includes('womens')
    const matchesWomens = !onlyWomens || isWomens

    return matchesSearch && matchesParent && matchesDivision && matchesWomens
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
      <div className="container animate-in">
        <header style={{ marginBottom: 'var(--space-8)' }}>
          <h1 style={{ marginBottom: 'var(--space-2)' }}>Competitions</h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-lg)' }}>
            Browse match series, active standings, and fixtures across all leagues
          </p>
        </header>

        {/* Dynamic Glassmorphic Filters Dashboard */}
        <div className="clubs-filter-bar" style={{ marginBottom: 'var(--space-8)' }}>
          <div className="clubs-search-input">
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

          <div className="clubs-filter-select-group">
            <select
              className="clubs-select-filter"
              value={parentComp}
              onChange={(e) => {
                setParentComp(e.target.value)
                setDivision('All') // reset division on parent comp switch
              }}
            >
              <option value="All">All Competitions</option>
              <option value="Shute Shield">Shute Shield</option>
              <option value="Suburban Rugby Union">Suburban Rugby Union</option>
            </select>

            <select
              className="clubs-select-filter"
              value={division}
              onChange={(e) => setDivision(e.target.value)}
            >
              <option value="All">All Divisions</option>
              {activeDivisions.map(div => (
                <option key={div} value={div}>Division {div}</option>
              ))}
            </select>

            <label className="clubs-checkbox-filter">
              <input
                type="checkbox"
                checked={onlyWomens}
                onChange={(e) => setOnlyWomens(e.target.checked)}
              />
              <span className="checkbox-custom"></span>
              <span className="checkbox-label">Women's Competition</span>
            </label>
          </div>
        </div>

        {loading && (
          <div className="comp-rows-container">
            <div className="skeleton" style={{ height: '56px', borderRadius: 'var(--radius-xl)', marginBottom: 'var(--space-3)' }} />
            <div className="skeleton" style={{ height: '56px', borderRadius: 'var(--radius-xl)', marginBottom: 'var(--space-3)' }} />
            <div className="skeleton" style={{ height: '56px', borderRadius: 'var(--radius-xl)' }} />
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
                              <div className="comp-row__logo-placeholder">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.8 }}>
                                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                                  <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                                </svg>
                              </div>
                              <div className="comp-row__meta">
                                <div className="comp-row__name">{comp.name}</div>
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
