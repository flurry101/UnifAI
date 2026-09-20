import React, { useEffect, useState } from 'react';
import RawCard from './RawCard';
import RawButton from './RawButton';
import { useAuth } from '../context/AuthContext';
import { getUserProfile } from '../api/auth';

/**
 * Synapse-aligned SSO / OAuth Callback Handler (mirrors frontend/src/routes/sso.login.tsx)
 * Exchanges a state-bound authorization code and routes the verified session.
 */
export default function OAuthCallback({ onComplete }) {
  const { exchangeOAuthCode, switchPersona } = useAuth();
  const [status, setStatus] = useState('processing'); // 'processing' | 'error' | 'success'
  const [errorMessage, setErrorMessage] = useState('');
  const [welcomeText, setWelcomeText] = useState('');

  useEffect(() => {
    handleCallback();
  }, []);

  const handleCallback = async () => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const returnedState = params.get('state');
    const error = params.get('error');
    const errorDescription = params.get('error_description');

    const expectedState = sessionStorage.getItem('unifai_oauth_state');
    sessionStorage.removeItem('unifai_oauth_state');
    if (!expectedState || !returnedState || expectedState !== returnedState) {
      setStatus('error');
      setErrorMessage('OAuth state validation failed. Please restart sign-in.');
      return;
    }

    if (error) {
      setStatus('error');
      setErrorMessage(errorDescription || error || 'Google OAuth authorization was denied or cancelled.');
      return;
    }

    if (params.get('session') === 'established') {
      try {
        const profile = await getUserProfile();
        if (!profile) throw new Error('Failed to verify SSO session.');
        const effectiveRole = profile.role || 'CPSE_USER';
        const targetPersona = effectiveRole === 'TECHNICAL_REVIEWER' ? 'reviewer' : (effectiveRole === 'NATIONAL_ADMIN' ? 'admin' : 'user');
        switchPersona(targetPersona);
        setWelcomeText(`Authenticated as ${profile.username || 'User'} (${effectiveRole}).`);
        setStatus('success');
        window.history.replaceState({}, document.title, '/');
        setTimeout(() => onComplete?.(targetPersona), 800);
      } catch (err) {
        setStatus('error');
        setErrorMessage(err.message || 'Failed to verify SSO session.');
      }
      return;
    }

    if (code) {
      try {
        const redirectUri = `${window.location.origin}/auth/google/callback`;

        const res = await exchangeOAuthCode({
          code,
          redirectUri,
          state: returnedState,
        });

        if (res.success) {
          setStatus('success');
          const profile = await getUserProfile();
          const effectiveRole = profile?.role || 'CPSE_USER';
          const targetPersona = effectiveRole === 'TECHNICAL_REVIEWER' ? 'reviewer' : (effectiveRole === 'NATIONAL_ADMIN' ? 'admin' : 'user');

          switchPersona(targetPersona);
          setWelcomeText(`Authenticated as ${profile?.username || 'User'} (${effectiveRole}).`);

          // Clear query parameters from URL cleanly
          window.history.replaceState({}, document.title, window.location.pathname.replace('/auth/google/callback', '/') || '/');

          setTimeout(() => {
            if (onComplete) onComplete(targetPersona);
          }, 800);
        } else {
          setStatus('error');
          setErrorMessage(res.error || 'Failed to exchange Google OAuth code.');
        }
      } catch (err) {
        setStatus('error');
        setErrorMessage(err.message || 'Unexpected error during Google OAuth callback.');
      }
      return;
    }

    setStatus('error');
    setErrorMessage('Missing OAuth authorization parameters in callback URL.');
  };

  const handleReturnHome = () => {
    window.location.href = '/';
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <RawCard elevated className="bg-raw-white p-6">
          <div className="border-b-3 border-raw-black pb-3 mb-4">
            <h2 className="font-headline text-lg text-raw-black uppercase tracking-tight">
              GOOGLE CLOUD IDENTITY AUTHENTICATION
            </h2>
          </div>

          {status === 'processing' && (
            <div className="space-y-4 font-mono text-xs">
              <div className="p-4 bg-raw-sunken border-2 border-raw-black">
                <div className="flex items-center gap-3 mb-2">
                  <span className="inline-block w-3 h-3 bg-raw-black animate-ping"></span>
                  <span className="font-bold text-raw-black">VERIFYING AUTHORIZATION TOKEN...</span>
                </div>
                <p className="text-[#444] text-[11px] leading-relaxed">
                  Exchanging Google OAuth 2.0 authorization code with CNMC security gateway and provisioning enterprise credentials.
                </p>
              </div>
            </div>
          )}

          {status === 'success' && (
            <div className="space-y-4 font-mono text-xs">
              <div className="p-4 bg-[#EBFEEB] border-2 border-raw-success text-raw-success font-bold leading-relaxed">
                <div>✓ GOOGLE AUTHENTICATION SUCCESSFUL.</div>
                <div className="text-[11px] mt-1 text-[#2e7d32]">{welcomeText}</div>
                <div className="text-[10px] mt-1 text-[#555]">REDIRECTING TO SECURE WORKSPACE...</div>
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="space-y-4">
              <div className="p-4 bg-[#FFEBEB] border-2 border-raw-error text-raw-error font-mono text-xs font-bold leading-relaxed">
                [OAUTH ERROR] {errorMessage}
              </div>
              <p className="font-sans text-xs text-[#555]">
                If this is a local development instance, ensure <strong>GOOGLE_CLIENT_ID</strong> and <strong>GOOGLE_CLIENT_SECRET</strong> are configured in your <code>.env</code> file with authorized redirect URI <code>{window.location.origin}/auth/google/callback</code>.
              </p>
              <RawButton
                variant="primary"
                size="medium"
                onClick={handleReturnHome}
                className="w-full"
              >
                ← RETURN TO PLATFORM
              </RawButton>
            </div>
          )}
        </RawCard>
      </div>
    </div>
  );
}
