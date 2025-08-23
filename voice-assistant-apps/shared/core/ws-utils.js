async function getAuthToken() {
  const token = (typeof localStorage !== 'undefined' &&
    (localStorage.getItem('voice_auth_token') ||
     localStorage.getItem('wsToken'))
  ) || 'devsecret';
  try { localStorage.setItem('wsToken', token); } catch (_) {}
  return token;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { getAuthToken };
}

if (typeof window !== 'undefined') {
  window.wsUtils = { getAuthToken };
}
