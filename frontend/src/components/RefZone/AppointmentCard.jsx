import React, { useState } from 'react';
import '../../pages/RefZone.css';

export default function AppointmentCard({ appointment }) {
  const [showOfficials, setShowOfficials] = useState(false);

  if (!appointment || !appointment.match) return null;

  const match = appointment.match;
  const isPast = match.moment < Date.now();
  const isCancelled = appointment.isActive === false;

  // Status styling
  let statusText = appointment.status || 'approved';
  let statusClass = 'badge--approved';

  if (isCancelled) {
    statusText = 'cancelled';
    statusClass = 'badge--cancelled';
  } else if (isPast) {
    statusText = 'past';
    statusClass = 'badge--past';
  } else if (statusText.toLowerCase() === 'pending') {
    statusClass = 'badge--pending';
  }


  // Format date & time in Sydney timezone
  const matchDate = new Date(match.moment);
  
  const dateStr = matchDate.toLocaleDateString('en-AU', {
    timeZone: 'Australia/Sydney',
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  const timeStr = matchDate.toLocaleTimeString('en-AU', {
    timeZone: 'Australia/Sydney',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });

  // Referee Role labeling
  const roleText = appointment.type || 'Referee';

  return (
    <div className="card appointment-card">
      <div className="appointment-card__header">
        <div className="appointment-card__badges">
          <span className="badge badge--role">{roleText}</span>
          <span className={`badge ${statusClass}`}>{statusText}</span>
        </div>
        <div className="appointment-card__time">
          <span>📅 {dateStr}</span>
          <span>⏰ {timeStr}</span>
        </div>
      </div>

      <div className="appointment-card__teams">
        <div className="appointment-card__team appointment-card__team--home">
          {match.homeTeam ? match.homeTeam.name : 'TBD'}
        </div>
        <div className="appointment-card__vs">VS</div>
        <div className="appointment-card__team appointment-card__team--away">
          {match.awayTeam ? match.awayTeam.name : 'TBD'}
        </div>
      </div>

      <div className="appointment-card__details">
        <div className="appointment-card__comp">
          🏆 {match.competition ? match.competition.name : 'Unknown Competition'}
          {appointment.competition && appointment.competition.association && (
            <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginLeft: 'var(--space-2)' }}>
              ({appointment.competition.association.name})
            </span>
          )}
        </div>
        <div className="appointment-card__venue">
          📍 {match.venue ? match.venue.name : 'TBD Venue'}
        </div>
      </div>

      {appointment.otherReferees && appointment.otherReferees.length > 0 && (
        <div className="officials-panel">
          <button
            type="button"
            className="officials-panel__trigger"
            onClick={() => setShowOfficials(!showOfficials)}
          >
            <span>Match Officials ({appointment.otherReferees.length})</span>
            <span>{showOfficials ? '▲' : '▼'}</span>
          </button>
          {showOfficials && (
            <div className="officials-panel__content">
              {appointment.otherReferees.map((ref, idx) => (
                <div className="official-item" key={ref._id || idx}>
                  <span className="official-name">
                    {ref.firstname} {ref.lastname}
                  </span>
                  <span className="official-role">{ref.type}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
