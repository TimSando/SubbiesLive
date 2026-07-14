import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { updateAppointmentStatus } from '../../api/refzone';
import '../../pages/RefZone.css';

export default function AppointmentCard({ appointment, onUpdate, hideActions }) {
  const [showOfficials, setShowOfficials] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState(null);

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
  } else if (statusText.toLowerCase() === 'declined') {
    statusClass = 'badge--cancelled';
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

  // Handle status update
  const handleStatusChange = async (status) => {
    setIsUpdating(true);
    setError(null);
    try {
      await updateAppointmentStatus(appointment._id, status);
      if (onUpdate) {
        onUpdate();
      }
    } catch (err) {
      console.error(`Failed to update appointment status to ${status}:`, err);
      setError(`Failed to ${status === 'approved' ? 'accept' : 'reject'} match. Please try again.`);
    } finally {
      setIsUpdating(false);
    }
  };

  const lowerStatus = statusText.toLowerCase();
  const showAccept = !hideActions && !isPast && !isCancelled && lowerStatus === 'pending';
  const showReject = !hideActions && !isPast && !isCancelled && (lowerStatus === 'pending' || lowerStatus === 'approved' || lowerStatus === 'confirmed');


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

      {appointment.db_game_id && (
        <div className="appointment-card__actions" style={{ marginTop: 'var(--space-4)' }}>
          <Link
            to={isPast || statusText === 'past' ? `/games/${appointment.db_game_id}` : `/games/${appointment.db_game_id}/prep`}
            className="btn btn--primary"
            style={{ display: 'block', textAlign: 'center', width: '100%', textDecoration: 'none' }}
          >
            {isPast || statusText === 'past' ? '📊 View Stats & Match Centre' : '📋 Match Preparation (Form Guide)'}
          </Link>
        </div>
      )}

      {(showAccept || showReject) && (
        <div className="appointment-card__response-actions" style={{ display: 'flex', gap: 'var(--space-2)', marginTop: 'var(--space-4)' }}>
          {showAccept && (
            <button
              type="button"
              className="btn btn--primary"
              style={{ flex: 1 }}
              onClick={() => handleStatusChange('approved')}
              disabled={isUpdating}
            >
              {isUpdating ? 'Accepting...' : '✓ Accept'}
            </button>
          )}
          {showReject && (
            <button
              type="button"
              className="btn btn--danger"
              style={{ flex: 1 }}
              onClick={() => handleStatusChange('declined')}
              disabled={isUpdating}
            >
              {isUpdating ? 'Rejecting...' : '✗ Reject'}
            </button>
          )}
        </div>
      )}

      {error && (
        <div style={{ color: 'var(--color-loss)', fontSize: 'var(--font-size-xs)', marginTop: 'var(--space-2)', textAlign: 'center' }}>
          {error}
        </div>
      )}

      {
        appointment.otherReferees && appointment.otherReferees.length > 0 && (
          <div className="officials-panel" style={{ marginTop: 'var(--space-4)' }}>
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
        )
      }
    </div >
  );
}
