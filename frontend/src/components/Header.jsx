import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getAccessibleWorkspaces } from '../api/auth';
import StatusChip from './StatusChip';
import RawButton from './RawButton';

export default function Header({ currentView, onViewChange, onOpenAuthModal }) {
  const { session, logout, switchPersona, health } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const workspaces = getAccessibleWorkspaces(session.role);
  const currentWorkspace = workspaces.find((w) => w.id === currentView);

  return (
    <header className="border-b-3 border-raw-black bg-raw-white sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3">
        
        {/* Corner Logo */}
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
          {/* CPSE Geo-Radar Access Button */}
          <button
            onClick={() => onViewChange('georadar')}
            className={`font-headline text-xs uppercase px-3 py-1.5 border-2 border-raw-black tracking-wider flex items-center gap-1.5 transition-none ${
              currentView === 'georadar'
                ? 'bg-raw-black text-raw-white font-bold'
                : 'bg-raw-white text-raw-black hover:bg-raw-black hover:text-raw-white'
            }`}
            title="Inter-CPSE Geospatial Spares Radar"
          >
            <span>📍</span>
            <span>CPSE GEO-RADAR</span>
          </button>
          {session.token ? (
            <div className="flex items-center gap-3">
              {/* Workspace Switcher Bar */}
              {workspaces.length > 1 ? (
                <div className="flex items-center border-2 border-raw-black bg-raw-white">
                  {workspaces.map((ws, idx) => (
                    <button
                      key={ws.id}
                      onClick={() => {
                        switchPersona(ws.id);
                        onViewChange(ws.id);
                      }}
                      className={`font-headline text-xs uppercase px-2.5 py-1.5 tracking-wider transition-none ${
                        idx > 0 ? 'border-l-2 border-raw-black' : ''
                      } ${
                        currentView === ws.id
                          ? 'bg-raw-black text-raw-white font-bold'
                          : 'bg-raw-white text-raw-black hover:bg-raw-black hover:text-raw-white'
                      }`}
                      title={ws.tagline}
                    >
                      {ws.shortLabel}
                    </button>
                  ))}
                </div>
              ) : (
                <button
                  onClick={() => onViewChange(workspaces[0].id)}
                  className={`font-headline text-xs uppercase px-3 py-1.5 border-2 border-raw-black tracking-wider transition-none ${
                    currentView === workspaces[0].id
                      ? 'bg-raw-black text-raw-white font-bold'
                      : 'bg-raw-white text-raw-black hover:bg-raw-black hover:text-raw-white'
                  }`}
                  title={workspaces[0].tagline}
                >
                  OPEN {workspaces[0].shortLabel} WORKSPACE →
                </button>
              )}

              {/* User Identity Pill */}
              <div className="font-mono text-xs border-2 border-raw-black px-2.5 py-1 bg-raw-sunken flex items-center gap-1.5">
                <span className="font-bold text-raw-black">{session.username}</span>
                <span className="bg-raw-black text-raw-white px-1 text-[10px] font-bold">
                  CPSE USER
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

      {/* Stakeholder Clarity & Context Tagline Sub-bar */}
      {currentView !== 'landing' && (
        <div className="border-t-2 border-raw-black bg-raw-sunken px-4 sm:px-6 py-1.5 text-xs font-mono flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="bg-raw-black text-raw-white px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider">
              SCOPE: {currentWorkspace?.label || currentView.toUpperCase()}
            </span>
            <span className="text-raw-black font-medium">
              {currentWorkspace?.tagline || 'CPSE Material Master Harmonization Platform'}
            </span>
          </div>
          <div className="text-[11px] text-[#555] hidden sm:block">
            STAKEHOLDER ROLE: <strong className="text-raw-black">CPSE USER</strong>
            {' (Unified CPSE Access: Harmonization, Review, CNMC & Audit)'}
          </div>
        </div>
      )}

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t-2 border-raw-black p-4 bg-raw-sunken flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <StatusChip
              label={health.online ? 'SYSTEM ONLINE' : 'BACKEND OFFLINE'}
              status={health.online ? 'active' : 'warning'}
            />
          </div>

          {/* Mobile CPSE Geo-Radar Access */}
          <button
            onClick={() => {
              onViewChange('georadar');
              setMobileMenuOpen(false);
            }}
            className={`w-full font-headline text-xs uppercase py-2 border-2 border-raw-black tracking-wider flex items-center justify-center gap-1.5 transition-none ${
              currentView === 'georadar'
                ? 'bg-raw-black text-raw-white font-bold'
                : 'bg-raw-white text-raw-black'
            }`}
          >
            <span>📍</span>
            <span>OPEN CPSE GEO-RADAR</span>
          </button>

          {session.token ? (
            <div className="space-y-2 mt-2">
              <div className="font-mono text-xs p-2 bg-raw-white border-1 border-raw-black flex justify-between">
                <span>USER: <strong>{session.username}</strong></span>
                <span className="bg-raw-black text-raw-white px-1 text-[10px] font-bold">
                  CPSE USER
                </span>
              </div>

              {/* Accessible Workspaces for Mobile */}
              <div className="flex flex-col gap-1.5">
                {workspaces.map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => {
                      switchPersona(ws.id);
                      onViewChange(ws.id);
                      setMobileMenuOpen(false);
                    }}
                    className={`w-full font-headline text-xs uppercase py-2 border-2 border-raw-black text-left px-3 ${
                      currentView === ws.id ? 'bg-raw-black text-raw-white font-bold' : 'bg-raw-white text-raw-black'
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span>{ws.label}</span>
                      <span className="text-[10px] font-mono opacity-75">{ws.tagline}</span>
                    </div>
                  </button>
                ))}
              </div>

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
