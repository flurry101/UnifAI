import React, { useState } from 'react';
import RawCard from './RawCard';
import RawButton from './RawButton';
import RawInput from './RawInput';
import { useAuth } from '../context/AuthContext';

export default function AuthModal({ isOpen, onClose, initialMode = 'login' }) {
  const [mode, setMode] = useState(initialMode); // 'login' | 'register'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('CPSE_USER');
  const [cpseId, setCpseId] = useState('IOCL');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const { login, register, switchPersona } = useAuth();

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg(null);
    setLoading(true);

    try {
      if (mode === 'login') {
        const res = await login(username, password);
        if (res.success) {
          onClose();
        } else {
          setErrorMsg(res.error || 'Authentication failed. Verify credentials.');
        }
      } else {
        const res = await register({
          username,
          password,
          role,
          cpse_id: cpseId,
        });
        if (res.success) {
          onClose();
        } else {
          setErrorMsg(res.error || 'Registration failed.');
        }
      }
    } catch (err) {
      setErrorMsg(err.message || 'Network error.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (personaKey, user, pass) => {
    setErrorMsg(null);
    setLoading(true);
    setUsername(user);
    setPassword(pass);
    const res = await login(user, pass);
    setLoading(false);
    if (res.success) {
      switchPersona(personaKey);
      onClose();
    } else {
      setErrorMsg(res.error || 'Quick login failed');
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-raw-black bg-opacity-75 flex items-center justify-center p-4">
      <div className="max-w-md w-full my-8">
        <RawCard elevated className="bg-raw-white">
          
          {/* Top Bar */}
          <div className="flex items-center justify-between border-b-3 border-raw-black pb-3 mb-4">
            <h2 className="font-headline text-xl text-raw-black uppercase">
              {mode === 'login' ? 'PLATFORM SIGN IN' : 'USER REGISTRATION'}
            </h2>
            <button
              onClick={onClose}
              className="font-mono text-xs font-bold px-2 py-1 border-1 border-raw-black hover:bg-raw-black hover:text-raw-white"
            >
              [ESC]
            </button>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="grid grid-cols-2 gap-2 mb-4">
            <button
              type="button"
              onClick={() => { setMode('login'); setErrorMsg(null); }}
              className={`font-headline text-xs uppercase py-2 border-2 border-raw-black tracking-wider transition-none ${
                mode === 'login' ? 'bg-raw-black text-raw-white' : 'bg-raw-white text-raw-black hover:bg-raw-sunken'
              }`}
            >
              SIGN IN
            </button>
            <button
              type="button"
              onClick={() => { setMode('register'); setErrorMsg(null); }}
              className={`font-headline text-xs uppercase py-2 border-2 border-raw-black tracking-wider transition-none ${
                mode === 'register' ? 'bg-raw-black text-raw-white' : 'bg-raw-white text-raw-black hover:bg-raw-sunken'
              }`}
            >
              REGISTER
            </button>
          </div>

          {errorMsg && (
            <div className="mb-4 p-3 bg-[#FFEBEB] border-2 border-raw-error text-raw-error font-mono text-xs font-bold">
              [AUTH ERROR] {errorMsg}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <RawInput
              label="USERNAME"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. cpse_user"
              required
            />

            <RawInput
              label="PASSWORD"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />

            {mode === 'register' && (
              <>
                <div>
                  <label className="block text-raw-black font-headline text-sm uppercase mb-1 tracking-wider">
                    CPSE ORGANIZATION
                  </label>
                  <select
                    value={cpseId}
                    onChange={(e) => setCpseId(e.target.value)}
                    className="w-full bg-raw-sunken text-raw-black font-mono text-[15px] p-3 border-3 border-raw-black outline-none"
                  >
                    <option value="IOCL">IOCL — Indian Oil</option>
                    <option value="ONGC">ONGC — Oil & Natural Gas Corp</option>
                    <option value="GAIL">GAIL — Gas Authority of India</option>
                    <option value="BPCL">BPCL — Bharat Petroleum</option>
                    <option value="HPCL">HPCL — Hindustan Petroleum</option>
                    <option value="NTPC">NTPC — National Thermal Power</option>
                    <option value="SAIL">SAIL — Steel Authority of India</option>
                    <option value="COAL_INDIA">Coal India Limited</option>
                    <option value="BHEL">BHEL — Bharat Heavy Electricals</option>
                    <option value="CENTRAL">Central Governance Board</option>
                  </select>
                </div>

                <div>
                  <label className="block text-raw-black font-headline text-sm uppercase mb-1 tracking-wider">
                    ASSIGNED ROLE
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full bg-raw-sunken text-raw-black font-mono text-[15px] p-3 border-3 border-raw-black outline-none"
                  >
                    <option value="CPSE_USER">USER (CPSE Operational Material Management)</option>
                    <option value="TECHNICAL_REVIEWER">REVIEWER (Technical Governance & Validation)</option>
                    <option value="NATIONAL_ADMIN">ADMIN (National Master Catalog Custodian)</option>
                  </select>
                </div>
              </>
            )}

            <RawButton
              type="submit"
              variant="primary"
              size="medium"
              disabled={loading}
              className="w-full mt-2"
            >
              {loading ? 'PROCESSING...' : mode === 'login' ? 'SIGN IN →' : 'REGISTER & SIGN IN →'}
            </RawButton>
          </form>

          {/* Quick 1-click test credentials strip */}
          {mode === 'login' && (
            <div className="mt-6 pt-4 border-t-2 border-raw-black">
              <span className="font-headline text-[10px] text-[#555555] uppercase block mb-2 tracking-wider">
                ONE-CLICK SEEDED CREDENTIALS:
              </span>
              <div className="grid grid-cols-3 gap-2 font-mono text-xs">
                <button
                  type="button"
                  onClick={() => handleQuickLogin('user', 'cpse_user', 'password123')}
                  className="p-1.5 border-1 border-raw-black bg-raw-sunken text-center hover:bg-raw-black hover:text-raw-white font-bold"
                >
                  USER
                </button>
                <button
                  type="button"
                  onClick={() => handleQuickLogin('reviewer', 'reviewer', 'password123')}
                  className="p-1.5 border-1 border-raw-black bg-raw-sunken text-center hover:bg-raw-black hover:text-raw-white font-bold"
                >
                  REVIEWER
                </button>
                <button
                  type="button"
                  onClick={() => handleQuickLogin('admin', 'admin', 'password123')}
                  className="p-1.5 border-1 border-raw-black bg-raw-sunken text-center hover:bg-raw-black hover:text-raw-white font-bold"
                >
                  ADMIN
                </button>
              </div>
            </div>
          )}

        </RawCard>
      </div>
    </div>
  );
}

