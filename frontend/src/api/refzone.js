const API_BASE = '/api/refzone';

export async function loginToRX(email, password, rememberMe = false) {
  const url = `${API_BASE}/login`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ email, password, remember_me: rememberMe }),
  });
  if (!res.ok) {
    throw new Error(`Login failed: ${res.status}`);
  }
  return res.json();
}

export async function verify2FA(mfaCode, mfaToken) {
  const url = `${API_BASE}/verify-2fa`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ code: mfaCode, token: mfaToken }),
  });
  if (!res.ok) {
    throw new Error(`2FA failed: ${res.status}`);
  }
  return res.json();
}

export async function logoutFromRX() {
  const url = `${API_BASE}/logout`;
  const res = await fetch(url, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) {
    throw new Error(`Logout failed: ${res.status}`);
  }
  return res.json();
}

export async function checkSession() {
  const url = `${API_BASE}/status`;
  const res = await fetch(url, {
    method: 'GET',
    credentials: 'include',
  });
  if (!res.ok) {
    return null;
  }
  return res.json();
}

export async function fetchWithRefresh(url, options = {}, authContext = null) {
  const fetchOptions = {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  };

  let res = await fetch(url, fetchOptions);

  if (res.status === 401) {
    console.log('RefZone: Access token expired. Attempting cookie refresh...');
    try {
      const refreshRes = await fetch(`${API_BASE}/refresh`, {
        method: 'POST',
        credentials: 'include',
      });

      if (!refreshRes.ok) {
        throw new Error('Refresh endpoint returned non-200');
      }

      // Retry original request
      res = await fetch(url, fetchOptions);
    } catch (err) {
      console.error('RefZone: Silent token refresh failed, logging out:', err);
      if (authContext && typeof authContext.clearAuth === 'function') {
        authContext.clearAuth();
      }
      throw err;
    }
  }

  if (!res.ok) {
    throw new Error(`API Request failed: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export async function fetchAppointments(authContext) {
  const userId = authContext && typeof authContext === 'object' ? authContext.userId : authContext;
  const url = `${API_BASE}/appointments?userId=${userId}`;
  return fetchWithRefresh(url, { method: 'GET' }, authContext);
}

export async function fetchProfile(authContext) {
  const userId = authContext && typeof authContext === 'object' ? authContext.userId : authContext;
  const url = `${API_BASE}/profile?userId=${userId}`;
  return fetchWithRefresh(url, { method: 'GET' }, authContext);
}
