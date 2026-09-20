import React, { useState, useEffect } from 'react';
import RawCard from '../components/RawCard';
import RawButton from '../components/RawButton';
import RawInput from '../components/RawInput';
import StatusChip from '../components/StatusChip';
import { fetchPendingReviews, submitReviewDecision } from '../api/governance';
import { useAuth } from '../context/AuthContext';

function getProposalComparisons(proposal) {
  if (!proposal) return [];
  if (proposal.comparisons && proposal.comparisons.length > 0) {
    return proposal.comparisons;
  }

  // Robust fallback attribute comparison generator
  const descA = (proposal.source_description || proposal.query_description || proposal.source_material_id || proposal.query_material_id || '').toUpperCase();
  const descB = (proposal.candidate_description || proposal.candidate_material_id || '').toUpperCase();

  const rows = [];

  // 1. Commodity Type
  const typeA = descA.match(/(VALVE(?:\s*BALL|\s*GATE|\s*GLOBE)?|PIPE|CYLINDER|TUBE|FLANGE|FITTING|GASKET|PUMP)/i)?.[0] || 'GENERAL MATERIAL';
  const typeB = descB.match(/(VALVE(?:\s*BALL|\s*GATE|\s*GLOBE)?|PIPE|CYLINDER|TUBE|FLANGE|FITTING|GASKET|PUMP)/i)?.[0] || 'GENERAL MATERIAL';
  const typeMatch = typeA === typeB;
  rows.push({ attribute: 'COMMODITY TYPE', valA: typeA, valB: typeB, match: typeMatch, conflict: !typeMatch });

  // 2. Standard / Spec
  const stdA = descA.match(/(?:IS:?\s*\d+(?:\s*PART\s*\d+)?|API\s*[0-9A-Z]+|ASME\s*[A-Z0-9]+|ASTM\s*[A-Z0-9]+|SA\s*\d+)/i)?.[0] || 'INDUSTRY SPEC';
  const stdB = descB.match(/(?:IS:?\s*\d+(?:\s*PART\s*\d+)?|API\s*[0-9A-Z]+|ASME\s*[A-Z0-9]+|ASTM\s*[A-Z0-9]+|SA\s*\d+)/i)?.[0] || 'INDUSTRY SPEC';
  const stdMatch = stdA === stdB || (stdA.includes('3196') && stdB.includes('3196')) || (stdA.includes('6D') && stdB.includes('6D')) || (stdA.includes('5L') && stdB.includes('5L'));
  rows.push({ attribute: 'STANDARD / SPEC', valA: stdA, valB: stdB, match: stdMatch, conflict: !stdMatch });

  // 3. Dimension / Size
  const sizeA = descA.match(/(\d+(?:\.\d+)?\s*(?:INCH|IN|MM|DN\s*\d+|KG|OD\s*[\d.]+))/i)?.[0] || 'DN STANDARD';
  const sizeB = descB.match(/(\d+(?:\.\d+)?\s*(?:INCH|IN|MM|DN\s*\d+|KG|OD\s*[\d.]+))/i)?.[0] || 'DN STANDARD';
  const sizeMatch = sizeA.replace(/\s+/g, '') === sizeB.replace(/\s+/g, '');
  rows.push({ attribute: 'SIZE / DIMENSION', valA: sizeA, valB: sizeB, match: sizeMatch, conflict: !sizeMatch });

  // 4. Pressure / Class
  const pressA = descA.match(/(\d+\s*#|\d+\s*BAR|SCH\s*\d+|CLASS\s*\d+|PN\s*\d+)/i)?.[0] || 'ATMOSPHERIC';
  const pressB = descB.match(/(\d+\s*#|\d+\s*BAR|SCH\s*\d+|CLASS\s*\d+|PN\s*\d+)/i)?.[0] || 'ATMOSPHERIC';
  const pressMatch = pressA === pressB;
  rows.push({ attribute: 'PRESSURE / RATING', valA: pressA, valB: pressB, match: pressMatch, conflict: !pressMatch });

  // 5. Material Grade
  const gradeA = descA.match(/(ASTM\s*[A-Z0-9]+|SA\d+|GRADE\s*[A-Z0-9]+|WCB|13CR|A106|X65|T22|CS|SS\d+)/i)?.[0] || 'CARBON STEEL';
  const gradeB = descB.match(/(ASTM\s*[A-Z0-9]+|SA\d+|GRADE\s*[A-Z0-9]+|WCB|13CR|A106|X65|T22|CS|SS\d+)/i)?.[0] || 'CARBON STEEL';
  const gradeMatch = gradeA === gradeB;
  rows.push({ attribute: 'MATERIAL GRADE', valA: gradeA, valB: gradeB, match: gradeMatch, conflict: !gradeMatch });

  return rows;
}

export default function ReviewerView() {
  const { session } = useAuth();
  const canSubmitDecisions = !!session.token;

  const [proposals, setProposals] = useState([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState(null);

  const [chosenRelation, setChosenRelation] = useState('EQUIVALENT');
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [selectedEvidence, setSelectedEvidence] = useState(['DIMENSION_MATCH', 'TECHNICAL_CONFLICT']);

  const evidenceOptions = [
    'EXACT_TECHNICAL_MATCH',
    'SEMANTIC_SIMILARITY',
    'DIMENSION_MATCH',
    'PRESSURE_MATCH',
    'MATERIAL_MATCH',
    'STANDARD_MATCH',
    'TECHNICAL_CONFLICT',
    'UOM_COMPATIBILITY'
  ];

  const relations = ['IDENTICAL', 'EQUIVALENT', 'VARIANT_OF', 'DISTINCT', 'UNDETERMINED'];

  useEffect(() => {
    loadQueue();
  }, []);

  const loadQueue = async () => {
    setLoading(true);
    try {
      const data = await fetchPendingReviews();
      setProposals(data);
      if (data && data.length > 0) {
        setChosenRelation(data[0].predicted_relation || 'EQUIVALENT');
      }
    } catch (err) {
      console.error('Failed to load review queue:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectProposal = (idx) => {
    setSelectedIdx(idx);
    setActionSuccess(null);
    const item = proposals[idx];
    if (item) {
      setChosenRelation(item.predicted_relation || 'EQUIVALENT');
    }
  };

  const handleSubmitDecision = async (action) => {
    if (!canSubmitDecisions) {
      alert('Security Notice: You must be signed in as a CPSE Officer to submit governance decisions.');
      return;
    }

    const current = proposals[selectedIdx];
    if (!current) return;

    setSubmitting(true);
    setActionSuccess(null);

    try {
      await submitReviewDecision(current.id, {
        action,
        relationship_override: chosenRelation,
        reviewerNotes,
        selectedEvidence,
      });

      setActionSuccess(`Decision [${action}] recorded for ${current.id}. Updated status: ${action === 'APPROVE' ? 'APPROVED' : 'REJECTED'}.`);

      setProposals((prev) =>
        prev.map((p, i) =>
          i === selectedIdx
            ? { ...p, governance_state: action === 'APPROVE' ? 'APPROVED' : 'REJECTED' }
            : p
        )
      );
    } catch (err) {
      alert(`Decision error: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const activeProposal = proposals[selectedIdx];
  const sourceCode = activeProposal?.source_material_id || activeProposal?.query_material_id || 'SOURCE_CODE';
  const candidateCode = activeProposal?.candidate_material_id || 'CANDIDATE_CODE';
  const sourceDesc = activeProposal?.source_description || activeProposal?.query_description || 'Query material baseline description.';
  const candidateDesc = activeProposal?.candidate_description || 'Candidate material baseline description.';
  const comparisons = getProposalComparisons(activeProposal);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* Title */}
      <div className="border-b-3 border-raw-black pb-4 mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-headline text-3xl md:text-4xl text-raw-black">
              REVIEW DASHBOARD
            </h1>
            <span className="font-mono text-xs bg-raw-black text-raw-white px-2.5 py-1 font-bold">
              ROLE: CPSE USER
            </span>
          </div>
          <p className="font-body text-sm text-[#444444] mt-1">
            DUAL-HUMAN GOVERNANCE, CONFLICT ARBITRATION &amp; GROUND TRUTH VALIDATION
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-8 border-3 border-raw-black font-mono text-center text-raw-black font-bold">
          LOADING PENDING GOVERNANCE QUEUE...
        </div>
      ) : proposals.length === 0 ? (
        <div className="p-8 border-3 border-raw-black font-mono text-center text-raw-black font-bold">
          NO PENDING REVIEWS. ALL CANDIDATE PAIRS ARE AUDITED.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

          {/* Queue Sidebar (1 col) */}
          <div className="lg:col-span-1">
            <RawCard className="p-4">
              <div className="flex items-center justify-between border-b-2 border-raw-black pb-2 mb-3">
                <span className="font-headline text-xs uppercase">REVIEW QUEUE</span>
                <span className="font-mono text-xs font-bold bg-raw-black text-raw-white px-2 py-0.5">
                  {proposals.length} PAIRS
                </span>
              </div>

              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {proposals.map((prop, idx) => {
                  const isSelected = idx === selectedIdx;
                  const itemSourceId = prop.source_material_id || prop.query_material_id || `ITEM-${idx + 1}`;
                  return (
                    <button
                      key={prop.id}
                      onClick={() => handleSelectProposal(idx)}
                      className={`w-full text-left p-2.5 border-2 border-raw-black transition-none font-mono text-xs ${
                        isSelected
                          ? 'bg-raw-black text-raw-white font-bold'
                          : 'bg-raw-white text-raw-black hover:bg-raw-sunken'
                      }`}
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className="truncate max-w-[120px] font-bold">{itemSourceId}</span>
                        <span className="text-[10px] uppercase font-bold">
                          {prop.predicted_relation || 'UNKNOWN'}
                        </span>
                      </div>
                      <div className="text-[10px] opacity-90 truncate">
                        vs. {prop.candidate_material_id}
                      </div>
                    </button>
                  );
                })}
              </div>
            </RawCard>
          </div>

          {/* Evaluation Workspace (3 cols) */}
          <div className="lg:col-span-3">
            {activeProposal && (
              <div className="space-y-6">

                {/* Candidate Pair Inspection Header */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Material A (Source) */}
                  <RawCard className="p-4 bg-raw-white">
                    <div className="flex items-center justify-between border-b-2 border-raw-black pb-2 mb-2">
                      <span className="font-headline text-xs text-[#555555]">
                        SOURCE CPSE [{activeProposal.source_cpse || 'LOCAL'}]
                      </span>
                      <StatusChip label="QUERY ANCHOR" status="default" />
                    </div>
                    <div className="font-mono text-sm font-bold text-raw-black mb-2">
                      CODE: {sourceCode}
                    </div>
                    <div className="p-3 bg-raw-sunken border-1 border-raw-black font-mono text-xs text-raw-black font-bold">
                      {sourceDesc}
                    </div>
                  </RawCard>

                  {/* Material B (Candidate) */}
                  <RawCard className="p-4 bg-raw-white">
                    <div className="flex items-center justify-between border-b-2 border-raw-black pb-2 mb-2">
                      <span className="font-headline text-xs text-[#555555]">
                        MATCH CPSE [{activeProposal.candidate_cpse || 'EXTERNAL'}]
                      </span>
                      <StatusChip label="CROSS-CPSE MATCH" status="active" />
                    </div>
                    <div className="font-mono text-sm font-bold text-raw-black mb-2">
                      CODE: {candidateCode}
                    </div>
                    <div className="p-3 bg-raw-sunken border-1 border-raw-black font-mono text-xs text-raw-black font-bold">
                      {candidateDesc}
                    </div>
                  </RawCard>
                </div>

                {/* Side-by-Side Comparison Table */}
                <RawCard>
                  <h3 className="font-headline text-sm text-raw-black border-b-2 border-raw-black pb-2 mb-3">
                    SIDE-BY-SIDE TECHNICAL ATTRIBUTE AUDIT (LANE 6)
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left font-mono text-xs border-collapse text-raw-black">
                      <thead>
                        <tr className="bg-raw-black text-raw-white uppercase font-bold">
                          <th className="p-2 border-r border-raw-white">Attribute</th>
                          <th className="p-2 border-r border-raw-white">Material A ({sourceCode})</th>
                          <th className="p-2 border-r border-raw-white">Material B ({candidateCode})</th>
                          <th className="p-2">Compatibility</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y-1 divide-raw-black border-b-1 border-raw-black text-raw-black">
                        {comparisons.map((c, idx) => (
                          <tr key={idx} className={c.conflict ? 'bg-[#FFEBEB] text-raw-black' : idx % 2 === 1 ? 'bg-raw-sunken text-raw-black' : 'bg-raw-white text-raw-black'}>
                            <td className="p-2 font-bold border-r border-raw-black text-raw-black">{c.attribute}</td>
                            <td className="p-2 border-r border-raw-black text-raw-black font-medium">{c.valA}</td>
                            <td className="p-2 border-r border-raw-black text-raw-black font-medium">{c.valB}</td>
                            <td className="p-2 font-bold">
                              {c.match ? (
                                <span className="text-raw-success">MATCH ✓</span>
                              ) : (
                                <span className="text-raw-error">CONFLICT ✗</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </RawCard>

                {/* Human Validation & Decision Action Form */}
                <RawCard elevated className="border-raw-black">
                  <div className="border-b-2 border-raw-black pb-2 mb-4 flex items-center justify-between">
                    <h3 className="font-headline text-base text-raw-black">
                      RECORD TECHNICAL ARBITRATION DECISION
                    </h3>
                    <span className="font-mono text-xs bg-raw-sunken px-2 py-0.5 border-1 border-raw-black text-raw-black font-bold">
                      AI PROPOSAL: {activeProposal.predicted_relation}
                    </span>
                  </div>

                  {actionSuccess && (
                    <div className="mb-4 p-3 bg-[#EBFEEB] border-2 border-raw-success font-mono text-xs font-bold text-raw-success">
                      ✓ {actionSuccess}
                    </div>
                  )}

                  <div className="space-y-4">
                    {/* Relationship Override */}
                    <div>
                      <label className="font-headline text-xs text-raw-black uppercase block mb-2 font-bold">
                        ASSERT FINAL RELATIONSHIP:
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {relations.map((rel) => (
                          <button
                            key={rel}
                            type="button"
                            onClick={() => setChosenRelation(rel)}
                            className={`font-mono text-xs px-3 py-1.5 border-2 border-raw-black uppercase font-bold transition-none ${
                              chosenRelation === rel
                                ? 'bg-raw-black text-raw-white'
                                : 'bg-raw-white text-raw-black hover:bg-raw-sunken'
                            }`}
                          >
                            {rel}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Evidence Checklist */}
                    <div>
                      <label className="font-headline text-xs text-raw-black uppercase block mb-2 font-bold">
                        PRIMARY TECHNICAL EVIDENCE:
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {evidenceOptions.map((ev) => {
                          const isSelected = selectedEvidence.includes(ev);
                          return (
                            <button
                              key={ev}
                              type="button"
                              onClick={() => {
                                if (isSelected) {
                                  setSelectedEvidence(selectedEvidence.filter((e) => e !== ev));
                                } else {
                                  setSelectedEvidence([...selectedEvidence, ev]);
                                }
                              }}
                              className={`font-mono text-[11px] px-2.5 py-1 border-1 border-raw-black uppercase transition-none ${
                                isSelected
                                  ? 'bg-raw-black text-raw-white font-bold'
                                  : 'bg-raw-white text-raw-black hover:bg-raw-sunken'
                              }`}
                            >
                              {isSelected ? `[✓] ${ev}` : `[ ] ${ev}`}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Reviewer Notes */}
                    <div>
                      <label className="font-headline text-xs text-raw-black uppercase block mb-1 font-bold">
                        ENGINEERING RATIONALE / JUSTIFICATION NOTES:
                      </label>
                      <textarea
                        rows={2}
                        value={reviewerNotes}
                        onChange={(e) => setReviewerNotes(e.target.value)}
                        placeholder="Explain technical reason for approval or conflict override..."
                        className="w-full bg-raw-sunken text-raw-black font-mono text-xs p-3 border-3 border-raw-black outline-none focus:border-5 font-medium"
                      />
                    </div>

                    {/* Decision Action Buttons */}
                    <div className="pt-3 border-t-2 border-raw-black flex flex-wrap gap-4 justify-end">
                      <RawButton
                        variant="destructive"
                        size="medium"
                        onClick={() => handleSubmitDecision('REJECT')}
                        disabled={submitting}
                      >
                        REJECT CANDIDATE LINKAGE ✗
                      </RawButton>
                      <RawButton
                        variant="primary"
                        size="medium"
                        onClick={() => handleSubmitDecision('APPROVE')}
                        disabled={submitting}
                      >
                        APPROVE AND COMMIT TO CNMC ✓
                      </RawButton>
                    </div>
                  </div>
                </RawCard>

              </div>
            )}
          </div>

        </div>
      )}

    </div>
  );
}
