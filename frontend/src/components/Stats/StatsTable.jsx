import { Link } from 'react-router-dom'

export default function StatsTable({ 
  title, 
  headers, 
  data, 
  renderRow 
}) {
  return (
    <div className="stats-table-wrapper animate-in">
      {title && <h2 className="stats-table-title">{title}</h2>}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th style={{ width: '60px' }}>Rank</th>
              {headers.map(h => (
                <th key={h.key} style={h.style}>{h.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, idx) => (
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
    </div>
  )
}
