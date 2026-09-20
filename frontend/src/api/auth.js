// Authentication API and Persona Management
import { apiFetch, getAccessToken, setAccessToken } from './client';

function storeSession(data) {
  if (data && data.access_token) {
    setAccessToken(data.access_token);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('unifai_token', data.access_token);
      if (data.role) {
        window.localStorage.setItem('unifai_role', data.role);
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
    displayTitle: 'NATIONAL ADMIN',
    badge: 'NATIONAL ADMIN',
    tagline: 'Common National Material Catalog (CNMC) Registry & Harmonization',
    description: 'Manage global CNMC catalog, view cross-CPSE lineage, and inspect RBAC security audit.',
    defaultUsername: 'admin',
    cpse: 'NATIONAL HARMONIZATION CELL',
  },
  AUDITOR: {
    id: 'auditor',
    role: 'AUDITOR',
    displayTitle: 'AUDITOR',
    badge: 'REGULATORY AUDITOR',
    tagline: 'Immutable Regulatory Audit Trail & Governance Compliance',
    description: 'Inspect real-time decision logs, model reasoning trails, and verify compliance with national procurement standards.',
    defaultUsername: 'auditor',
    cpse: 'CAG / REGULATORY OVERSIGHT',
  },
  CPSE_ADMIN: {
    id: 'admin',
    role: 'CPSE_ADMIN',
    displayTitle: 'CPSE ADMIN',
    badge: 'ENTERPRISE & SYSTEM ADMIN',
    tagline: 'Full Cross-Workspace Authority & User Administration',
    description: 'Full administrative control across all CPSE workspaces, user role provisioning, and cross-enterprise harmonization.',
    defaultUsername: 'cpse_admin',
    cpse: 'CENTRAL ENTERPRISE COMMAND',
  },
};

export function getAccessibleWorkspaces(role) {
  // CPSE_ADMIN (The super admin / first user): Can access and switch between ALL workspaces
  if (role === 'CPSE_ADMIN') {
    return [
      { id: 'user', label: 'CPSE USER', shortLabel: 'USER', tagline: 'Local Material Catalog' },
      { id: 'reviewer', label: 'TECHNICAL REVIEWER', shortLabel: 'REVIEWER', tagline: 'Conflict Resolution' },
      { id: 'admin', label: 'NATIONAL ADMIN', shortLabel: 'NATL ADMIN', tagline: 'CNMC Master Registry & Users' },
      { id: 'auditor', label: 'AUDITOR', shortLabel: 'AUDITOR', tagline: 'Audit Trail & Compliance' },
    ];
  }
  // NATIONAL_ADMIN: Can see auditor, cpse_user, technical_reviewer views (+ admin)
  if (role === 'NATIONAL_ADMIN') {
    return [
      { id: 'admin', label: 'NATIONAL ADMIN', shortLabel: 'NATL ADMIN', tagline: 'CNMC Master Registry' },
      { id: 'auditor', label: 'AUDITOR', shortLabel: 'AUDITOR', tagline: 'Audit Trail & Compliance' },
      { id: 'reviewer', label: 'TECHNICAL REVIEWER', shortLabel: 'REVIEWER', tagline: 'Conflict Resolution' },
      { id: 'user', label: 'CPSE USER', shortLabel: 'USER', tagline: 'Local Material Catalog' },
    ];
  }
  // TECHNICAL_REVIEWER: Can see cpse_user and their own view only
  if (role === 'TECHNICAL_REVIEWER') {
    return [
      { id: 'reviewer', label: 'TECHNICAL REVIEWER', shortLabel: 'REVIEWER', tagline: 'Conflict Resolution' },
      { id: 'user', label: 'CPSE USER', shortLabel: 'USER', tagline: 'Local Material Catalog' },
    ];
  }
  // AUDITOR: auditor view only
  if (role === 'AUDITOR') {
    return [
      { id: 'auditor', label: 'AUDITOR', shortLabel: 'AUDITOR', tagline: 'Audit Trail & Compliance' },
    ];
  }
  // CPSE_USER: user view only
  return [
    { id: 'user', label: 'CPSE USER', shortLabel: 'USER', tagline: 'Local Material Catalog' },
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

  let role = savedRole || 'CPSE_USER';
  if (token) {
    const payload = parseJwt(token);
    if (payload) {
      const appRole = payload.app_metadata?.unifai_role || payload.app_metadata?.role;
      if (appRole && appRole !== 'authenticated') {
        role = appRole;
      } else if (payload.role && payload.role !== 'authenticated') {
        role = payload.role;
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
    role,
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
