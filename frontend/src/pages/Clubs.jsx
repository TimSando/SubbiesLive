import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { api } from '../api/client.js'
import PageSubscribeButton from '../components/NotificationToggle/PageSubscribeButton.jsx'

export default function Clubs() {
  const { data: clubs, loading, error } = useApi(() => api.getClubs(), [])

  const [followingClubIds, setFollowingClubIds] = useState(() => {
    const existing = JSON.parse(localStorage.getItem('subbies_following_clubs') || '[]')
    return new Set(existing.map(c => c.id))
  })

  // React to follow status updates from other pages
  useEffect(() => {
    const handleFollowUpdate = () => {
      const existing = JSON.parse(localStorage.getItem('subbies_following_clubs') || '[]')
      setFollowingClubIds(new Set(existing.map(c => c.id)))
    }
    window.addEventListener('followingUpdated', handleFollowUpdate)
    return () => window.removeEventListener('followingUpdated', handleFollowUpdate)
  }, [])

  const toggleFollow = (club, event) => {
    event.preventDefault()
    event.stopPropagation()
    const existing = JSON.parse(localStorage.getItem('subbies_following_clubs') || '[]')
    const isFollowing = followingClubIds.has(club.id)
    let updated
    if (isFollowing) {
      updated = existing.filter(c => c.id !== club.id)
    } else {
      updated = [...existing, { id: club.id, name: club.name, logo_url: club.logo_url }]
    }
    localStorage.setItem('subbies_following_clubs', JSON.stringify(updated))
    setFollowingClubIds(new Set(updated.map(c => c.id)))
    window.dispatchEvent(new Event('followingUpdated'))
  }

  // Filter states preserved in sessionStorage
  const [searchQuery, setSearchQuery] = useState(() => sessionStorage.getItem('clubs_searchQuery') || '')
  const [parentComp, setParentComp] = useState(() => sessionStorage.getItem('clubs_parentComp') || 'All')
  const [division, setDivision] = useState(() => sessionStorage.getItem('clubs_division') || 'All')
  const [onlyWomens, setOnlyWomens] = useState(() => sessionStorage.getItem('clubs_onlyWomens') === 'true')

  useEffect(() => {
    sessionStorage.setItem('clubs_searchQuery', searchQuery)
  }, [searchQuery])

  useEffect(() => {
    sessionStorage.setItem('clubs_parentComp', parentComp)
  }, [parentComp])

  useEffect(() => {
    sessionStorage.setItem('clubs_division', division)
  }, [division])

  useEffect(() => {
    sessionStorage.setItem('clubs_onlyWomens', onlyWomens ? 'true' : 'false')
  }, [onlyWomens])

  // Dynamically extract divisions based on selected competition
  const activeDivisions = Array.from(new Set(
    (clubs || [])
      .filter(c => parentComp === 'All' || c.competition_mapping?.parent_competition === parentComp)
      .map(c => c.competition_mapping?.division)
      .filter(Boolean)
  )).sort((a, b) => parseInt(a) - parseInt(b))

  // Apply sequential filtering
  const filteredClubs = (clubs || []).filter(club => {
    // 1. Search filter
    const matchesSearch = club.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (club.short_name && club.short_name.toLowerCase().includes(searchQuery.toLowerCase()))

    // 2. Parent Competition filter
    const matchesParent = parentComp === 'All' || club.competition_mapping?.parent_competition === parentComp

    // 3. Division filter
    const matchesDivision = division === 'All' || club.competition_mapping?.division === division

    // 4. Women's team filter
    const matchesWomens = !onlyWomens || club.has_womens_team === true

    return matchesSearch && matchesParent && matchesDivision && matchesWomens
  })

  // Group clubs by parent_competition, then by division
  const grouped = {}
  for (const club of filteredClubs) {
    const parent = club.competition_mapping?.parent_competition || 'Other'
    const div = club.competition_mapping?.division ? `Division ${club.competition_mapping.division}` : 'General / Other'

    if (!grouped[parent]) {
      grouped[parent] = {}
    }
    if (!grouped[parent][div]) {
      grouped[parent][div] = []
    }
    grouped[parent][div].push(club)
  }

  // Sort parent groups: Shute Shield first, Suburban second, others last
  const sortedParents = Object.keys(grouped).sort((a, b) => {
    if (a === 'Shute Shield') return -1
    if (b === 'Shute Shield') return 1
    if (a === 'Suburban Rugby Union') return -1
    if (b === 'Suburban Rugby Union') return 1
    if (a === 'Other') return 1
    if (b === 'Other') return -1
    return a.localeCompare(b)
  })

  // Sort division sub-groups numerically, with Other last
  const getDivNum = (divName) => {
    const match = divName.match(/\d+/)
    return match ? parseInt(match[0]) : 999
  }
  const getSortedDivisions = (parentName) => {
    return Object.keys(grouped[parentName]).sort((a, b) => getDivNum(a) - getDivNum(b))
  }

  return (
    <div className="page">
      <div className="container animate-in">
        <header style={{ marginBottom: 'var(--space-8)' }}>
          <h1 style={{ marginBottom: 'var(--space-2)' }}>Clubs</h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-lg)' }}>
            Search and navigate to individual club rosters, matches, and details
          </p>
        </header>

        {/* Dynamic Glassmorphic Filters Dashboard */}
        <div className="clubs-filter-bar">
          <div className="clubs-search-input">
            <span className="clubs-search-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.6 }}>
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </span>
            <input
              type="text"
              placeholder="Search clubs by name or nickname..."
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
              <span className="checkbox-label">Women's Team</span>
            </label>
          </div>
        </div>

        {/* Loading and Error States */}
        {loading && (
          <div className="club-rows-container">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="skeleton" style={{ height: '76px', borderRadius: 'var(--radius-xl)' }} />
            ))}
          </div>
        )}

        {error && (
          <div className="card" style={{ color: 'var(--color-loss)', padding: 'var(--space-6)' }}>
            Failed to load clubs: {error}
          </div>
        )}

        {/* Render Nested Hierarchical Groupings */}
        {clubs && filteredClubs.length === 0 && (
          <div className="card" style={{ textAlign: 'center', padding: 'var(--space-10)', color: 'var(--color-text-secondary)' }}>
            <span style={{ fontSize: '2.5rem', display: 'block', marginBottom: 'var(--space-4)' }}>🏉</span>
            <h3>No Clubs Found</h3>
            <p style={{ marginTop: 'var(--space-2)' }}>Try relaxing your search query or dropdown filters.</p>
          </div>
        )}

        {clubs && sortedParents.map(parentKey => (
          <section key={parentKey} style={{ marginBottom: 'var(--space-10)' }}>
            <h2 className="clubs-section__title" style={{ fontSize: 'var(--font-size-2xl)', color: 'var(--color-text-accent)' }}>
              {parentKey}
            </h2>

            {getSortedDivisions(parentKey).map(divKey => (
              <div key={divKey} style={{ marginBottom: 'var(--space-6)' }}>
                <h3 style={{
                  fontSize: 'var(--font-size-base)',
                  color: 'var(--color-text-secondary)',
                  marginBottom: 'var(--space-3)',
                  paddingLeft: 'var(--space-2)',
                  fontWeight: 'var(--font-weight-semibold)',
                  opacity: 0.85
                }}>
                  {divKey}
                </h3>

                <div className="club-rows-container">
                  {grouped[parentKey][divKey].map(club => (
                    <Link
                      to={`/clubs/${club.id}`}
                      className="club-row"
                      id={`club-${club.id}`}
                      key={club.id}
                    >
                      <div className="club-row__info">
                        {club.logo_url ? (
                          <img
                            src={club.logo_url}
                            alt={`${club.name} logo`}
                            className="club-row__logo"
                            onError={(e) => { e.target.style.display = 'none' }}
                          />
                        ) : (
                          <div className="club-row__logo-placeholder">🏉</div>
                        )}
                        <div className="club-row__meta">
                          <span className="club-row__name">{club.name}</span>
                          {club.home_ground_name && (
                            <span className="club-row__ground">
                              📍{' '}
                              {club.home_ground_map_url ? (
                                <a
                                  href={club.home_ground_map_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="club-row__ground-link"
                                  onClick={(e) => e.stopPropagation()} // prevents triggering parent Link navigation
                                >
                                  {club.home_ground_name}
                                </a>
                              ) : (
                                club.home_ground_name
                              )}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="club-row__actions" onClick={(e) => e.stopPropagation()}>
                        <PageSubscribeButton topicType="club" topicId={club.id} topicName={club.name} />
                        <button
                          onClick={(e) => toggleFollow(club, e)}
                          title={followingClubIds.has(club.id) ? 'Unfollow club' : 'Follow club'}
                          className={`page-subscribe-btn ${followingClubIds.has(club.id) ? 'page-subscribe-btn--active' : ''}`}
                        >
                          <svg
                            viewBox="0 0 24 24"
                            width="18"
                            height="18"
                            fill={followingClubIds.has(club.id) ? 'currentColor' : 'none'}
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                          </svg>
                        </button>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </section>
        ))}
      </div>
    </div>
  )
}
