import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import RefZoneLogin from './RefZoneLogin';
import RefZoneDashboard from './RefZoneDashboard';
import { parseJwtExpiry } from '../utils/tokenUtils';
import { loginToRX } from '../api/refzone';

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
  const timeoutRef = useRef(null);

  const clearAuth = () => {
    console.log('RefZone: Clearing authentication context');
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    localStorage.removeItem('rx_auth_remember');
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

  // Attempt auto-login on mount
  useEffect(() => {
    const tryAutoLogin = async () => {
      const stored = localStorage.getItem('rx_auth_remember');
      if (!stored) return;

      try {
        const { encryptedEmail, encryptedPassword, expiresAt } = JSON.parse(stored);
        if (Date.now() > expiresAt) {
          console.log('RefZone: Remembered session has expired.');
          localStorage.removeItem('rx_auth_remember');
          return;
        }

        console.log('RefZone: Found stored credentials, attempting auto-login...');
        setAutoLoginLoading(true);
        const loginData = await loginToRX(encryptedEmail, encryptedPassword);
        
        if (loginData && loginData.jwtTokens && loginData.jwtTokens.accessToken) {
          setAuthDataState({
            accessToken: loginData.jwtTokens.accessToken,
            userId: loginData.userId,
            encryptedEmail,
            encryptedPassword,
            profile: loginData.profile || {
              firstname: 'Referee',
              lastname: '',
              headshot: '',
            },
          });
          console.log('RefZone: Auto-login successful!');
        }
      } catch (err) {
        console.error('RefZone: Auto-login failed:', err);
        localStorage.removeItem('rx_auth_remember');
      } finally {
        setAutoLoginLoading(false);
      }
    };

    tryAutoLogin();
  }, []);


  // Handle proactive token refresh
  useEffect(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    if (authData && authData.accessToken && authData.encryptedEmail && authData.encryptedPassword) {
      const exp = parseJwtExpiry(authData.accessToken);
      if (exp) {
        const refreshBuffer = 5 * 60 * 1000; // 5 minutes before expiry
        const delay = Math.max(0, (exp - Date.now()) - refreshBuffer);
        
        console.log(`RefZone: Scheduling proactive token refresh in ${(delay / 1000 / 60).toFixed(1)} minutes`);
        
        timeoutRef.current = setTimeout(async () => {
          console.log('RefZone: Performing proactive token refresh...');
          try {
            const loginData = await loginToRX(authData.encryptedEmail, authData.encryptedPassword);
            setAuthData({
              accessToken: loginData.jwtTokens.accessToken,
              userId: loginData.userId,
              profile: loginData.profile,
            });
          } catch (err) {
            console.error('RefZone: Proactive token refresh failed:', err);
            clearAuth();
          }
        }, delay);
      }
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [authData && authData.accessToken, authData && authData.encryptedEmail, authData && authData.encryptedPassword]);

  const value = {
    accessToken: authData ? authData.accessToken : null,
    userId: authData ? authData.userId : null,
    encryptedEmail: authData ? authData.encryptedEmail : null,
    encryptedPassword: authData ? authData.encryptedPassword : null,
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
  const { accessToken, autoLoginLoading } = useRefZone();

  return (
    <div className="refzone-wrapper">
      {autoLoginLoading ? (
        <div className="container page" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', gap: '1.5rem' }}>
          <div className="card skeleton" style={{ width: '100%', maxWidth: '420px', height: '300px', borderRadius: 'var(--radius-xl)' }}></div>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', fontWeight: 'var(--font-weight-medium)' }}>
            Signing you in securely to RugbyXplorer...
          </p>
        </div>
      ) : !accessToken ? (
        <RefZoneLogin />
      ) : (
        <RefZoneDashboard />
      )}
    </div>
  );
}

