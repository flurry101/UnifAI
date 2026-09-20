import React, { useState, useEffect } from 'react';
import RawCard from '../components/RawCard';
import RawButton from '../components/RawButton';
import RawInput from '../components/RawInput';
import StatusChip from '../components/StatusChip';
import { SAMPLE_MATERIALS, searchMaterials, fetchMaterialById, triggerAiMatch } from '../api/materials';
import { useAuth } from '../context/AuthContext';

function extractAttributes(mat) {
  if (!mat) return {};
  if (mat.specifications && Object.keys(mat.specifications).length > 0) {
    return mat.specifications;
  }
  const desc = (mat.normalized_description || mat.original_description || '').toUpperCase();
  const specs = {};

  // Standard
  const stdMatch = desc.match(/(?:IS:?\s*\d+(?:\s*PART\s*\d+)?|API\s*[0-9A-Z]+|ASME\s*[A-Z0-9]+|ASTM\s*[A-Z0-9]+|SA\s*\d+\s*[A-Z0-9]*|DIN\s*\d+)/i);
  if (stdMatch) specs['STANDARD'] = stdMatch[0];

  // Size / Dimension
  const sizeMatch = desc.match(/(\d+(?:\.\d+)?\s*(?:INCH|IN|MM|DN\s*\d+|KG|LITERS|L|OD\s*[\d.]+\s*MM|THK\s*[\d.]+\s*MM))/i);
  if (sizeMatch) specs['DIMENSION / SIZE'] = sizeMatch[0];

  // Pressure / Rating
  const pressMatch = desc.match(/(\d+\s*#|\d+\s*BAR|\d+\s*PSI|SCH\s*\d+|CLASS\s*\d+|PN\s*\d+)/i);
  if (pressMatch) specs['RATING / PRESSURE'] = pressMatch[0];

  // Material Grade
  const gradeMatch = desc.match(/(ASTM\s*[A-Z0-9]+|SA\d+\s*[A-Z0-9]+|GRADE\s*[A-Z0-9]+|WCB|13CR|A106|X65|T22|CS|SS\d+|ALLOY\s*STEEL|CARBON\s*STEEL)/i);
  if (gradeMatch) specs['MATERIAL GRADE'] = gradeMatch[0];

  // Commodity / Type
  const typeMatch = desc.match(/(VALVE(?:\s*BALL|\s*GATE|\s*GLOBE)?|PIPE|CYLINDER|TUBE\s*BOILER|FLANGE|FITTING|GASKET|PUMP)/i);
  if (typeMatch) specs['COMMODITY TYPE'] = typeMatch[0];

  if (Object.keys(specs).length === 0) {
    specs['STATUS'] = 'INGESTED ERP RECORD';
    specs['SOURCE SYSTEM'] = mat.source_system || 'ENTERPRISE ERP';
  }
  return specs;
}

export default function UserView({ onViewChange }) {
  const { session } = useAuth();

  const [availableMaterials, setAvailableMaterials] = useState(SAMPLE_MATERIALS);
  const [searchId, setSearchId] = useState(SAMPLE_MATERIALS[0].material_id);
  const [selectedMaterial, setSelectedMaterial] = useState(SAMPLE_MATERIALS[0]);
  const [loadingMaterial, setLoadingMaterial] = useState(false);
  const [matchingLoading, setMatchingLoading] = useState(false);
  const [matchResults, setMatchResults] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Ingest from Supabase / SQLite on mount
  useEffect(() => {
    async function loadIngested() {
      try {
        const list = await searchMaterials('', 40);
        // Strictly filter out synthetic test mock items (e.g. MOCK-1)
        const cleanIngested = (list || []).filter((item) => {
          const code = (item.original_material_code || item.material_id || '').toUpperCase();
          return !code.startsWith('MOCK');
        });

        // Prioritize verified engineering benchmarks, followed by genuine ingested CPSE catalog records
        const combined = [...SAMPLE_MATERIALS];
        cleanIngested.forEach((item) => {
          if (!combined.some((c) => c.material_id === item.material_id)) {
            combined.push(item);
          }
        });

        setAvailableMaterials(combined);
        // Default to first real benchmark material
        setSelectedMaterial(SAMPLE_MATERIALS[0]);
        setSearchId(SAMPLE_MATERIALS[0].material_id);
      } catch (err) {
        console.warn('Failed to load ingested materials from API, using verified benchmarks:', err);
        setAvailableMaterials(SAMPLE_MATERIALS);
        setSelectedMaterial(SAMPLE_MATERIALS[0]);
        setSearchId(SAMPLE_MATERIALS[0].material_id);
      }
    }
    loadIngested();
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

  const currentSpecs = extractAttributes(selectedMaterial);
  const itemDescription = selectedMaterial?.normalized_description || selectedMaterial?.original_description || 'NO SPECIFICATION TEXT PROVIDED IN RECORD';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* View Title Bar */}
      <div className="border-b-3 border-raw-black pb-4 mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-headline text-3xl md:text-4xl text-raw-black">
              MATERIAL HARMONIZATION DASHBOARD
            </h1>
            <span className="font-mono text-xs bg-raw-black text-raw-white px-2.5 py-1 font-bold">
              ROLE: CPSE USER
            </span>
          </div>
          <p className="font-body text-sm text-[#444444] mt-1">
            LOCAL MATERIAL INGESTION, SPECIFICATION INSPECTOR &amp; AI CANDIDATE RETRIEVAL
          </p>
        </div>
      </div>

      {/* Preset Quick Selectors */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <label className="font-headline text-xs text-raw-black block uppercase tracking-wider">
            INGESTED CPSE MATERIALS &amp; VERIFIED BENCHMARKS ({availableMaterials.length} RECORDS):
          </label>
          <span className="font-mono text-[11px] text-[#666666]">CLICK TO INSPECT RECORD</span>
        </div>
        <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto p-2 border-2 border-raw-black bg-raw-sunken">
          {availableMaterials.map((mat) => {
            const isSelected = selectedMaterial?.material_id === mat.material_id;
            return (
              <button
                key={mat.material_id}
                onClick={() => {
                  setSelectedMaterial(mat);
                  setSearchId(mat.material_id);
                  handleLookup(mat.material_id);
                }}
                className={`font-mono text-xs px-2.5 py-1 border-1 border-raw-black uppercase font-bold transition-none ${
                  isSelected
                    ? 'bg-raw-black text-raw-white'
                    : 'bg-raw-white text-raw-black hover:bg-raw-black hover:text-raw-white'
                }`}
              >
                [{mat.cpse_id || 'LOCAL'}] {mat.original_material_code || mat.material_id}
              </button>
            );
          })}
        </div>
      </div>

      {/* Material Lookup Form */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="md:col-span-2">
          <RawInput
            label="MATERIAL MASTER LOOKUP (CPSE RECORD ID OR CODE)"
            placeholder="e.g. MAT-IOCL-CYL-14KG, MAT-ONGC-VLV-BALL-6IN..."
            value={searchId}
            onChange={(e) => setSearchId(e.target.value)}
          />
        </div>
        <div className="flex items-end">
          <RawButton
            variant="default"
            size="medium"
            onClick={() => handleLookup(searchId)}
            disabled={loadingMaterial}
            className="w-full"
          >
            {loadingMaterial ? 'RETRIEVING RECORD...' : 'INSPECT SPECIFICATION →'}
          </RawButton>
        </div>
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div className="p-4 mb-6 bg-raw-white border-3 border-raw-warning font-mono text-xs text-raw-black">
          [SYSTEM WARNING] {errorMsg}
        </div>
      )}

      {/* Material Inspector Card */}
      {selectedMaterial && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Detailed Specifications (2 cols) */}
          <div className="lg:col-span-2">
            <RawCard elevated className="h-full flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b-2 border-raw-black pb-3 mb-4">
                  <div>
                    <span className="font-mono text-xs bg-raw-black text-raw-white px-2 py-0.5 font-bold mr-2">
                      {selectedMaterial.cpse_id || 'INTERNAL'}
                    </span>
                    <span className="font-mono text-sm font-bold text-raw-black">
                      {selectedMaterial.original_material_code || selectedMaterial.material_id}
                    </span>
                  </div>
                  <StatusChip label="INGESTED LOCAL RECORD" status="active" />
                </div>

                <div className="mb-4">
                  <span className="font-headline text-xs text-[#555555] uppercase block mb-1">
                    ITEM DESCRIPTION (UNSTRUCTURED ERP TEXT)
                  </span>
                  <div className="p-3 bg-raw-sunken border-1 border-raw-black font-mono text-sm text-raw-black font-bold">
                    {itemDescription}
                  </div>
                </div>

                {/* Extracted Attributes */}
                <div className="mb-6">
                  <span className="font-headline text-xs text-[#555555] uppercase block mb-2">
                    EXTRACTED ATTRIBUTES (LANE 3 SYNTACTIC EXTRACTION)
                  </span>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-xs">
                    {Object.entries(currentSpecs).map(([key, val]) => (
                      <div key={key} className="p-2 border-1 border-raw-black bg-raw-white">
                        <span className="text-[#666666] block text-[10px] uppercase font-bold">{key}</span>
                        <span className="font-bold text-raw-black">{val}</span>
                      </div>
                    ))}
                  </div>
                </div>
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
                      {proposal.decision_status === 'REVIEW' ? (
                        <button
                          type="button"
                          onClick={() => onViewChange && onViewChange('reviewer')}
                          className="font-headline text-xs uppercase px-2.5 py-1 bg-raw-black text-raw-white hover:bg-raw-warning hover:text-raw-black font-bold flex items-center gap-1 cursor-pointer transition-none border-1 border-raw-black"
                          title="Open Review Dashboard to evaluate this proposal"
                        >
                          <span>OPEN IN REVIEW DASHBOARD</span>
                          <span>→</span>
                        </button>
                      ) : (
                        <span className="font-bold text-raw-success">
                          ELIGIBLE FOR AUTO-MAP
                        </span>
                      )}
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
