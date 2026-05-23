export function parseJwtExpiry(token) {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    // Decode base64url safely
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      window
        .atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const payload = JSON.parse(jsonPayload);
    return payload.exp ? payload.exp * 1000 : null; // to milliseconds
  } catch (e) {
    console.error('Failed to parse JWT expiry:', e);
    return null;
  }
}
