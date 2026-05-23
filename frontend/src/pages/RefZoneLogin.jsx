import React, { useState } from 'react';
import { useRefZone } from './RefZone';
import { loginToRX } from '../api/refzone';
import { encryptForRX } from '../utils/rxCrypto';
import './RefZone.css';

export default function RefZoneLogin() {
  const { setAuthData } = useRefZone();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Email and Password are required.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      console.log('RefZone: Encrypting credentials in browser...');
      const encryptedEmail = await encryptForRX(email);
      const encryptedPassword = await encryptForRX(password);

      console.log('RefZone: Submitting encrypted credentials to backend...');
      const loginData = await loginToRX(encryptedEmail, encryptedPassword);

      if (!loginData || !loginData.jwtTokens || !loginData.jwtTokens.accessToken || !loginData.userId) {
        throw new Error('Invalid response from authentication server.');
      }

      console.log('RefZone: Authentication successful!');
      
      if (rememberMe) {
        const expiresAt = Date.now() + 30 * 24 * 60 * 60 * 1000; // 30 days
        localStorage.setItem('rx_auth_remember', JSON.stringify({
          encryptedEmail,
          encryptedPassword,
          expiresAt
        }));
      } else {
        localStorage.removeItem('rx_auth_remember');
      }

      setAuthData({
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
    } catch (err) {
      console.error('RefZone: Login failed:', err);
      setError('Failed to login. Please check your credentials and try again.');
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

          <div className="form-group-checkbox" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
            <input
              id="remember-checkbox"
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              disabled={loading}
              style={{ cursor: 'pointer', width: '16px', height: '16px', accentColor: 'var(--color-win)' }}
            />
            <label htmlFor="remember-checkbox" style={{ cursor: 'pointer', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)', userSelect: 'none' }}>
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

        <div className="form-note">
          ⚠️ <strong>Security Notice:</strong> Your credentials are encrypted in your browser using RSA-OAEP before submission. Your plaintext password is never sent to our server, and no credentials are saved in our database.
        </div>
      </div>
    </div>
  );
}
