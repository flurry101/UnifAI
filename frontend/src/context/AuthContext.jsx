import React, { createContext, useContext, useState, useEffect } from 'react';
import { PERSONAS, getCurrentSession, saveSession, clearSession, loginWithCredentials as apiLogin, registerUser as apiRegister } from '../api/auth';
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
    setSession(prev => ({
      ...prev,
      username: persona.defaultUsername,
      role: persona.role,
    }));
    saveSession(pKey.toUpperCase(), session.token);
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
        isAuthenticated: true,
      });
      return { success: true };
    }
    return { success: false, error: res.error };
  };

  const register = async ({ username, password, role, cpse_id }) => {
    const res = await apiRegister({ username, password, role, cpse_id });
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
        isAuthenticated: true,
      });
      return { success: true };
    }
    return { success: false, error: res.error };
  };

  const logout = () => {
    clearSession();
    setActivePersona('user');
    setSession({
      token: null,
      username: 'cpse_user',
      role: 'CPSE_USER',
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

