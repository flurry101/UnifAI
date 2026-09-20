import React from 'react';
import RawButton from '../components/RawButton';
import RawCard from '../components/RawCard';
import SectorGrid from '../components/SectorGrid';
import { useAuth } from '../context/AuthContext';

export default function LandingView({ onSelectView, onOpenAuthModal }) {
  const { session, activePersona } = useAuth();

  const handleEnter = () => {
    if (session.token) {
      onSelectView(activePersona);
    } else {
      onOpenAuthModal('login');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 md:py-16">
      
      {/* Hero Section */}
      <div className="border-5 border-raw-black p-6 md:p-12 bg-raw-white mb-12">
        
        {/* Punchy Product Tagline */}
        <div className="border-b-3 border-raw-black pb-4 mb-6">
          <div className="font-mono text-xs uppercase tracking-widest text-[#555555] mb-2 font-bold">
            NATIONAL UNIFIED MATERIAL MASTER PLATFORM
          </div>
          <h1 className="font-headline text-3xl sm:text-5xl md:text-6xl text-raw-black leading-[1.05] tracking-tight uppercase">
            ONE NATION — ONE MATERIAL CODE.
          </h1>
          <p className="font-headline text-xl sm:text-2xl text-raw-black mt-2 uppercase tracking-wide">
            AI-POWERED STANDARDIZATION & HARMONIZATION ACROSS CPSEs.
          </p>
        </div>
        {/* Platform Call to Action */}
        <div className="border-t-3 border-raw-black pt-6 mt-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="font-mono text-xs text-[#444444] max-w-xl">
            Automates deduplication, technical attribute normalization, and Common National Material Code (CNMC) mapping across Indian CPSE supply chains.
          </div>
          <RawButton
            variant="primary"
            size="large"
            onClick={handleEnter}
            className="w-full sm:w-auto"
          >
            {session.token ? 'ACCESS WORKSPACE →' : 'ENTER →'}
          </RawButton>
        </div>
      </div>

      {/* INTER-CPSE GEO-RADAR SPOTLIGHT BANNER */}
      <div className="border-3 border-raw-black p-6 bg-raw-sunken mb-12 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="bg-raw-black text-raw-white font-headline text-[11px] px-2 py-0.5 tracking-wider uppercase">
              NEW GEOSPATIAL FEATURE
            </span>
            <span className="font-mono text-xs font-bold text-emerald-700">
              ● 383 UNITS GEOCODED
            </span>
          </div>
          <h2 className="font-headline text-2xl uppercase tracking-tight font-black">
            [CPSE GEO-RADAR] Inter-Enterprise Spares Network
          </h2>
          <p className="font-mono text-xs text-gray-700 mt-1 max-w-2xl">
            Why wait <strong>9 months for foreign import replenishment</strong> when an identical CNMC-standardized valve or turbine spare is sitting idle in a sister CPSE warehouse 40 km away? Explore 383 plants across 15 CPSEs on the interactive MapLibre + Deck.gl network.
          </p>
        </div>
        <button
          onClick={() => onSelectView('georadar')}
          className="font-headline text-sm uppercase px-6 py-3 border-3 border-raw-black bg-raw-white text-raw-black hover:bg-raw-black hover:text-raw-white tracking-widest font-bold whitespace-nowrap shadow-sm transition-none"
        >
          LAUNCH GEO-RADAR 🗺️ →
        </button>
      </div>

      {/* TARGET SECTORS SECTION */}
      <SectorGrid />

    </div>
  );
}
