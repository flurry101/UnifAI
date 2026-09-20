// Authentication API and Persona Management
import { apiFetch, getAccessToken, setAccessToken } from './client';

function storeSession(data) {
  setAccessToken(data.access_token);
  return data;
}

export const PERSONAS = {
  USER: {
    id: 'user',
    role: 'CPSE_USER',
    displayTitle: 'USER',
    badge: 'CPSE OPERATIONAL USER',
    description: 'Ingest local materials, inspect specifications, and invoke AI matching pipelines.',
    defaultUsername: 'cpse_user',
    cpse: 'ONGC / IOCL',
  },
  REVIEWER: {
    id: 'reviewer',
    role: 'TECHNICAL_REVIEWER',
    displayTitle: 'REVIEWER',
    badge: 'TECHNICAL REVIEWER',
    description: 'Evaluate technical attribute conflicts, inspect feature differences, and record decisions.',
    defaultUsername: 'reviewer',
    cpse: 'CENTRAL REVIEW BOARD',
  },
  ADMIN: {
    id: 'admin',
    role: 'NATIONAL_ADMIN',
    displayTitle: 'ADMIN',
    badge: 'NATIONAL ADMIN',
    description: 'Manage global CNMC catalog, view cross-CPSE lineage, and inspect RBAC security audit.',
    defaultUsername: 'admin',
    cpse: 'NATIONAL HARMONIZATION CELL',
  }
};

export async function loginWithCredentials(usernameOrEmail, password) {
  const formData = new URLSearchParams();
  formData.append('username', usernameOrEmail);
  formData.append('password', password);

  try {
    const data = await apiFetch('/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (data.access_token) {
      storeSession(data);
      return { success: true, token: data.access_token, user: data };
    }
    return { success: false, error: 'Token missing in response' };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

export async function registerUser({ username, email, password, role, cpse_id }) {
  try {
    const data = await apiFetch('/api/v1/auth/register', {
      method: 'POST',
      body: {
        username,
        email: email || undefined,
        password,
        role,
        cpse_id,
      },
    });

    if (data.access_token) {
      storeSession(data);
      return { success: true, token: data.access_token, user: data };
    }
    return { success: false, error: 'Token missing in response' };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

export async function exchangeGoogleCode({ code, redirectUri, state }) {
  try {
    const data = await apiFetch('/api/v1/auth/google/exchange', {
      method: 'POST',
      body: {
        code,
        redirect_uri: redirectUri,
        state,
      },
    });

    if (data.access_token) {
      storeSession(data);
      return { success: true, token: data.access_token, user: data };
    }
    return { success: false, error: 'Token missing in Google code exchange response' };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

export async function getGoogleOAuthUrl(redirectUri = null, state = null) {
  try {
    const params = new URLSearchParams();
    if (redirectUri) params.set('redirect_uri', redirectUri);
    if (state) params.set('state', state);
    const query = params.toString() ? `?${params.toString()}` : '';
    return await apiFetch(`/api/v1/auth/google/url${query}`);
  } catch (err) {
    return { configured: false, error: err.message };
  }
}

// Decode base64url JWT payload
export function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
}

export function getCurrentSession() {
  const token = getAccessToken();
  const savedPersonaId = localStorage.getItem('unifai_active_persona') || 'user';

  let role = 'CPSE_USER';
  if (token) {
    const payload = parseJwt(token);
    if (payload && payload.role) {
      role = payload.role;
    }
  }

  return {
    token,
    username: null,
    personaId: savedPersonaId,
    role,
  };
}

export function saveSession(personaKey, token = null) {
  const persona = PERSONAS[personaKey] || PERSONAS.USER;
  localStorage.setItem('unifai_active_persona', persona.id);
  if (token) {
    setAccessToken(token);
  }
}

export function clearSession() {
  localStorage.removeItem('unifai_active_persona');
  setAccessToken(null);
}

export async function probeCookieSession() {
  try {
    const user = await apiFetch('/api/v1/auth/me');
    return { status: 'authenticated', user };
  } catch (err) {
    if (err.status === 401 || err.status === 403) {
      return { status: 'unauthenticated' };
    }
    return { status: 'unknown', error: err };
  }
}

export async function getUserProfile() {
  try {
    const token = getAccessToken();
    return await apiFetch('/api/v1/auth/me', {
      ...(token ? { headers: { Authorization: `Bearer ${token}` } } : {})
    });
  } catch (err) {
    return null;
  }
}
