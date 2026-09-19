import React, { useState } from 'react';
import RawCard from './RawCard';
import RawButton from './RawButton';
import RawInput from './RawInput';
import { useAuth } from '../context/AuthContext';
import { getGoogleOAuthUrl } from '../api/auth';

export default function AuthModal({ isOpen, onClose, initialMode = 'login' }) {
  const [mode, setMode] = useState(initialMode); // 'login' | 'register'
  const [identifier, setIdentifier] = useState(''); // username or email
  const [email, setEmail] = useState('');
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
        const res = await login(identifier, password);
        if (res.success) {
          onClose();
        } else {
          setErrorMsg(res.error || 'Authentication failed. Check your email/username and password.');
        }
      } else {
        const res = await register({
          username: identifier,
          email: email || undefined,
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

  const handleGoogleClick = async () => {
    setErrorMsg(null);
    setLoading(true);
    try {
      // Store preferred role and CPSE organization for provisioning after callback
      localStorage.setItem('unifai_pending_role', role);
      localStorage.setItem('unifai_pending_cpse', cpseId);

      const redirectUri = `${window.location.origin}/auth/google/callback`;
      const urlRes = await getGoogleOAuthUrl(redirectUri);

      if (urlRes.configured && urlRes.oauth_url) {
        // Traditional Google OAuth Redirect to Google Cloud Identity consent screen
        window.location.href = urlRes.oauth_url;
      } else {
        setErrorMsg(
          urlRes.message ||
          'Google OAuth is not configured with active credentials. Please provide GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.'
        );
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to initiate Google OAuth redirect.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (personaKey, user, pass) => {
    setErrorMsg(null);
    setLoading(true);
    setIdentifier(user);
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
      <div className="max-w-md w-full my-8 max-h-[90vh] overflow-y-auto">
        <RawCard elevated className="bg-raw-white">

          {/* Top Bar */}
          <div className="flex items-center justify-between border-b-3 border-raw-black pb-3 mb-4">
            <h2 className="font-headline text-xl text-raw-black uppercase tracking-tight">
              {mode === 'login' ? 'PLATFORM SIGN IN' : 'USER REGISTRATION'}
            </h2>
            <button
              onClick={onClose}
              className="font-mono text-xs font-bold px-2 py-1 border-2 border-raw-black hover:bg-raw-black hover:text-raw-white transition-none"
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
            <div className="mb-4 p-3 bg-[#FFEBEB] border-2 border-raw-error text-raw-error font-mono text-xs font-bold leading-relaxed">
              [AUTH ERROR] {errorMsg}
            </div>
          )}

          {/* Traditional Google OAuth Button */}
          <div className="mb-4">
            <button
              type="button"
              onClick={handleGoogleClick}
              disabled={loading}
              className="w-full flex items-center justify-center py-3 px-4 border-3 border-raw-black bg-raw-white text-raw-black hover:bg-raw-sunken font-headline text-xs tracking-wider uppercase font-bold transition-none"
            >
              {/* Official Google 'G' Logo SVG */}
              <svg className="w-5 h-5 mr-3 shrink-0" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
              </svg>
              {mode === 'login' ? 'SIGN IN WITH GOOGLE' : 'REGISTER WITH GOOGLE'}
            </button>
          </div>

          {/* Divider */}
          <div className="flex items-center my-4">
            <div className="flex-1 border-t-2 border-raw-black"></div>
            <span className="px-3 font-headline text-[10px] uppercase tracking-widest text-[#555] bg-raw-white">
              OR CONTINUE WITH EMAIL
            </span>
            <div className="flex-1 border-t-2 border-raw-black"></div>
          </div>

          {/* Email / Username Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <RawInput
              label={mode === 'login' ? 'EMAIL OR USERNAME' : 'USERNAME'}
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder={mode === 'login' ? 'e.g. cpse_user or officer@iocl.co.in' : 'e.g. ongc_engineer'}
              required
            />

            {mode === 'register' && (
              <RawInput
                label="OFFICIAL CPSE EMAIL"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g. engineer@ongc.co.in"
                required
              />
            )}

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
                    className="w-full bg-raw-sunken text-raw-black font-mono text-[13px] p-3 border-3 border-raw-black outline-none"
                  >
                    <optgroup label="── OIL &amp; GAS ──">
                      <option value="ONGC">ONGC — Oil &amp; Natural Gas Corporation</option>
                      <option value="IOCL">IOCL — Indian Oil Corporation</option>
                      <option value="GAIL">GAIL — Gas Authority of India</option>
                      <option value="HPCL">HPCL — Hindustan Petroleum</option>
                      <option value="BPCL">BPCL — Bharat Petroleum</option>
                      <option value="CPCL">CPCL — Chennai Petroleum</option>
                    </optgroup>
                    <optgroup label="── POWER ──">
                      <option value="NTPC">NTPC — National Thermal Power</option>
                      <option value="NHPC">NHPC — National Hydroelectric Power</option>
                      <option value="POWERGRID">POWERGRID — Power Grid Corporation</option>
                    </optgroup>
                    <optgroup label="── STEEL ──">
                      <option value="SAIL">SAIL — Steel Authority of India</option>
                      <option value="RINL">RINL — Rashtriya Ispat Nigam</option>
                    </optgroup>
                    <optgroup label="── MINING ──">
                      <option value="COAL_INDIA">Coal India Limited</option>
                      <option value="NMDC">NMDC — National Mineral Development</option>
                    </optgroup>
                    <optgroup label="── HEAVY ENGINEERING ──">
                      <option value="BHEL">BHEL — Bharat Heavy Electricals</option>
                    </optgroup>
                    <optgroup label="── DEFENCE ELECTRONICS ──">
                      <option value="BEL">BEL — Bharat Electronics</option>
                    </optgroup>
                  </select>
                </div>

                <div>
                  <label className="block text-raw-black font-headline text-sm uppercase mb-1 tracking-wider">
                    ASSIGNED ROLE
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full bg-raw-sunken text-raw-black font-mono text-[13px] p-3 border-3 border-raw-black outline-none"
                  >
                    <option value="CPSE_USER">USER — CPSE Operational Material Management</option>
                    <option value="TECHNICAL_REVIEWER">REVIEWER — Technical Governance &amp; Validation</option>
                    <option value="NATIONAL_ADMIN">ADMIN — National Master Catalog Custodian</option>
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
              {loading ? 'PROCESSING...' : mode === 'login' ? 'SIGN IN WITH EMAIL →' : 'REGISTER & SIGN IN →'}
            </RawButton>
          </form>

        </RawCard>
      </div>
    </div>
  );
}
