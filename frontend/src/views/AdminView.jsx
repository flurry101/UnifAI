import React, { useState, useEffect } from 'react';
import RawCard from '../components/RawCard';
import RawButton from '../components/RawButton';
import StatusChip from '../components/StatusChip';
import { fetchCnmcCatalog } from '../api/cnmc';
import { useAuth } from '../context/AuthContext';

export default function AdminView() {
  const { session } = useAuth();

  const [catalog, setCatalog] = useState([]);
  const [selectedCnmc, setSelectedCnmc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterQuery, setFilterQuery] = useState('');

  useEffect(() => {
    loadCatalog();
  }, []);

  const loadCatalog = async () => {
    setLoading(true);
    try {
      const data = await fetchCnmcCatalog();
      setCatalog(data);
      if (data.length > 0) {
        setSelectedCnmc(data[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const filteredItems = catalog.filter((item) => {
    const q = filterQuery.toLowerCase();
    return (
      (item.cnmc_code || '').toLowerCase().includes(q) ||
      (item.standardized_description || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* View Header */}
      <div className="border-b-3 border-raw-black pb-4 mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-headline text-3xl md:text-4xl text-raw-black">
              CNMC CATALOG DASHBOARD
            </h1>
            <span className="font-mono text-xs bg-raw-black text-raw-white px-2.5 py-1 font-bold">
              ROLE: CPSE USER
            </span>
          </div>
          <p className="font-body text-sm text-[#444444] mt-1">
            COMMON NATIONAL MATERIAL CATALOG (CNMC) MASTER REGISTRY &amp; CROSS-CPSE LINKAGES
          </p>
        </div>
      </div>

      {/* Catalog Metric Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 font-mono text-xs">
        <RawCard className="p-4 bg-raw-sunken">
          <span className="text-[#666666] block font-bold">TOTAL CNMC CODES</span>
          <span className="font-headline text-2xl text-raw-black mt-1 block">
            {catalog.length}
          </span>
        </RawCard>
        <RawCard className="p-4 bg-raw-sunken">
          <span className="text-[#666666] block font-bold">APPROVED MASTERS</span>
          <span className="font-headline text-2xl text-raw-success mt-1 block">
            {catalog.filter((c) => c.status === 'APPROVED').length}
          </span>
        </RawCard>
        <RawCard className="p-4 bg-raw-sunken">
          <span className="text-[#666666] block font-bold">PROPOSED CODES</span>
          <span className="font-headline text-2xl text-raw-warning mt-1 block">
            {catalog.filter((c) => c.status === 'PROPOSED').length}
          </span>
        </RawCard>
        <RawCard className="p-4 bg-raw-sunken">
          <span className="text-[#666666] block font-bold">MAPPED CPSE ENTITIES</span>
          <span className="font-headline text-2xl text-raw-black mt-1 block">
            {catalog.reduce((acc, c) => acc + (c.linked_cpse_materials?.length || 0), 0)}
          </span>
        </RawCard>
      </div>

      {/* Filter and Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* CNMC Table (2 cols) */}
        <div className="lg:col-span-2">
          <RawCard elevated>
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b-2 border-raw-black pb-3 mb-4 gap-2">
              <h2 className="font-headline text-lg text-raw-black">
                STANDARDIZED CNMC DIRECTORY
              </h2>
              <input
                type="text"
                placeholder="FILTER CODES / SPECS..."
                value={filterQuery}
                onChange={(e) => setFilterQuery(e.target.value)}
                className="font-mono text-xs p-1.5 border-2 border-raw-black bg-raw-sunken outline-none"
              />
            </div>

            {loading ? (
              <div className="p-6 font-mono text-xs text-center">FETCHING CNMC RECORDS...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs border-collapse">
                  <thead>
                    <tr className="bg-raw-black text-raw-white uppercase font-bold">
                      <th className="p-2 border-r border-raw-white">CNMC Code</th>
                      <th className="p-2 border-r border-raw-white">Standard Description</th>
                      <th className="p-2 border-r border-raw-white">Status</th>
                      <th className="p-2">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y-1 divide-raw-black">
                    {filteredItems.map((item) => {
                      const isSelected = selectedCnmc?.id === item.id;
                      return (
                        <tr
                          key={item.id}
                          className={`${
                            isSelected ? 'bg-raw-black text-raw-white font-bold' : 'hover:bg-raw-sunken'
                          }`}
                        >
                          <td className="p-2 border-r border-raw-black whitespace-nowrap">
                            {item.cnmc_code}
                          </td>
                          <td className="p-2 border-r border-raw-black max-w-xs truncate">
                            {item.standardized_description}
                          </td>
                          <td className="p-2 border-r border-raw-black">
                            <StatusChip
                              label={item.status}
                              status={item.status === 'APPROVED' ? 'active' : 'warning'}
                            />
                          </td>
                          <td className="p-2">
                            <button
                              onClick={() => setSelectedCnmc(item)}
                              className={`underline uppercase text-xs ${
                                isSelected ? 'text-raw-white' : 'text-raw-black font-bold'
                              }`}
                            >
                              INSPECT
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </RawCard>
        </div>

        {/* Selected CNMC Lineage & Cross-CPSE Mapping (1 col) */}
        <div>
          {selectedCnmc ? (
            <RawCard elevated className="flex flex-col justify-between h-full">
              <div>
                <div className="flex items-center justify-between border-b-2 border-raw-black pb-2 mb-3">
                  <span className="font-mono text-xs font-bold text-raw-black">
                    CNMC LINEAGE RECORD
                  </span>
                  <StatusChip
                    label={selectedCnmc.status}
                    status={selectedCnmc.status === 'APPROVED' ? 'active' : 'warning'}
                  />
                </div>

                <div className="mb-4">
                  <span className="font-headline text-[11px] text-[#555555] uppercase block">
                    COMMON NATIONAL CODE
                  </span>
                  <div className="font-mono text-lg font-bold text-raw-black">
                    {selectedCnmc.cnmc_code}
                  </div>
                </div>

                <div className="mb-4">
                  <span className="font-headline text-[11px] text-[#555555] uppercase block mb-1">
                    CANONICAL DESCRIPTION
                  </span>
                  <div className="p-3 bg-raw-sunken border-1 border-raw-black font-mono text-xs text-[#222222] leading-relaxed">
                    {selectedCnmc.standardized_description}
                  </div>
                </div>

                {/* Core Attributes */}
                {selectedCnmc.core_attributes && (
                  <div className="mb-4">
                    <span className="font-headline text-[11px] text-[#555555] uppercase block mb-1">
                      CORE SPECIFICATIONS
                    </span>
                    <div className="grid grid-cols-2 gap-1 font-mono text-[11px]">
                      {Object.entries(selectedCnmc.core_attributes).map(([k, v]) => (
                        <div key={k} className="border-1 border-raw-black p-1.5 bg-raw-white">
                          <span className="text-[#666666] block text-[9px] uppercase font-bold">{k}</span>
                          <span className="font-bold text-raw-black">{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Mapped CPSE Codes */}
                <div>
                  <span className="font-headline text-[11px] text-[#555555] uppercase block mb-1">
                    CROSS-CPSE LINKAGES (CONVERGENCE)
                  </span>
                  {selectedCnmc.linked_cpse_materials && selectedCnmc.linked_cpse_materials.length > 0 ? (
                    <div className="space-y-1 font-mono text-xs">
                      {selectedCnmc.linked_cpse_materials.map((m, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 border-1 border-raw-black bg-raw-sunken"
                        >
                          <div>
                            <span className="font-bold bg-raw-black text-raw-white px-1 mr-1.5">
                              {m.cpse}
                            </span>
                            <span>{m.material_code}</span>
                          </div>
                          <span className="text-[10px] uppercase font-bold text-raw-success">
                            [{m.relation}]
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-xs font-mono text-[#666666] p-2 border-1 border-raw-black">
                      No external CPSE materials mapped yet.
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-4 mt-6 border-t-2 border-raw-black text-[11px] font-mono text-[#555555]">
                REGISTRY ID: {selectedCnmc.id}
              </div>
            </RawCard>
          ) : (
            <RawCard className="p-6 font-mono text-xs text-center">
              SELECT A CNMC RECORD TO INSPECT LINEAGE
            </RawCard>
          )}
        </div>

      </div>

    </div>
  );
}
