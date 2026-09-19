import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import StatusChip from './StatusChip';
import RawButton from './RawButton';

export default function Header({ onOpenRbacModal, currentView, onViewChange }) {
  const { activePersona, switchPersona, health } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const personas = [
    { id: 'user', label: 'USER' },
    { id: 'reviewer', label: 'REVIEWER' },
    { id: 'admin', label: 'ADMIN' },
  ];

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
              className="w-9 h-9 border-2 border-raw-black object-contain bg-raw-white"
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
            <button
              onClick={onOpenRbacModal}
              className="font-mono text-xs uppercase underline hover:bg-raw-black hover:text-raw-white px-1"
              title="Inspect backend RBAC security and role mapping"
            >
              [RBAC AUDIT]
            </button>
          </div>
        </div>

        {/* Desktop Role Switcher / Navigation */}
        <div className="hidden md:flex items-center gap-2">
          <span className="font-mono text-xs uppercase font-bold text-[#555555] mr-1">
            VIEW AS:
          </span>
          {personas.map((p) => {
            const isActive = activePersona === p.id && currentView !== 'landing';
            return (
              <button
                key={p.id}
                onClick={() => {
                  switchPersona(p.id);
                  onViewChange(p.id);
                }}
                className={`font-headline text-xs uppercase px-3 py-1.5 border-2 border-raw-black tracking-widest transition-none ${
                  isActive
                    ? 'bg-raw-black text-raw-white'
                    : 'bg-raw-white text-raw-black hover:bg-raw-black hover:text-raw-white'
                }`}
              >
                {p.label}
              </button>
            );
          })}
        </div>

        {/* Mobile Toggle Button */}
        <div className="md:hidden flex items-center gap-2">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="border-2 border-raw-black px-2.5 py-1 font-headline text-xs uppercase bg-raw-white text-raw-black"
          >
            {mobileMenuOpen ? 'CLOSE ✕' : 'ROLES ☰'}
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
            <button
              onClick={() => {
                onOpenRbacModal();
                setMobileMenuOpen(false);
              }}
              className="font-mono text-xs underline font-bold"
            >
              [INSPECT RBAC]
            </button>
          </div>
          <div className="font-mono text-xs font-bold text-raw-black mt-2">
            SWITCH STAKEHOLDER VIEW:
          </div>
          <div className="grid grid-cols-3 gap-2">
            {personas.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  switchPersona(p.id);
                  onViewChange(p.id);
                  setMobileMenuOpen(false);
                }}
                className={`font-headline text-xs uppercase py-2 border-2 border-raw-black text-center ${
                  activePersona === p.id && currentView !== 'landing'
                    ? 'bg-raw-black text-raw-white'
                    : 'bg-raw-white text-raw-black'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}

