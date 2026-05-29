import { useState, useMemo, useEffect } from 'react'

export default function StatsTable({ 
  title, 
  headers, 
  data, 
  renderRow,
  viewMode = 'total',
  paged = false,
  pageSize = 10
}) {
  const [sortConfig, setSortConfig] = useState({ key: 'total_points', direction: 'desc' })
  const [currentPage, setCurrentPage] = useState(1)

  // Reset page when data or sort changes
  useEffect(() => {
    setCurrentPage(1)
  }, [data, sortConfig])

  const sortedData = useMemo(() => {
    let sortableItems = [...data]
    if (sortConfig.key !== null) {
      sortableItems.sort((a, b) => {
        let aVal = a[sortConfig.key]
        let bVal = b[sortConfig.key]

        // Handle string comparison for names
        if (typeof aVal === 'string') {
          aVal = aVal.toLowerCase()
          bVal = bVal.toLowerCase()
        }

        if (aVal < bVal) {
          return sortConfig.direction === 'asc' ? -1 : 1
        }
        if (aVal > bVal) {
          return sortConfig.direction === 'asc' ? 1 : -1
        }
        return 0
      })
    }
    return sortableItems
  }, [data, sortConfig])

  const paginatedData = useMemo(() => {
    if (!paged) return sortedData
    const start = (currentPage - 1) * pageSize
    return sortedData.slice(start, start + pageSize)
  }, [sortedData, paged, currentPage, pageSize])

  const totalPages = useMemo(() => {
    return Math.ceil(sortedData.length / pageSize) || 1
  }, [sortedData, pageSize])

  const requestSort = (key) => {
    let direction = 'desc'
    if (sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc'
    }
    setSortConfig({ key, direction })
  }

  const getSortIcon = (key) => {
    if (sortConfig.key !== key) return '↕️'
    return sortConfig.direction === 'asc' ? '🔼' : '🔽'
  }

  return (
    <div className="stats-table-wrapper animate-in">
      {title && (
        <h2 className="stats-table-title">
          {title} {viewMode === 'average' && <span style={{ fontSize: '0.9rem', fontWeight: 'normal', color: 'var(--color-accent-primary)', marginLeft: 'var(--space-2)' }}>(Per Game Average)</span>}
        </h2>
      )}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th style={{ width: '60px' }}>Rank</th>
              {headers.map(h => (
                <th 
                  key={h.key} 
                  style={{ ...h.style, cursor: 'pointer', userSelect: 'none' }}
                  onClick={() => requestSort(h.key)}
                  className={sortConfig.key === h.key ? 'th-sorted' : ''}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    {h.label}
                    <span style={{ fontSize: '0.7rem', opacity: sortConfig.key === h.key ? 1 : 0.3 }}>
                      {getSortIcon(h.key)}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row, idx) => (
              <tr key={idx}>
                <td>
                  <span className={`rank-badge ${row.rank <= 3 ? `rank-badge--${row.rank}` : ''}`}>
                    {row.rank <= 3 ? (row.rank === 1 ? '🥇' : row.rank === 2 ? '🥈' : '🥉') : row.rank}
                  </span>
                </td>
                {renderRow(row)}
              </tr>
            ))}
            {data.length === 0 && (
              <tr>
                <td colSpan={headers.length + 1} style={{ textAlign: 'center', padding: 'var(--space-12)', color: 'var(--color-text-muted)' }}>
                  No data available for this selection
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {paged && (
        <div className="pagination-controls" style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: 'var(--space-4)',
          marginTop: 'var(--space-4)',
          padding: 'var(--space-2)'
        }}>
          <button
            className="btn btn--ghost"
            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
            disabled={currentPage === 1}
            style={{ padding: '6px 12px', fontSize: '0.85rem' }}
          >
            ◀️ Previous
          </button>
          <span style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
            Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
          </span>
          <button
            className="btn btn--ghost"
            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
            disabled={currentPage === totalPages}
            style={{ padding: '6px 12px', fontSize: '0.85rem' }}
          >
            Next ▶️
          </button>
        </div>
      )}
    </div>
  )
}
