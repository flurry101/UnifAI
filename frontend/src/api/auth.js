// Authentication API and Persona Management
import { apiFetch } from './client';

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
      localStorage.setItem('unifai_token', data.access_token);
      localStorage.setItem('unifai_username', data.username || usernameOrEmail);
      if (data.email) localStorage.setItem('unifai_email', data.email);
      if (data.avatar_url) localStorage.setItem('unifai_avatar', data.avatar_url);
      if (data.role) localStorage.setItem('unifai_role', data.role);
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
      localStorage.setItem('unifai_token', data.access_token);
      localStorage.setItem('unifai_username', data.username || username);
      if (data.email) localStorage.setItem('unifai_email', data.email);
      if (data.role) localStorage.setItem('unifai_role', data.role);
      return { success: true, token: data.access_token, user: data };
    }
    return { success: false, error: 'Token missing in response' };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

export async function loginWithGoogle({ email, name, avatar_url, role = 'CPSE_USER', cpse_id = 'IOCL', id_token = null }) {
  try {
    const data = await apiFetch('/api/v1/auth/google', {
      method: 'POST',
      body: {
        id_token,
        email,
        name,
        avatar_url,
        role,
        cpse_id,
      },
    });

    if (data.access_token) {
      localStorage.setItem('unifai_token', data.access_token);
      localStorage.setItem('unifai_username', data.username || email.split('@')[0]);
      localStorage.setItem('unifai_email', data.email || email);
      if (data.avatar_url) localStorage.setItem('unifai_avatar', data.avatar_url);
      if (data.role) localStorage.setItem('unifai_role', data.role);
      return { success: true, token: data.access_token, user: data };
    }
    return { success: false, error: 'Token missing in Google auth response' };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

export async function exchangeGoogleCode({ code, redirectUri, role = 'CPSE_USER', cpseId = 'IOCL' }) {
  try {
    const data = await apiFetch('/api/v1/auth/google/exchange', {
      method: 'POST',
      body: {
        code,
        redirect_uri: redirectUri,
        role,
        cpse_id: cpseId,
      },
    });

    if (data.access_token) {
      localStorage.setItem('unifai_token', data.access_token);
      localStorage.setItem('unifai_username', data.username || 'google_user');
      if (data.email) localStorage.setItem('unifai_email', data.email);
      if (data.avatar_url) localStorage.setItem('unifai_avatar', data.avatar_url);
      if (data.role) localStorage.setItem('unifai_role', data.role);
      return { success: true, token: data.access_token, user: data };
    }
    return { success: false, error: 'Token missing in Google code exchange response' };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

export async function getGoogleOAuthUrl(redirectUri = null) {
  try {
    const query = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : '';
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
  const token = localStorage.getItem('unifai_token');
  const savedPersonaId = localStorage.getItem('unifai_active_persona') || 'USER';
  const username = localStorage.getItem('unifai_username') || 'cpse_user';

  let role = 'CPSE_USER';
  if (token) {
    const payload = parseJwt(token);
    if (payload && payload.role) {
      role = payload.role;
    }
  }

  return {
    token,
    username,
    personaId: savedPersonaId,
    role,
  };
}

export function saveSession(personaKey, token = null) {
  const persona = PERSONAS[personaKey] || PERSONAS.USER;
  localStorage.setItem('unifai_active_persona', persona.id);
  localStorage.setItem('unifai_username', persona.defaultUsername);
  if (token) {
    localStorage.setItem('unifai_token', token);
  }
}

export function clearSession() {
  localStorage.removeItem('unifai_token');
  localStorage.removeItem('unifai_username');
  localStorage.removeItem('unifai_active_persona');
}

export async function getUserProfile() {
  try {
    const token = localStorage.getItem('unifai_token');
    if (!token) return null;
    return await apiFetch('/api/v1/auth/me', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
  } catch (err) {
    return null;
  }
}

