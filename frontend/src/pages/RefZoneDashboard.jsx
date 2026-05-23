import React, { useState, useEffect } from 'react';
import { useRefZone } from './RefZone';
import { fetchAppointments } from '../api/refzone';
import AppointmentCard from '../components/RefZone/AppointmentCard';
import './RefZone.css';

export default function RefZoneDashboard() {
  const auth = useRefZone();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('weekend'); // 'weekend', 'upcoming', 'past'

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('RefZone: Fetching appointments...');
      const data = await fetchAppointments(auth);
      setAppointments(data || []);
    } catch (err) {
      console.error('RefZone: Failed to load appointments:', err);
      setError('Failed to fetch your appointments. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [auth.userId]);

  // Compute Sydney timezone-based weekend dates
  const getWeekendGroup = () => {
    const now = Date.now();
    
    // Get current date string in Sydney timezone (YYYY-MM-DD)
    const sydneyNowStr = new Date().toLocaleDateString('en-CA', { timeZone: 'Australia/Sydney' });
    const [sYear, sMonth, sDay] = sydneyNowStr.split('-').map(Number);
    
    // Create Date object representing Sydney's local midnight
    const sydneyDate = new Date(sYear, sMonth - 1, sDay);
    const dayOfWeek = sydneyDate.getDay(); // 0 = Sun, 1 = Mon, ..., 6 = Sat
    
    let satDiff = 0;
    let sunDiff = 0;
    
    if (dayOfWeek === 6) { // Saturday
      satDiff = 0;
      sunDiff = 1;
    } else if (dayOfWeek === 0) { // Sunday
      satDiff = -1;
      sunDiff = 0;
    } else { // Mon-Fri
      satDiff = 6 - dayOfWeek;
      sunDiff = 7 - dayOfWeek;
    }
    
    const satDate = new Date(sydneyDate);
    satDate.setDate(sydneyDate.getDate() + satDiff);
    const satStr = satDate.toLocaleDateString('en-CA');
    
    const sunDate = new Date(sydneyDate);
    sunDate.setDate(sydneyDate.getDate() + sunDiff);
    const sunStr = sunDate.toLocaleDateString('en-CA');

    const getSydneyDateString = (ts) => {
      return new Date(ts).toLocaleDateString('en-CA', { timeZone: 'Australia/Sydney' });
    };

    const thisWeekend = [];
    const upcoming = [];
    const past = [];

    appointments.forEach((app) => {
      if (!app.match) return;
      const appDateStr = getSydneyDateString(app.match.moment);
      const isPastMoment = app.match.moment < now;
      const isCancelled = app.isActive === false;

      // Check if cancelled
      if (isCancelled) {
        past.push(app);
      } else if (appDateStr === satStr || appDateStr === sunStr) {
        // Check if it falls on Saturday or Sunday of this/next weekend
        thisWeekend.push(app);
      } else if (isPastMoment) {
        // Show approved/confirmed only in past games
        if (app.status === 'approved' || app.status === 'confirmed') {
          past.push(app);
        }
      } else {
        upcoming.push(app);
      }
    });


    // Sort thisWeekend ascending by moment
    thisWeekend.sort((a, b) => a.match.moment - b.match.moment);
    // Sort upcoming ascending by moment
    upcoming.sort((a, b) => a.match.moment - b.match.moment);
    // Sort past descending by moment (newest first)
    past.sort((a, b) => b.match.moment - a.match.moment);

    return { thisWeekend, upcoming, past };
  };

  const { thisWeekend, upcoming, past } = getWeekendGroup();

  const getInitials = () => {
    if (!auth.profile) return 'R';
    const first = auth.profile.firstname ? auth.profile.firstname[0] : '';
    const last = auth.profile.lastname ? auth.profile.lastname[0] : '';
    return (first + last).toUpperCase() || 'R';
  };

  return (
    <div className="container page animate-in">
      <div className="dashboard-header">
        <div className="referee-profile">
          {auth.profile?.headshot ? (
            <img
              src={auth.profile.headshot}
              alt="Referee headshot"
              className="referee-avatar"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          ) : (
            <div className="referee-avatar-placeholder">{getInitials()}</div>
          )}
          <div>
            <h1 className="referee-name">
              {auth.profile
                ? `${auth.profile.firstname} ${auth.profile.lastname}`
                : 'Referee Dashboard'}
            </h1>
            <div className="referee-title">RugbyXplorer RefZone</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
          <button type="button" className="btn btn--ghost" onClick={loadData} disabled={loading}>
            🔄 {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <button type="button" className="btn btn--ghost" onClick={auth.clearAuth}>
            Logout
          </button>
        </div>
      </div>

      <div className="tab-bar">
        <button
          type="button"
          className={`tab-bar__tab ${activeTab === 'weekend' ? 'tab-bar__tab--active' : ''}`}
          onClick={() => setActiveTab('weekend')}
        >
          This Weekend ({thisWeekend.length})
        </button>
        <button
          type="button"
          className={`tab-bar__tab ${activeTab === 'upcoming' ? 'tab-bar__tab--active' : ''}`}
          onClick={() => setActiveTab('upcoming')}
        >
          Coming Up ({upcoming.length})
        </button>
        <button
          type="button"
          className={`tab-bar__tab ${activeTab === 'past' ? 'tab-bar__tab--active' : ''}`}
          onClick={() => setActiveTab('past')}
        >
          Past Games ({past.length})
        </button>
      </div>

      {loading ? (
        <div className="grid grid--2">
          <div className="card skeleton" style={{ height: '220px' }}></div>
          <div className="card skeleton" style={{ height: '220px' }}></div>
        </div>
      ) : error ? (
        <div className="alert-danger" style={{ padding: 'var(--space-6)' }}>
          <p>{error}</p>
          <button
            type="button"
            className="btn btn--primary mt-4"
            onClick={loadData}
            style={{ marginTop: 'var(--space-4)' }}
          >
            Retry Loading
          </button>
        </div>
      ) : (
        <div className="refzone-sections">
          {activeTab === 'weekend' && (
            <div>
              <h2 className="refzone-section__title">
                🏉 Games This Weekend
                <span className="refzone-section__count">{thisWeekend.length}</span>
              </h2>
              {thisWeekend.length === 0 ? (
                <div className="no-appointments">
                  No match appointments scheduled for this upcoming weekend.
                </div>
              ) : (
                <div className="grid grid--2">
                  {thisWeekend.map((app) => (
                    <AppointmentCard key={app._id} appointment={app} />
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'upcoming' && (
            <div>
              <h2 className="refzone-section__title">
                📅 Upcoming Pending & Confirmed
                <span className="refzone-section__count">{upcoming.length}</span>
              </h2>
              {upcoming.length === 0 ? (
                <div className="no-appointments">
                  No other future appointments scheduled.
                </div>
              ) : (
                <div className="grid grid--2">
                  {upcoming.map((app) => (
                    <AppointmentCard key={app._id} appointment={app} />
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'past' && (
            <div>
              <h2 className="refzone-section__title">
                📜 Past Matches
                <span className="refzone-section__count">{past.length}</span>
              </h2>
              {past.length === 0 ? (
                <div className="no-appointments">
                  No past match appointments found.
                </div>
              ) : (
                <div className="grid grid--2">
                  {past.map((app) => (
                    <AppointmentCard key={app._id} appointment={app} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
