import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import StatusChip from './StatusChip';
import RawButton from './RawButton';

export default function Header({ currentView, onViewChange, onOpenAuthModal }) {
  const { session, logout, activePersona, switchPersona, health } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const getRoleLabel = () => {
    if (activePersona === 'reviewer') return 'REVIEWER';
    if (activePersona === 'admin') return 'ADMIN';
    return 'USER';
  };

  return (
    <header className="border-b-3 border-raw-black bg-raw-white sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3">
        
        {/* Corner Logo (no black box border around image) */}
        <div className="flex items-center gap-3">
          <a
            href="#landing"
            onClick={(e) => {
              e.preventDefault();
              onViewChange('landing');
            }}
            className="flex items-center gap-2 group !no-underline"
          >
            <img
              src="/assets/favicon.png"
              alt="unifAI Logo"
              className="w-9 h-9 object-contain bg-transparent"
            />
            <span className="font-headline text-2xl tracking-tighter text-raw-black group-hover:bg-raw-black group-hover:text-raw-white px-1">
              unifAI
            </span>
          </a>

          {/* System Status */}
          <div className="hidden sm:flex items-center gap-2 pl-3 border-l-2 border-raw-black">
            <StatusChip
              label={health.online ? 'SYSTEM ONLINE' : 'BACKEND OFFLINE'}
              status={health.online ? 'active' : 'warning'}
            />
          </div>
        </div>

        {/* Desktop Navigation & Authentication Controls */}
        <div className="hidden md:flex items-center gap-3">
          
          {session.token ? (
            <div className="flex items-center gap-3">
              {/* Active Workspace Link */}
              <button
                onClick={() => onViewChange(activePersona)}
                className={`font-headline text-xs uppercase px-3 py-1.5 border-2 border-raw-black tracking-wider transition-none ${
                  currentView === activePersona
                    ? 'bg-raw-black text-raw-white'
                    : 'bg-raw-white text-raw-black hover:bg-raw-black hover:text-raw-white'
                }`}
              >
                OPEN {getRoleLabel()} WORKSPACE →
              </button>

              {/* User Identity Pill */}
              <div className="font-mono text-xs border-2 border-raw-black px-2.5 py-1 bg-raw-sunken flex items-center gap-1.5">
                <span className="font-bold text-raw-black">{session.username}</span>
                <span className="bg-raw-black text-raw-white px-1 text-[10px] font-bold">
                  {getRoleLabel()}
                </span>
              </div>

              {/* Sign Out Button */}
              <button
                onClick={() => {
                  logout();
                  onViewChange('landing');
                }}
                className="font-headline text-xs uppercase px-3 py-1.5 border-2 border-raw-black bg-raw-white text-raw-black hover:bg-raw-black hover:text-raw-white tracking-wider"
              >
                SIGN OUT
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => onOpenAuthModal('login')}
                className="font-headline text-xs uppercase px-4 py-1.5 border-2 border-raw-black bg-raw-white text-raw-black hover:bg-raw-black hover:text-raw-white tracking-wider"
              >
                SIGN IN
              </button>
              <button
                onClick={() => onOpenAuthModal('register')}
                className="font-headline text-xs uppercase px-4 py-1.5 border-2 border-raw-black bg-raw-black text-raw-white hover:bg-raw-white hover:text-raw-black tracking-wider"
              >
                REGISTER
              </button>
            </div>
          )}

        </div>

        {/* Mobile Toggle Button */}
        <div className="md:hidden flex items-center gap-2">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="border-2 border-raw-black px-2.5 py-1 font-headline text-xs uppercase bg-raw-white text-raw-black"
          >
            {mobileMenuOpen ? 'CLOSE ✕' : 'MENU ☰'}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t-2 border-raw-black p-4 bg-raw-sunken flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <StatusChip
              label={health.online ? 'SYSTEM ONLINE' : 'BACKEND OFFLINE'}
              status={health.online ? 'active' : 'warning'}
            />
          </div>

          {session.token ? (
            <div className="space-y-2 mt-2">
              <div className="font-mono text-xs p-2 bg-raw-white border-1 border-raw-black flex justify-between">
                <span>USER: <strong>{session.username}</strong></span>
                <span className="bg-raw-black text-raw-white px-1 text-[10px] font-bold">
                  {getRoleLabel()}
                </span>
              </div>
              <button
                onClick={() => {
                  onViewChange(activePersona);
                  setMobileMenuOpen(false);
                }}
                className="w-full font-headline text-xs uppercase py-2 border-2 border-raw-black bg-raw-black text-raw-white text-center"
              >
                OPEN {getRoleLabel()} WORKSPACE
              </button>
              <button
                onClick={() => {
                  logout();
                  onViewChange('landing');
                  setMobileMenuOpen(false);
                }}
                className="w-full font-headline text-xs uppercase py-2 border-2 border-raw-black bg-raw-white text-raw-black text-center"
              >
                SIGN OUT
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-2 mt-2">
              <button
                onClick={() => {
                  onOpenAuthModal('login');
                  setMobileMenuOpen(false);
                }}
                className="font-headline text-xs uppercase py-2 border-2 border-raw-black bg-raw-white text-raw-black text-center"
              >
                SIGN IN
              </button>
              <button
                onClick={() => {
                  onOpenAuthModal('register');
                  setMobileMenuOpen(false);
                }}
                className="font-headline text-xs uppercase py-2 border-2 border-raw-black bg-raw-black text-raw-white text-center"
              >
                REGISTER
              </button>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
