import React from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'

export default function Competitions() {
  const { data: competitions, loading, error } = useApi(() => api.getCompetitions(), [])

  // Grouping logic
  const grouped = {
    'Shute Shield': {},
    'Suburban Rugby Union': {},
    'Other': {}
  }

  if (competitions) {
    for (const comp of competitions) {
      const parent = comp.parent_competition || 'Other'
      const div = comp.division || 'General'
      
      if (!grouped[parent]) grouped[parent] = {}
      if (!grouped[parent][div]) grouped[parent][div] = []
      grouped[parent][div].push(comp)
    }
  }

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

  // State for collapsible divisions (default all collapsed)
  const [expandedDivs, setExpandedDivs] = React.useState({})

  const toggleDiv = (parent, div) => {
    const key = `${parent}::${div}`
    setExpandedDivs(prev => ({
      ...prev,
      [key]: !prev[key]
    }))
  }

  return (
    <div className="page">
      <div className="container animate-in">
        <header style={{ marginBottom: 'var(--space-8)' }}>
          <h1 style={{ marginBottom: 'var(--space-2)' }}>Competitions</h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-lg)' }}>
            Browse {competitions?.length || ''} competitions by parent organization
          </p>
        </header>

        {loading && (
          <div className="grid grid--2">
            <div className="skeleton" style={{ height: '400px' }} />
            <div className="skeleton" style={{ height: '400px' }} />
          </div>
        )}

        {error && (
          <div className="card" style={{ color: 'var(--color-loss)' }}>
            Failed to load competitions: {error}
          </div>
        )}

        {competitions && (
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', 
            gap: 'var(--space-12)',
            alignItems: 'start'
          }}>
            {['Shute Shield', 'Suburban Rugby Union'].map(parent => (
              <div key={parent} className="parent-column">
                <h2 className="parent-column__title" style={{ 
                  marginBottom: 'var(--space-6)',
                  paddingBottom: 'var(--space-2)',
                  borderBottom: '2px solid var(--color-accent-primary)',
                  display: 'inline-block'
                }}>
                  {parent}
                </h2>
                
                {sortDivs(grouped[parent]).map(div => {
                  const isExpanded = expandedDivs[`${parent}::${div}`]
                  return (
                    <div key={div} className="division-group" style={{ 
                      marginBottom: 'var(--space-4)',
                      borderBottom: '1px solid var(--color-border)',
                      paddingBottom: 'var(--space-2)'
                    }}>
                      <button
                        onClick={() => toggleDiv(parent, div)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          width: '100%',
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          padding: 'var(--space-2) 0',
                          color: 'var(--color-text-muted)',
                          fontSize: 'var(--font-size-sm)',
                          fontWeight: 'var(--font-weight-semibold)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                        }}
                      >
                        <span>{div !== 'General' ? `Division ${div}` : 'General'}</span>
                        <span style={{ 
                          transition: 'transform 0.2s', 
                          transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                          fontSize: '10px'
                        }}>▼</span>
                      </button>
                      
                      {isExpanded && (
                        <div style={{ 
                          display: 'flex', 
                          flexDirection: 'column', 
                          gap: 'var(--space-3)',
                          marginTop: 'var(--space-4)',
                          marginBottom: 'var(--space-4)',
                          animation: 'fade-in 0.3s ease-out'
                        }}>
                          {sortGrades(grouped[parent][div]).map(comp => (
                            <Link
                              to={`/competitions/${comp.id}`}
                              key={comp.id}
                              className="card card--clickable"
                              style={{ padding: 'var(--space-4)' }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                  <div style={{ fontWeight: 600 }}>{comp.name}</div>
                                  {comp.grade && (
                                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-secondary)' }}>
                                      Grade {comp.grade}
                                    </div>
                                  )}
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                  <div style={{ color: 'var(--color-text-accent)', fontWeight: 700 }}>{comp.team_count}</div>
                                  <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>Teams</div>
                                </div>
                              </div>
                            </Link>
                          ))}
                        </div>
                      )}
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
