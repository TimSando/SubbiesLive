const API_BASE = '/api/refzone';

export async function loginToRX(encryptedEmail, encryptedPassword) {
  const url = `${API_BASE}/login`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email: encryptedEmail, password: encryptedPassword }),
  });
  if (!res.ok) {
    throw new Error(`Login failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchWithRefresh(url, options, authContext) {
  let headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (authContext && authContext.accessToken) {
    headers['Authorization'] = `Bearer ${authContext.accessToken}`;
  }

  let res = await fetch(url, {
    ...options,
    headers,
  });

  if (res.status === 401 && authContext && authContext.encryptedEmail && authContext.encryptedPassword) {
    console.log('RefZone: Access token expired. Attempting silent re-login...');
    try {
      const loginData = await loginToRX(authContext.encryptedEmail, authContext.encryptedPassword);
      const newAccessToken = loginData.jwtTokens.accessToken;
      const newUserId = loginData.userId;
      
      // Update auth context state
      authContext.setAuthData({
        accessToken: newAccessToken,
        userId: newUserId,
        profile: loginData.profile,
      });

      // Retry the original request
      headers['Authorization'] = `Bearer ${newAccessToken}`;
      res = await fetch(url, {
        ...options,
        headers,
      });
    } catch (err) {
      console.error('RefZone: Silent re-login failed, logging out:', err);
      authContext.clearAuth();
      throw err;
    }
  }

  if (!res.ok) {
    throw new Error(`API Request failed: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export async function fetchAppointments(authContext) {
  const url = `${API_BASE}/appointments?userId=${authContext.userId}`;
  return fetchWithRefresh(url, { method: 'GET' }, authContext);
}

export async function fetchProfile(authContext) {
  const url = `${API_BASE}/profile?userId=${authContext.userId}`;
  return fetchWithRefresh(url, { method: 'GET' }, authContext);
}
