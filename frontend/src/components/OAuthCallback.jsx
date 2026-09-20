import React, { useEffect, useState } from 'react';
import RawCard from './RawCard';
import RawButton from './RawButton';
import { useAuth } from '../context/AuthContext';
import { getUserProfile } from '../api/auth';
import { supabase } from '../api/supabase';

/**
 * Synapse-aligned SSO / OAuth Callback Handler (mirrors frontend/src/routes/sso.login.tsx)
 * Exchanges a state-bound authorization code or Supabase session and routes the verified session.
 */
export default function OAuthCallback({ onComplete }) {
  const { exchangeSupabaseSession, switchPersona } = useAuth();
  const [status, setStatus] = useState('processing'); // 'processing' | 'error' | 'success'
  const [errorMessage, setErrorMessage] = useState('');
  const [welcomeText, setWelcomeText] = useState('');

  useEffect(() => {
    let resolved = false;
    let subscription = null;

    const handleSuccess = async (targetPersona, username, role) => {
      if (resolved) return;
      resolved = true;
      subscription?.unsubscribe();
      setStatus('success');
      switchPersona(targetPersona);
      setWelcomeText(`Authenticated as ${username || 'User'} (${role || 'CPSE_USER'}).`);
      window.history.replaceState({}, document.title, '/');
      setTimeout(() => onComplete?.(targetPersona), 800);
    };

    const processSupabaseSession = async (session) => {
      if (resolved) return false;
      try {
        const res = await exchangeSupabaseSession(session.access_token);
        if (res.success) {
          const profile = await getUserProfile();
          const effectiveRole = profile?.role || 'CPSE_USER';
          const targetPersona = effectiveRole === 'TECHNICAL_REVIEWER' ? 'reviewer' : (effectiveRole === 'NATIONAL_ADMIN' ? 'admin' : 'user');
          await handleSuccess(targetPersona, profile?.username, effectiveRole);
          return true;
        } else {
          if (!resolved) {
            resolved = true;
            subscription?.unsubscribe();
            setStatus('error');
            setErrorMessage(res.error || 'Failed to link Supabase session with UnifAI.');
          }
          return false;
        }
      } catch (err) {
        if (!resolved) {
          resolved = true;
          subscription?.unsubscribe();
          setStatus('error');
          setErrorMessage(err.message || 'Error processing Supabase session.');
        }
        return false;
      }
    };

    const handleCallback = async () => {
      const searchParams = new URLSearchParams(window.location.search);
      const error = searchParams.get('error') || new URLSearchParams(window.location.hash.replace(/^#/, '')).get('error');
      const errorDescription = searchParams.get('error_description') || new URLSearchParams(window.location.hash.replace(/^#/, '')).get('error_description');

      if (error) {
        setStatus('error');
        setErrorMessage(errorDescription || error || 'OAuth authorization was denied or cancelled.');
        return;
      }

      // Cookie-based server-side session (legacy Synapse SSO path)
      if (searchParams.get('session') === 'established') {
        try {
          const profile = await getUserProfile();
          if (!profile) throw new Error('Failed to verify SSO session.');
          const effectiveRole = profile.role || 'CPSE_USER';
          const targetPersona = effectiveRole === 'TECHNICAL_REVIEWER' ? 'reviewer' : (effectiveRole === 'NATIONAL_ADMIN' ? 'admin' : 'user');
          await handleSuccess(targetPersona, profile.username, effectiveRole);
        } catch (err) {
          setStatus('error');
          setErrorMessage(err.message || 'Failed to verify SSO session.');
        }
        return;
      }

      // Supabase PKCE / implicit flow:
      // detectSessionInUrl:true auto-exchanges the ?code= on client init and fires SIGNED_IN.
      // Register onAuthStateChange FIRST to catch the event, then check getSession() in
      // case the exchange already completed synchronously before we registered.

      const { data: { subscription: sub } } = supabase.auth.onAuthStateChange(async (event, session) => {
        if ((event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') && session && !resolved) {
          await processSupabaseSession(session);
        }
      });
      subscription = sub;

      // Check if Supabase already finished the exchange (synchronous fast path)
      try {
        const { data: sessionData } = await supabase.auth.getSession();
        if (sessionData?.session && !resolved) {
          await processSupabaseSession(sessionData.session);
          return;
        }
      } catch (_) { /* ignore, listener will catch it */ }

      // If no code or hash token at all, nothing to wait for
      if (!searchParams.get('code') && !window.location.hash.includes('access_token')) {
        subscription?.unsubscribe();
        setStatus('error');
        setErrorMessage('No OAuth session or code found in callback URL. Please try signing in again.');
        return;
      }

      // Otherwise wait for the SIGNED_IN event (Supabase is still processing the code)
      // Timeout after 15 seconds
      setTimeout(() => {
        if (!resolved) {
          subscription?.unsubscribe();
          setStatus('error');
          setErrorMessage('Google sign-in timed out. Please try again.');
        }
      }, 15000);
    };

    handleCallback();

    return () => { subscription?.unsubscribe(); };
  }, []);

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
