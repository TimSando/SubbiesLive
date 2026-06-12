import React, { createContext, useContext, useState, useEffect } from 'react';
import RefZoneLogin from './RefZoneLogin';
import RefZoneDashboard from './RefZoneDashboard';
import { checkSession, fetchProfile, logoutFromRX } from '../api/refzone';

export const RefZoneContext = createContext(null);

export function useRefZone() {
  const context = useContext(RefZoneContext);
  if (!context) {
    throw new Error('useRefZone must be used within a RefZoneContext.Provider');
  }
  return context;
}

export function RefZoneProvider({ children }) {
  const [authData, setAuthDataState] = useState(null);
  const [autoLoginLoading, setAutoLoginLoading] = useState(false);

  const clearAuth = () => {
    console.log('RefZone: Clearing authentication context');
    logoutFromRX().catch((err) => console.error('RefZone: Logout request failed:', err));
    setAuthDataState(null);
  };

  const setAuthData = (newData) => {
    setAuthDataState((prev) => {
      if (!prev) {
        return newData;
      }
      return { ...prev, ...newData };
    });
  };

  // Attempt auto-login on mount by checking the session cookie
  useEffect(() => {
    const trySessionRestore = async () => {
      console.log('RefZone: Checking for existing session cookie...');
      setAutoLoginLoading(true);
      try {
        const session = await checkSession();
        if (session && session.authenticated) {
          console.log('RefZone: Active session found. Fetching referee profile...');
          const profileData = await fetchProfile(session.userId);
          setAuthDataState({
            userId: session.userId,
            profile: profileData || {
              firstname: 'Referee',
              lastname: '',
              headshot: '',
            },
          });
          console.log('RefZone: Session restored successfully!');
        }
      } catch (err) {
        console.error('RefZone: Cookie session restoration failed:', err);
      } finally {
        setAutoLoginLoading(false);
      }
    };

    trySessionRestore();
  }, []);

  const value = {
    userId: authData ? authData.userId : null,
    profile: authData ? authData.profile : null,
    autoLoginLoading,
    setAuthData,
    clearAuth,
  };

  return (
    <RefZoneContext.Provider value={value}>
      {children}
    </RefZoneContext.Provider>
  );
}

export default function RefZone() {
  const { userId, autoLoginLoading } = useRefZone();

  return (
    <div className="refzone-wrapper">
      {autoLoginLoading ? (
        <div className="container page" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: '1.5rem' }}>
          <div className="card skeleton" style={{ width: '100%', maxWidth: '420px', height: '300px', borderRadius: 'var(--radius-xl)' }}></div>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-medium)' }}>
            Signing you in securely to RugbyXplorer...
          </p>
        </div>
      ) : !userId ? (
        <RefZoneLogin />
      ) : (
        <RefZoneDashboard />
      )}
    </div>
  );
}
