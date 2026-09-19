import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Header from './components/Header';
import Footer from './components/Footer';
import RbacStatusModal from './components/RbacStatusModal';
import LandingView from './views/LandingView';
import UserView from './views/UserView';
import ReviewerView from './views/ReviewerView';
import AdminView from './views/AdminView';

function AppContent() {
  const { activePersona } = useAuth();
  const [currentView, setCurrentView] = useState('landing');
  const [isRbacModalOpen, setIsRbacModalOpen] = useState(false);

  const handleViewChange = (viewName) => {
    setCurrentView(viewName);
    window.scrollTo({ top: 0, behavior: 'instant' });
  };

  return (
    <div className="min-h-screen flex flex-col bg-raw-white text-raw-black">
      {/* Header */}
      <Header
        currentView={currentView}
        onViewChange={handleViewChange}
        onOpenRbacModal={() => setIsRbacModalOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {currentView === 'landing' && (
          <LandingView onSelectView={handleViewChange} />
        )}
        {currentView === 'user' && <UserView />}
        {currentView === 'reviewer' && <ReviewerView />}
        {currentView === 'admin' && (
          <AdminView onOpenRbacModal={() => setIsRbacModalOpen(true)} />
        )}
      </main>

      {/* Mandatory Brutalist Footer */}
      <Footer />

      {/* RBAC Security Inspection Modal */}
      <RbacStatusModal
        isOpen={isRbacModalOpen}
        onClose={() => setIsRbacModalOpen(false)}
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

