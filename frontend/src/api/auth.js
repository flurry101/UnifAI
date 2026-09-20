// Authentication API and Persona Management
import { apiFetch, getAccessToken, setAccessToken } from './client';

function storeSession(data) {
  if (data && data.access_token) {
    setAccessToken(data.access_token);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('unifai_token', data.access_token);
      if (data.role) {
        const cleanRole = data.role === 'CPSE_ADMIN' ? 'CPSE_USER' : data.role;
        window.localStorage.setItem('unifai_role', cleanRole);
      }
      if (data.username) {
        window.localStorage.setItem('unifai_username', data.username);
      }
      if (data.email) {
        window.localStorage.setItem('unifai_email', data.email);
      }
      if (data.avatar_url) {
        window.localStorage.setItem('unifai_avatar', data.avatar_url);
      }
    }
  }
  return data;
}

export const PERSONAS = {
  USER: {
    id: 'user',
    role: 'CPSE_USER',
    displayTitle: 'DASHBOARD',
    badge: 'CPSE OFFICER',
    description: 'Ingest local materials, inspect specifications, and invoke AI matching pipelines.',
    defaultUsername: 'cpse_user',
    cpse: 'ONGC / IOCL',
  },
  REVIEWER: {
    id: 'reviewer',
    role: 'CPSE_USER',
    displayTitle: 'REVIEW',
    badge: 'CPSE OFFICER',
    description: 'Evaluate technical attribute conflicts, inspect feature differences, and record decisions.',
    defaultUsername: 'cpse_user',
    cpse: 'CENTRAL REVIEW BOARD',
  },
  ADMIN: {
    id: 'admin',
    role: 'CPSE_USER',
    displayTitle: 'CNMC CATALOG',
    badge: 'CPSE OFFICER',
    tagline: 'Common National Material Catalog (CNMC) Registry & Harmonization',
    description: 'Inspect global CNMC catalog and view cross-CPSE lineage.',
    defaultUsername: 'cpse_user',
    cpse: 'NATIONAL HARMONIZATION CELL',
  },
  AUDITOR: {
    id: 'auditor',
    role: 'CPSE_USER',
    displayTitle: 'AUDIT',
    badge: 'CPSE OFFICER',
    tagline: 'Immutable Regulatory Audit Trail & Governance Compliance',
    description: 'Inspect real-time decision logs, model reasoning trails, and verify compliance with national procurement standards.',
    defaultUsername: 'cpse_user',
    cpse: 'CAG / REGULATORY OVERSIGHT',
  },
};

export function getAccessibleWorkspaces(_role) {
  // All 5 roles are merged into one CPSE Officer access model:
  // Every CPSE user has full access to all 4 functional dashboards.
  return [
    { id: 'user', label: 'MATERIAL HARMONIZATION DASHBOARD', shortLabel: 'DASHBOARD', tagline: 'Local Material Ingestion & AI Matching' },
    { id: 'reviewer', label: 'REVIEW DASHBOARD', shortLabel: 'REVIEW', tagline: 'Technical Conflict Arbitration & Ground Truth' },
    { id: 'admin', label: 'CNMC CATALOG DASHBOARD', shortLabel: 'CNMC CATALOG', tagline: 'Common National Material Catalog Master' },
    { id: 'auditor', label: 'AUDIT & COMPLIANCE DASHBOARD', shortLabel: 'AUDIT', tagline: 'Immutable Regulatory Audit Trail & Governance' },
  ];
}

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

export async function exchangeSupabaseToken({ supabaseToken, role, cpse_id }) {
  try {
    const data = await apiFetch('/api/v1/auth/supabase/exchange', {
      method: 'POST',
      body: {
        supabase_token: supabaseToken,
        role: role || 'CPSE_USER',
        cpse_id: cpse_id || 'IOCL',
      },
    });

    if (data.access_token) {
      storeSession(data);
      return { success: true, token: data.access_token, user: data };
    }
    return { success: false, error: 'Token missing in Supabase exchange response' };
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
  const savedPersonaId = typeof window !== 'undefined' ? (window.localStorage.getItem('unifai_active_persona') || 'user') : 'user';
  const savedRole = typeof window !== 'undefined' ? window.localStorage.getItem('unifai_role') : null;
  const savedUsername = typeof window !== 'undefined' ? window.localStorage.getItem('unifai_username') : null;

  let role = (savedRole === 'CPSE_ADMIN' ? 'CPSE_USER' : savedRole) || 'CPSE_USER';
  if (token) {
    const payload = parseJwt(token);
    if (payload) {
      const appRole = payload.app_metadata?.unifai_role || payload.app_metadata?.role;
      if (appRole && appRole !== 'authenticated') {
        role = appRole === 'CPSE_ADMIN' ? 'CPSE_USER' : appRole;
      } else if (payload.role && payload.role !== 'authenticated') {
        role = payload.role === 'CPSE_ADMIN' ? 'CPSE_USER' : payload.role;
      }
    }
  }

  let personaId = savedPersonaId;
  if (role === 'NATIONAL_ADMIN') {
    personaId = 'admin';
  } else if (role === 'TECHNICAL_REVIEWER') {
    personaId = 'reviewer';
  }

  return {
    token,
    username: savedUsername,
    personaId,
    role: role === 'CPSE_ADMIN' ? 'CPSE_USER' : role,
  };
}

export function saveSession(personaKey, token = null) {
  const persona = PERSONAS[personaKey] || PERSONAS.USER;
  if (typeof window !== 'undefined') {
    window.localStorage.setItem('unifai_active_persona', persona.id);
  }
  if (token) {
    setAccessToken(token);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('unifai_token', token);
    }
  }
}

export function clearSession() {
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem('unifai_active_persona');
    window.localStorage.removeItem('unifai_token');
    window.localStorage.removeItem('unifai_role');
    window.localStorage.removeItem('unifai_username');
    window.localStorage.removeItem('unifai_email');
    window.localStorage.removeItem('unifai_avatar');
  }
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
