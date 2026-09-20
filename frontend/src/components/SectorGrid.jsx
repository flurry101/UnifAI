import React from 'react';
import RawCard from './RawCard';

const SECTORS = [
  {
    code: 'SEC-01',
    name: 'OIL & GAS',
    leadCpse: 'ONGC, IOCL, GAIL, BPCL, HPCL, CPCL',
  },
  {
    code: 'SEC-02',
    name: 'POWER',
    leadCpse: 'NTPC, POWERGRID, NHPC',
  },
  {
    code: 'SEC-03',
    name: 'STEEL',
    leadCpse: 'SAIL, RINL',
  },
  {
    code: 'SEC-04',
    name: 'MINING',
    leadCpse: 'COAL INDIA, NMDC, MOIL',
  },
  {
    code: 'SEC-05',
    name: 'HEAVY ENGINEERING',
    leadCpse: 'BHEL, BEML, HEC',
  },
];

export default function SectorGrid() {
  return (
    <section className="my-10">
      <div className="border-b-3 border-raw-black pb-3 mb-6 flex flex-col md:flex-row md:items-end justify-between gap-2">
        <div>
          <h2 className="font-headline text-2xl md:text-3xl tracking-tight text-raw-black">
            TARGET SECTORS
          </h2>
          <p className="font-body text-sm text-[#444444] mt-1">
            PRIORITY CENTRAL PUBLIC SECTOR INDUSTRIAL DOMAINS UNDER AI HARMONIZATION
          </p>
        </div>
        <div className="font-mono text-xs uppercase bg-raw-sunken px-3 py-1 border-1 border-raw-black">
          5 ACTIVE TRACKS • NATIONWIDE CONVERGENCE
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {SECTORS.map((sector) => (
          <RawCard key={sector.code} className="hover:border-5 transition-none flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b-1 border-raw-black pb-2 mb-3">
                <span className="font-mono text-xs font-bold text-raw-black">{sector.code}</span>
                <span className="font-mono text-[11px] bg-raw-sunken px-2 py-0.5 border-1 border-raw-black font-semibold">
                  MANDATED
                </span>
              </div>
              <h3 className="font-headline text-lg md:text-xl text-raw-black mb-3">
                {sector.name}
              </h3>
            </div>
            <div className="pt-3 border-t-1 border-raw-black text-[11px] font-body text-[#555555]">
              <strong className="text-raw-black">KEY CPSES:</strong> {sector.leadCpse}
            </div>
          </RawCard>
        ))}
      </div>
    </section>
  );
}
