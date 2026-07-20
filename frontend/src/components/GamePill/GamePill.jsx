import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client.js'

export function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric', month: 'short' })
}

export function formatTime(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit' })
}

export default function GamePill({ game }) {
  const isCompleted = game.status === 'completed'
  const isLive = game.status === 'in_progress'
  const isScheduled = game.status === 'scheduled'
  const homeWin = isCompleted && game.home_score > game.away_score
  const awayWin = isCompleted && game.away_score > game.home_score
  const showScore = isCompleted || isLive
  
  const [prediction, setPrediction] = useState(null)

  useEffect(() => {
    let isMounted = true
    if (isScheduled) {
      api.getGamePrediction(game.id)
        .then((data) => {
          if (isMounted) {
            setPrediction(data)
          }
        })
        .catch(() => {
          // Ignore 404s (unrated teams) or other errors silently for the badge
        })
    }
    return () => {
      isMounted = false
    }
  }, [game.id, isScheduled])

  return (
    <Link 
      to={`/games/${game.id}`} 
      className={`game-pill ${isLive ? 'game-pill--live' : ''}`} 
      id={`game-${game.id}`}
    >
      <div className="game-pill__meta">
        <span className="game-pill__comp">{game.competition_name}</span>
        <span className="game-pill__round">{game.round_name}</span>
      </div>
      <div className="game-pill__teams">
        <div className={`game-pill__team ${homeWin ? 'game-pill__team--winner' : ''}`}>
          <span className="game-pill__team-name">{game.home_team.club_name || game.home_team.name}</span>
          {showScore && (
            <span className={`game-pill__score ${homeWin ? 'game-pill__score--winner' : ''}`}>
              {game.home_score ?? 0}
            </span>
          )}
        </div>
        <div className={`game-pill__team ${awayWin ? 'game-pill__team--winner' : ''}`}>
          <span className="game-pill__team-name">{game.away_team.club_name || game.away_team.name}</span>
          {showScore && (
            <span className={`game-pill__score ${awayWin ? 'game-pill__score--winner' : ''}`}>
              {game.away_score ?? 0}
            </span>
          )}
        </div>
      </div>
      <div className="game-pill__footer">
        <span className="game-pill__date">
          {formatDate(game.game_date)} {!isCompleted && `at ${formatTime(game.game_date)}`}
        </span>
        {isLive ? (
          <span className="live-badge">
            <span className="live-dot" /> Live
          </span>
        ) : (
          <span className="game-pill__status">{game.status}</span>
        )}
      </div>
      {prediction && (
        <div className="game-pill__prediction" style={{
          marginTop: 'var(--space-3)',
          paddingTop: 'var(--space-3)',
          borderTop: '1px dashed var(--color-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '11px',
          color: 'var(--color-text-secondary)',
          fontWeight: 'var(--font-weight-medium)'
        }}>
          <span>{Math.round(prediction.home_win_probability * 100)}% ({prediction.home_odds_display})</span>
          <span style={{ fontSize: '10px', opacity: 0.7 }}>Draw {Math.round(prediction.draw_probability * 100)}%</span>
          <span>{Math.round(prediction.away_win_probability * 100)}% ({prediction.away_odds_display})</span>
        </div>
      )}
    </Link>
  )
}
