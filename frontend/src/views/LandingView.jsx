import React from 'react';
import RawButton from '../components/RawButton';
import RawCard from '../components/RawCard';
import SectorGrid from '../components/SectorGrid';
import { useAuth } from '../context/AuthContext';

export default function LandingView({ onSelectView }) {
  const { switchPersona } = useAuth();

  const handleRoleSelect = (roleId) => {
    switchPersona(roleId);
    onSelectView(roleId);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 md:py-12">
      
      {/* Hero Section */}
      <div className="border-5 border-raw-black p-6 md:p-12 bg-raw-white mb-10">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b-3 border-raw-black pb-4 mb-6">
          <div className="font-mono text-xs uppercase tracking-widest bg-raw-black text-raw-white px-3 py-1 font-bold">
            AI PIPELINE ARCHITECTURE
          </div>
          <div className="font-mono text-xs uppercase text-[#444444]">
            LANES 1–8 • EMBEDDING: QWEN3-0.6B • CLASSIFIER: LIGHTGBM
          </div>
        </div>

        {/* Problem Statement Line in Large Archivo Black */}
        <div className="my-6">
          <span className="font-mono text-xs uppercase font-bold text-raw-black block mb-2 tracking-widest">
            PROBLEM STATEMENT:
          </span>
          <h1 className="font-h1 text-raw-black leading-tight tracking-tight">
            DISPARATE MATERIAL NOMENCLATURE AND LOCALIZED CODING ACROSS CPSES CAUSE DUPLICATE PROCUREMENT, FRAGMENTED INVENTORY VISIBILITY, AND INFLATED PUBLIC EXPENDITURE THAT CAN ONLY BE RESOLVED THROUGH AUTOMATED AI-DRIVEN HARMONIZATION LINKED TO A COMMON NATIONAL MATERIAL CATALOG.
          </h1>
        </div>

        {/* Context Strip */}
        <div className="border-t-3 border-raw-black pt-4 mt-6 grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
          <div>
            <strong className="block text-raw-black uppercase font-bold">PURPOSE</strong>
            <span className="text-[#333333]">Cross-enterprise deduplication & semantic unification.</span>
          </div>
          <div>
            <strong className="block text-raw-black uppercase font-bold">TARGET AUDIENCE</strong>
            <span className="text-[#333333]">CPSE Engineers, Technical Reviewers, National Custodians.</span>
          </div>
          <div>
            <strong className="block text-raw-black uppercase font-bold">CONTENT DENSITY</strong>
            <span className="text-[#333333]">High technical specs, engineering tolerances & audit logs.</span>
          </div>
        </div>
      </div>

      {/* Stakeholder Workspaces Navigation */}
      <section className="my-10">
        <div className="border-b-3 border-raw-black pb-3 mb-6">
          <h2 className="font-headline text-2xl md:text-3xl tracking-tight text-raw-black">
            STAKEHOLDER OPERATIONAL WORKSPACES
          </h2>
          <p className="font-body text-sm text-[#444444] mt-1">
            DIRECT ACCESS GATED BY STAKEHOLDER RESPONSIBILITY (RBAC ENABLED)
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* USER Workspace */}
          <RawCard elevated className="flex flex-col justify-between border-raw-black hover:border-raw-black">
            <div>
              <div className="flex items-center justify-between border-b-2 border-raw-black pb-2 mb-4">
                <span className="font-mono text-xs font-bold text-raw-black">ROLE: CPSE_USER</span>
                <span className="font-mono text-[11px] bg-raw-sunken px-2 py-0.5 border-1 border-raw-black font-bold">
                  OPERATIONAL
                </span>
              </div>
              <h3 className="font-headline text-3xl text-raw-black mb-2">USER</h3>
              <p className="font-body text-sm text-[#333333] mb-6 leading-relaxed">
                Ingest native CPSE items, inspect multi-attribute extraction (Lane 3), and execute real-time AI matching candidate generation (Lanes 5–8).
              </p>
            </div>
            <RawButton
              variant="primary"
              size="medium"
              onClick={() => handleRoleSelect('user')}
              className="w-full"
            >
              LAUNCH USER VIEW →
            </RawButton>
          </RawCard>

          {/* REVIEWER Workspace */}
          <RawCard elevated className="flex flex-col justify-between border-raw-black hover:border-raw-black">
            <div>
              <div className="flex items-center justify-between border-b-2 border-raw-black pb-2 mb-4">
                <span className="font-mono text-xs font-bold text-raw-black">ROLE: TECHNICAL_REVIEWER</span>
                <span className="font-mono text-[11px] bg-raw-sunken px-2 py-0.5 border-1 border-raw-black font-bold">
                  GOVERNANCE
                </span>
              </div>
              <h3 className="font-headline text-3xl text-raw-black mb-2">REVIEWER</h3>
              <p className="font-body text-sm text-[#333333] mb-6 leading-relaxed">
                Dual-human verification queue for edge-case candidate pairs. Side-by-side technical conflict detection, attribute override, and audit approvals.
              </p>
            </div>
            <RawButton
              variant="primary"
              size="medium"
              onClick={() => handleRoleSelect('reviewer')}
              className="w-full"
            >
              LAUNCH REVIEWER VIEW →
            </RawButton>
          </RawCard>

          {/* ADMIN Workspace */}
          <RawCard elevated className="flex flex-col justify-between border-raw-black hover:border-raw-black">
            <div>
              <div className="flex items-center justify-between border-b-2 border-raw-black pb-2 mb-4">
                <span className="font-mono text-xs font-bold text-raw-black">ROLE: NATIONAL_ADMIN</span>
                <span className="font-mono text-[11px] bg-raw-sunken px-2 py-0.5 border-1 border-raw-black font-bold">
                  CATALOG CUSTODIAN
                </span>
              </div>
              <h3 className="font-headline text-3xl text-raw-black mb-2">ADMIN</h3>
              <p className="font-body text-sm text-[#333333] mb-6 leading-relaxed">
                Global Common National Material Code (CNMC) oversight. View cross-CPSE mapping linkages, system-wide deduplication rate, and RBAC security status.
              </p>
            </div>
            <RawButton
              variant="primary"
              size="medium"
              onClick={() => handleRoleSelect('admin')}
              className="w-full"
            >
              LAUNCH ADMIN VIEW →
            </RawButton>
          </RawCard>

        </div>
      </section>

      {/* TARGET SECTORS SECTION */}
      <SectorGrid />

    </div>
  );
}

