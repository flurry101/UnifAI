import React, { createContext, useContext, useState, useEffect } from 'react';
import { PERSONAS, getCurrentSession, saveSession, clearSession, loginWithCredentials as apiLogin, registerUser as apiRegister, exchangeGoogleCode } from '../api/auth';
import { checkBackendHealth } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [activePersona, setActivePersona] = useState('user');
  const [session, setSession] = useState({
    token: null,
    username: 'cpse_user',
    role: 'CPSE_USER',
  });
  const [health, setHealth] = useState({ online: false, checking: true });

  // Initialize session and poll health
  useEffect(() => {
    const current = getCurrentSession();
    if (current.personaId && (current.personaId === 'user' || current.personaId === 'reviewer' || current.personaId === 'admin')) {
      setActivePersona(current.personaId);
    }
    setSession({
      token: current.token,
      username: current.username,
      role: current.role || 'CPSE_USER',
      email: null,
      avatar_url: null,
      isAuthenticated: !!current.token,
    });

    const verifyHealth = async () => {
      const res = await checkBackendHealth();
      setHealth({ online: res.online, service: res.service, checking: false });
    };

    verifyHealth();
    const interval = setInterval(verifyHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const switchPersona = (personaKey) => {
    const pKey = personaKey.toLowerCase();
    const persona = pKey === 'reviewer' ? PERSONAS.REVIEWER : (pKey === 'admin' ? PERSONAS.ADMIN : PERSONAS.USER);
    setActivePersona(persona.id);
    saveSession(pKey.toUpperCase());
  };

  const login = async (username, password) => {
    const res = await apiLogin(username, password);
    if (res.success) {
      const current = getCurrentSession();
      let detectedPersona = 'user';
      if (current.role === 'TECHNICAL_REVIEWER') detectedPersona = 'reviewer';
      else if (current.role === 'NATIONAL_ADMIN') detectedPersona = 'admin';
      setActivePersona(detectedPersona);
      setSession({
        token: res.token,
        username: username,
        role: current.role,
        email: res.user?.email || null,
        avatar_url: res.user?.avatar_url || null,
        isAuthenticated: true,
      });
      return { success: true };
    }
    return { success: false, error: res.error };
  };

  const register = async ({ username, email, password, role, cpse_id }) => {
    const res = await apiRegister({ username, email, password, role, cpse_id });
    if (res.success) {
      const current = getCurrentSession();
      let detectedPersona = 'user';
      if (current.role === 'TECHNICAL_REVIEWER') detectedPersona = 'reviewer';
      else if (current.role === 'NATIONAL_ADMIN') detectedPersona = 'admin';
      setActivePersona(detectedPersona);
      setSession({
        token: res.token,
        username: username,
        role: current.role,
        email: res.user?.email || email || null,
        isAuthenticated: true,
      });
      return { success: true };
    }
    return { success: false, error: res.error };
  };

  const exchangeOAuthCode = async ({ code, redirectUri, state }) => {
    const res = await exchangeGoogleCode({ code, redirectUri, state });
    if (res.success) {
      const current = getCurrentSession();
      let detectedPersona = 'user';
      if (current.role === 'TECHNICAL_REVIEWER') detectedPersona = 'reviewer';
      else if (current.role === 'NATIONAL_ADMIN') detectedPersona = 'admin';
      setActivePersona(detectedPersona);
      setSession({
        token: res.token,
        username: res.user?.username || 'google_user',
        email: res.user?.email || null,
        role: current.role,
        auth_provider: 'google',
        avatar_url: res.user?.avatar_url || null,
        isAuthenticated: true,
      });
      return { success: true };
    }
    return { success: false, error: res.error };
  };

  const logout = () => {
    clearSession();
    localStorage.removeItem('unifai_email');
    localStorage.removeItem('unifai_avatar');
    localStorage.removeItem('unifai_role');
    localStorage.removeItem('unifai_pending_role');
    localStorage.removeItem('unifai_pending_cpse');
    setActivePersona('user');
    setSession({
      token: null,
      username: 'cpse_user',
      email: null,
      role: 'CPSE_USER',
      isAuthenticated: false,
    });
  };

  const getPersonaConfig = () => {
    if (activePersona === 'reviewer') return PERSONAS.REVIEWER;
    if (activePersona === 'admin') return PERSONAS.ADMIN;
    return PERSONAS.USER;
  };

  return (
    <AuthContext.Provider
      value={{
        activePersona,
        personaConfig: getPersonaConfig(),
        session,
        health,
        switchPersona,
        login,
        register,
        exchangeOAuthCode,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
