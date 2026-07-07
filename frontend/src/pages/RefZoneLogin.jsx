import React, { useState } from 'react';
import { useRefZone } from './RefZone';
import { loginToRX, verify2FA, fetchProfile } from '../api/refzone';
import './RefZone.css';

export default function RefZoneLogin() {
  const { setAuthData } = useRefZone();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 2FA state variables
  const [requires2FA, setRequires2FA] = useState(false);
  const [mfaToken, setMfaToken] = useState(null);
  const [mfaCode, setMfaCode] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Email and Password are required.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      console.log('RefZone: Submitting credentials to backend...');
      const loginData = await loginToRX(email, password, rememberMe);

      if (loginData.status === 'mfa_required') {
        console.log('RefZone: MFA challenge required.');
        setRequires2FA(true);
        setMfaToken(loginData.mfa_token);
        setLoading(false);
        return;
      }

      if (!loginData || !loginData.userId) {
        throw new Error('Invalid response from authentication server.');
      }

      console.log('RefZone: Authentication successful!');
      
      const profileData = await fetchProfile(loginData.userId);

      setAuthData({
        userId: loginData.userId,
        profile: profileData || {
          firstname: 'Referee',
          lastname: '',
          headshot: '',
        },
      });
    } catch (err) {
      console.error('RefZone: Login failed:', err);
      setError('Failed to login. Please check your credentials and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify2FA = async (e) => {
    e.preventDefault();
    if (!mfaCode || mfaCode.length !== 6) {
      setError('A 6-digit code is required.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      console.log('RefZone: Submitting 2FA code...');
      const verifyData = await verify2FA(mfaCode, mfaToken, rememberMe);

      if (!verifyData || !verifyData.userId) {
        throw new Error('Invalid response from 2FA verification.');
      }

      console.log('RefZone: 2FA Verification successful!');
      
      const profileData = await fetchProfile(verifyData.userId);

      setAuthData({
        userId: verifyData.userId,
        profile: profileData || {
          firstname: 'Referee',
          lastname: '',
          headshot: '',
        },
      });
    } catch (err) {
      console.error('RefZone: 2FA verification failed:', err);
      setError('Invalid 2FA code. Please check the code and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-card__header">
          <span className="login-card__icon">🏉</span>
          <h2 className="login-card__title">RefZone</h2>
          <p className="login-card__subtitle">
            Authenticate using your RugbyXplorer credentials
          </p>
        </div>

        {error && <div className="alert-danger" style={{ marginBottom: '1.5rem' }}>{error}</div>}

        {requires2FA ? (
          <form onSubmit={handleVerify2FA} className="login-form">
            <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-4)', textAlign: 'center' }}>
              A verification code has been sent to your registered device. Enter it below.
            </p>
            <div className="form-group">
              <label className="form-label" htmlFor="mfa-code-input">
                Verification Code
              </label>
              <input
                id="mfa-code-input"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                className="form-input"
                placeholder="000000"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                disabled={loading}
                required
                autoFocus
              />
            </div>

            <button
              type="submit"
              className="btn btn--primary"
              disabled={loading}
              style={{ width: '100%', marginTop: '1rem' }}
            >
              {loading ? 'Verifying...' : 'Verify Code'}
            </button>
            
            <button
              type="button"
              className="btn btn--ghost"
              disabled={loading}
              onClick={() => {
                setRequires2FA(false);
                setMfaToken(null);
                setMfaCode('');
              }}
              style={{ width: '100%', marginTop: '0.5rem' }}
            >
              Back to Login
            </button>
          </form>
        ) : (
          <form onSubmit={handleSubmit} className="login-form">
            <div className="form-group">
              <label className="form-label" htmlFor="email-input">
                Email Address
              </label>
              <input
                id="email-input"
                type="email"
                className="form-input"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="password-input">
                Password
              </label>
              <input
                id="password-input"
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div className="form-checkbox-group">
              <input
                id="remember-me-checkbox"
                type="checkbox"
                className="form-checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                disabled={loading}
              />
              <label className="form-checkbox-label" htmlFor="remember-me-checkbox">
                Remember me for 30 days
              </label>
            </div>

            <button
              type="submit"
              className="btn btn--primary"
              disabled={loading}
              style={{ width: '100%', marginTop: '1rem' }}
            >
              {loading ? 'Authenticating...' : 'Sign In with RugbyXplorer'}
            </button>
          </form>
        )}

        <div className="form-note">
          ⚠️ <strong>Security Notice:</strong> Sessions are managed securely on our backend using HTTP-only, secure cookies. Your credentials are sent directly over HTTPS to our server and are never stored.
        </div>
      </div>
    </div>
  );
}
