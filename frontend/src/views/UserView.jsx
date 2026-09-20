import React, { useState, useEffect } from 'react';
import RawCard from '../components/RawCard';
import RawButton from '../components/RawButton';
import RawInput from '../components/RawInput';
import StatusChip from '../components/StatusChip';
import { SAMPLE_MATERIALS, fetchMaterialById, triggerAiMatch } from '../api/materials';
import { useAuth } from '../context/AuthContext';

export default function UserView() {
  const { session } = useAuth();

  const [searchId, setSearchId] = useState(SAMPLE_MATERIALS[0].material_id);
  const [selectedMaterial, setSelectedMaterial] = useState(SAMPLE_MATERIALS[0]);
  const [loadingMaterial, setLoadingMaterial] = useState(false);
  const [matchingLoading, setMatchingLoading] = useState(false);
  const [matchResults, setMatchResults] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    handleLookup(SAMPLE_MATERIALS[0].material_id);
  }, []);

  const handleLookup = async (idToSearch) => {
    const id = idToSearch || searchId;
    if (!id) return;
    setLoadingMaterial(true);
    setErrorMsg(null);
    setMatchResults(null);

    try {
      const data = await fetchMaterialById(id);
      setSelectedMaterial(data);
    } catch (err) {
      setErrorMsg(`Material not found: ${err.message}`);
    } finally {
      setLoadingMaterial(false);
    }
  };

  const handleRunAiMatch = async () => {
    if (!selectedMaterial) return;
    setMatchingLoading(true);
    setErrorMsg(null);

    try {
      const results = await triggerAiMatch(selectedMaterial.material_id || searchId);
      setMatchResults(results);
    } catch (err) {
      setErrorMsg(`AI Matching failed: ${err.message}`);
    } finally {
      setMatchingLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* View Title Bar */}
      <div className="border-b-3 border-raw-black pb-4 mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-headline text-3xl md:text-4xl text-raw-black">
              USER WORKSPACE
            </h1>
            <span className="font-mono text-xs bg-raw-black text-raw-white px-2.5 py-1 font-bold">
              ROLE: CPSE_USER
            </span>
          </div>
          <p className="font-body text-sm text-[#444444] mt-1">
            LOCAL MATERIAL INGESTION, SPECIFICATION INSPECTOR &amp; AI CANDIDATE RETRIEVAL
          </p>
        </div>
      </div>

      {/* Preset Quick Selectors */}
      <div className="mb-6">
        <label className="font-headline text-xs text-raw-black block uppercase tracking-wider mb-2">
          LOAD VERIFIED BENCHMARK MATERIAL (CLICK TO INSPECT):
        </label>
        <div className="flex flex-wrap gap-2">
          {SAMPLE_MATERIALS.map((mat) => (
            <button
              key={mat.material_id}
              onClick={() => {
                setSearchId(mat.material_id);
                handleLookup(mat.material_id);
              }}
              className={`font-mono text-xs px-3 py-1.5 border-2 border-raw-black uppercase font-bold transition-none ${
                selectedMaterial?.material_id === mat.material_id
                  ? 'bg-raw-black text-raw-white'
                  : 'bg-raw-white text-raw-black hover:bg-raw-black hover:text-raw-white'
              }`}
            >
              [{mat.cpse_id}] {mat.original_material_code}
            </button>
          ))}
        </div>
      </div>

      {/* Material Lookup Form */}
      <RawCard className="mb-8">
        <div className="flex flex-col sm:flex-row items-end gap-3">
          <div className="flex-1 w-full">
            <RawInput
              label="QUERY MATERIAL ID / SYSTEM CODE"
              value={searchId}
              onChange={(e) => setSearchId(e.target.value)}
              placeholder="e.g. MAT-IOCL-CYL-14KG, MAT-IOCL-, or 1236/1231"
              helperText="Query by enterprise material code, ID prefix (e.g. MAT-IOCL-), or commodity description."
            />
          </div>
          <RawButton
            variant="secondary"
            size="medium"
            onClick={() => handleLookup(searchId)}
            disabled={loadingMaterial}
            className="w-full sm:w-auto h-[48px]"
          >
            {loadingMaterial ? 'LOOKING UP...' : 'SEARCH MATERIAL'}
          </RawButton>
        </div>

        {errorMsg && (
          <div className="mt-4 p-3 bg-raw-white border-2 border-raw-error text-raw-error font-mono text-xs font-bold">
            [ERROR] {errorMsg}
          </div>
        )}
      </RawCard>

      {/* Active Material Card */}
      {selectedMaterial && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">

          {/* Main Specs (2 cols) */}
          <div className="lg:col-span-2">
            <RawCard elevated className="h-full flex flex-col justify-between">
              <div>
                <div className="flex flex-wrap items-center justify-between border-b-2 border-raw-black pb-3 mb-4 gap-2">
                  <div>
                    <span className="font-mono text-xs font-bold text-raw-black">
                      CPSE ORIGIN: <span className="bg-raw-black text-raw-white px-1.5 py-0.5">{selectedMaterial.cpse_id || 'CENTRAL'}</span>
                    </span>
                    <span className="font-mono text-xs text-[#555555] ml-3">
                      SYSTEM: {selectedMaterial.source_system || 'ERP_DB'}
                    </span>
                  </div>
                  <StatusChip label="INVENTORY ACTIVE" status="active" />
                </div>

                <div className="mb-4">
                  <span className="font-headline text-xs text-[#555555] uppercase block mb-1">
                    ORIGINAL MATERIAL CODE
                  </span>
                  <div className="font-mono text-lg font-bold text-raw-black">
                    {selectedMaterial.original_material_code || selectedMaterial.material_id}
                  </div>
                </div>

                <div className="mb-6">
                  <span className="font-headline text-xs text-[#555555] uppercase block mb-1">
                    NORMALIZED TECHNICAL DESCRIPTION (LANE 2)
                  </span>
                  <div className="p-3 bg-raw-sunken border-2 border-raw-black font-mono text-sm leading-relaxed text-raw-black">
                    {selectedMaterial.normalized_description || 'No normalized description recorded.'}
                  </div>
                </div>

                {selectedMaterial.specifications && (
                  <div className="mb-6">
                    <span className="font-headline text-xs text-[#555555] uppercase block mb-2">
                      EXTRACTED ATTRIBUTES (LANE 3 SYNTACTIC EXTRACTION)
                    </span>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-xs">
                      {Object.entries(selectedMaterial.specifications).map(([key, val]) => (
                        <div key={key} className="p-2 border-1 border-raw-black bg-raw-white">
                          <span className="text-[#666666] block text-[10px] uppercase font-bold">{key}</span>
                          <span className="font-bold text-raw-black">{val}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Match Trigger Button */}
              <div className="pt-4 border-t-2 border-raw-black">
                <RawButton
                  variant="primary"
                  size="large"
                  onClick={handleRunAiMatch}
                  disabled={matchingLoading}
                  className="w-full"
                >
                  {matchingLoading
                    ? 'RUNNING AI PIPELINE (LANES 5→8)...'
                    : '▶ EXECUTE AI HARMONIZATION PIPELINE'}
                </RawButton>
              </div>
            </RawCard>
          </div>

          {/* AI Pipeline Architecture Info (1 col) */}
          <div>
            <RawCard className="h-full bg-raw-sunken flex flex-col justify-between font-mono text-xs">
              <div>
                <h3 className="font-headline text-sm text-raw-black border-b-2 border-raw-black pb-2 mb-3">
                  AI PIPELINE SPECIFICATION
                </h3>
                <ul className="space-y-2 text-[#222222]">
                  <li className="p-2 border-1 border-raw-black bg-raw-white">
                    <strong>LANE 5:</strong> Qwen3-0.6B Embedding (1024-dim) vector cosine retrieval over 21k CPSE corpus.
                  </li>
                  <li className="p-2 border-1 border-raw-black bg-raw-white">
                    <strong>LANE 6:</strong> 42-feature lexical, syntactic &amp; dimensional conflict extractor.
                  </li>
                  <li className="p-2 border-1 border-raw-black bg-raw-white">
                    <strong>LANE 7:</strong> LightGBM multi-class relationship classifier.
                  </li>
                  <li className="p-2 border-1 border-raw-black bg-raw-white">
                    <strong>LANE 8:</strong> Deterministic Safety Decision Engine (gates auto-linking vs human review).
                  </li>
                </ul>
              </div>

              <div className="mt-4 pt-3 border-t-1 border-raw-black text-[11px] text-[#555555]">
                Strict safety guarantee: High-confidence identical matches are proposed; conflicts automatically route to Reviewers.
              </div>
            </RawCard>
          </div>
        </div>
      )}

      {/* AI Matching Results */}
      {matchResults && (
        <section className="mt-10 border-t-3 border-raw-black pt-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="font-headline text-2xl text-raw-black">
                AI MATCH CANDIDATES GENERATED
              </h2>
              <p className="font-body text-xs text-[#555555]">
                {matchResults.length} CANDIDATE(S) DISCOVERED FROM CROSS-CPSE INVENTORIES
              </p>
            </div>
            <span className="font-mono text-xs bg-raw-black text-raw-white px-2 py-1 font-bold">
              MODEL: {matchResults[0]?.model_version || 'Lane8-LGBM'}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {matchResults.map((proposal) => {
              const isIdentical = proposal.predicted_relation === 'IDENTICAL';
              const isEquivalent = proposal.predicted_relation === 'EQUIVALENT';
              const isVariant = proposal.predicted_relation === 'VARIANT_OF';

              let statusVariant = 'default';
              if (isIdentical) statusVariant = 'active';
              else if (isEquivalent) statusVariant = 'active';
              else if (isVariant) statusVariant = 'warning';
              else statusVariant = 'error';

              return (
                <RawCard key={proposal.id} elevated className="flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between border-b-2 border-raw-black pb-2 mb-3">
                      <span className="font-mono text-xs font-bold text-raw-black">
                        CANDIDATE CPSE: {proposal.candidate_cpse || 'CROSS_ENTERPRISE'}
                      </span>
                      <StatusChip
                        label={proposal.predicted_relation}
                        status={statusVariant}
                      />
                    </div>

                    <div className="mb-2">
                      <span className="font-headline text-[11px] text-[#555555] uppercase block">
                        CANDIDATE MATERIAL CODE
                      </span>
                      <div className="font-mono text-sm font-bold text-raw-black">
                        {proposal.candidate_material_id}
                      </div>
                    </div>

                    <div className="p-3 bg-raw-sunken border-1 border-raw-black font-mono text-xs mb-4 text-[#222222]">
                      {proposal.candidate_description || 'Material specification matches query geometry.'}
                    </div>

                    {proposal.lane7_probabilities && (
                      <div className="mb-4">
                        <span className="font-headline text-[10px] text-[#555555] uppercase block mb-1">
                          LANE 7 PROBABILITY VECTOR
                        </span>
                        <div className="grid grid-cols-4 gap-1 font-mono text-[10px] text-center">
                          {Object.entries(proposal.lane7_probabilities).map(([rel, prob]) => (
                            <div key={rel} className="border-1 border-raw-black p-1 bg-raw-white">
                              <div className="text-[9px] text-[#555555] truncate">{rel}</div>
                              <div className="font-bold text-raw-black">
                                {(Number(prob) * 100).toFixed(1)}%
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="p-2 border-1 border-raw-black bg-[#FAFAFA] font-mono text-xs flex items-center justify-between mb-4">
                      <span>DECISION ROUTING:</span>
                      <span className={`font-bold ${proposal.decision_status === 'REVIEW' ? 'text-raw-warning' : 'text-raw-success'}`}>
                        {proposal.decision_status === 'REVIEW' ? 'ROUTED TO REVIEWER' : 'ELIGIBLE FOR AUTO-MAP'}
                      </span>
                    </div>
                  </div>

                  <div className="border-t-2 border-raw-black pt-3 flex justify-between items-center text-xs font-mono">
                    <span className="text-[#555555]">PROPOSAL ID: {proposal.id}</span>
                    <span className="font-bold underline text-raw-black">
                      STATUS: {proposal.governance_state}
                    </span>
                  </div>
                </RawCard>
              );
            })}
          </div>
        </section>
      )}

    </div>
  );
}
