import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Header from './components/Header';
import Footer from './components/Footer';
import AuthModal from './components/AuthModal';
import OAuthCallback from './components/OAuthCallback';
import LandingView from './views/LandingView';
import UserView from './views/UserView';
import ReviewerView from './views/ReviewerView';
import AdminView from './views/AdminView';
import AuditorView from './views/AuditorView';

function AppContent() {
  const { session, activePersona } = useAuth();
  const [currentView, setCurrentView] = useState('landing');
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');

  const isOAuthCallback = window.location.pathname.startsWith('/auth/google/callback');

  const handleViewChange = (viewName) => {
    setCurrentView(viewName);
    window.scrollTo({ top: 0, behavior: 'instant' });
  };

  const handleOpenAuthModal = (mode = 'login') => {
    setAuthModalMode(mode);
    setIsAuthModalOpen(true);
  };

  return (
    <div className="min-h-screen flex flex-col bg-raw-white text-raw-black">
      {/* Header */}
      <Header
        currentView={currentView}
        onViewChange={handleViewChange}
        onOpenAuthModal={handleOpenAuthModal}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {isOAuthCallback ? (
          <OAuthCallback onComplete={() => handleViewChange(activePersona || 'user')} />
        ) : (
          <>
            {currentView === 'landing' && (
              <LandingView
                onSelectView={handleViewChange}
                onOpenAuthModal={handleOpenAuthModal}
              />
            )}
            {currentView === 'user' && <UserView />}
            {currentView === 'reviewer' && <ReviewerView />}
            {currentView === 'admin' && <AdminView />}
            {currentView === 'auditor' && <AuditorView />}
          </>
        )}
      </main>

      {/* Mandatory Brutalist Footer */}
      <Footer />

      {/* Traditional Authentication Modal (Sign In & Sign Up) */}
      <AuthModal
        isOpen={isAuthModalOpen}
        initialMode={authModalMode}
        onClose={() => {
          setIsAuthModalOpen(false);
          // If signed in, switch to their authorized persona view
          if (session.token) {
            handleViewChange(activePersona);
          }
        }}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
