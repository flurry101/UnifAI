import React, { useState, useEffect } from 'react';
import RawCard from '../components/RawCard';
import RawButton from '../components/RawButton';
import RawInput from '../components/RawInput';
import StatusChip from '../components/StatusChip';
import { fetchPendingReviews, submitReviewDecision } from '../api/governance';

export default function ReviewerView() {
  const [proposals, setProposals] = useState([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Form State
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
      if (data.length > 0) {
        setChosenRelation(data[0].predicted_relation || 'EQUIVALENT');
      }
    } catch (err) {
      console.error(err);
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
    const current = proposals[selectedIdx];
    if (!current) return;

    setSubmitting(true);
    setActionSuccess(null);

    try {
      await submitReviewDecision(current.id, {
        action,
        relationship_override: chosenRelation,
      });

      setActionSuccess(`Decision [${action}] recorded for ${current.id}. Updated status: ${action === 'APPROVE' ? 'APPROVED' : 'REJECTED'}.`);
      
      // Update local state queue
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

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      
      {/* Title */}
      <div className="border-b-3 border-raw-black pb-4 mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-headline text-3xl md:text-4xl text-raw-black">
              REVIEWER WORKSPACE
            </h1>
            <span className="font-mono text-xs bg-raw-black text-raw-white px-2.5 py-1 font-bold">
              ROLE: TECHNICAL_REVIEWER
            </span>
          </div>
          <p className="font-body text-sm text-[#444444] mt-1">
            DUAL-HUMAN GOVERNANCE, CONFLICT ARBITRATION & GROUND TRUTH VALIDATION
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-8 border-3 border-raw-black font-mono text-center">
          LOADING PENDING GOVERNANCE QUEUE...
        </div>
      ) : proposals.length === 0 ? (
        <div className="p-8 border-3 border-raw-black font-mono text-center">
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
              
              <div className="space-y-2">
                {proposals.map((item, idx) => {
                  const isSelected = idx === selectedIdx;
                  const isDone = item.governance_state !== 'PENDING';
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleSelectProposal(idx)}
                      className={`w-full text-left p-3 border-2 border-raw-black font-mono text-xs transition-none block ${
                        isSelected
                          ? 'bg-raw-black text-raw-white'
                          : 'bg-raw-white text-raw-black hover:bg-raw-sunken'
                      }`}
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-bold">{item.id}</span>
                        <span className={`text-[10px] px-1 border-1 ${
                          isDone ? 'border-raw-success bg-raw-success text-raw-white' : 'border-raw-warning bg-raw-warning text-raw-black'
                        }`}>
                          {item.governance_state}
                        </span>
                      </div>
                      <div className="text-[11px] truncate opacity-90">
                        {item.query_material_id}
                      </div>
                    </button>
                  );
                })}
              </div>
            </RawCard>
          </div>

          {/* Main Inspection & Decision Panel (3 cols) */}
          <div className="lg:col-span-3">
            {activeProposal && (
              <div className="space-y-6">
                
                {/* Conflict Warning Banner if present */}
                {activeProposal.technical_conflict && (
                  <div className="border-3 border-raw-error bg-[#FFF5F5] p-4 text-raw-black font-mono">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="bg-raw-error text-raw-white font-bold px-2 py-0.5 text-xs">
                        TECHNICAL CONFLICT DETECTED
                      </span>
                      <span className="text-xs font-bold text-raw-error">LANE 6 SAFETY CHECK</span>
                    </div>
                    <p className="text-xs mt-1 text-[#333333]">
                      {activeProposal.conflict_summary || 'Physical attributes diverge between candidate pairs. Mandatory human override required.'}
                    </p>
                  </div>
                )}

                {/* Side by side materials */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <RawCard elevated>
                    <div className="font-headline text-xs text-[#555555] uppercase border-b-2 border-raw-black pb-1 mb-2">
                      MATERIAL A [QUERY]
                    </div>
                    <div className="font-mono text-xs font-bold text-raw-black mb-1">
                      CPSE: {activeProposal.query_cpse || 'IOCL'}
                    </div>
                    <div className="font-mono text-sm font-bold text-raw-black mb-2">
                      CODE: {activeProposal.query_material_id}
                    </div>
                    <div className="p-3 bg-raw-sunken border-1 border-raw-black font-mono text-xs text-[#222222]">
                      {activeProposal.query_description}
                    </div>
                  </RawCard>

                  <RawCard elevated>
                    <div className="font-headline text-xs text-[#555555] uppercase border-b-2 border-raw-black pb-1 mb-2">
                      MATERIAL B [CANDIDATE]
                    </div>
                    <div className="font-mono text-xs font-bold text-raw-black mb-1">
                      CPSE: {activeProposal.candidate_cpse || 'ONGC'}
                    </div>
                    <div className="font-mono text-sm font-bold text-raw-black mb-2">
                      CODE: {activeProposal.candidate_material_id}
                    </div>
                    <div className="p-3 bg-raw-sunken border-1 border-raw-black font-mono text-xs text-[#222222]">
                      {activeProposal.candidate_description}
                    </div>
                  </RawCard>
                </div>

                {/* Side-by-Side Comparison Table */}
                {activeProposal.comparisons && (
                  <RawCard>
                    <h3 className="font-headline text-sm text-raw-black border-b-2 border-raw-black pb-2 mb-3">
                      SIDE-BY-SIDE TECHNICAL ATTRIBUTE AUDIT (LANE 6)
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left font-mono text-xs border-collapse">
                        <thead>
                          <tr className="bg-raw-black text-raw-white uppercase font-bold">
                            <th className="p-2 border-r border-raw-white">Attribute</th>
                            <th className="p-2 border-r border-raw-white">Material A Value</th>
                            <th className="p-2 border-r border-raw-white">Material B Value</th>
                            <th className="p-2">Compatibility</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y-1 divide-raw-black border-b-1 border-raw-black">
                          {activeProposal.comparisons.map((c, idx) => (
                            <tr key={idx} className={c.conflict ? 'bg-[#FFEBEB]' : idx % 2 === 1 ? 'bg-raw-sunken' : 'bg-raw-white'}>
                              <td className="p-2 font-bold border-r border-raw-black">{c.attribute}</td>
                              <td className="p-2 border-r border-raw-black">{c.valA}</td>
                              <td className="p-2 border-r border-raw-black">{c.valB}</td>
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
                )}

                {/* Human Validation & Decision Action Form */}
                <RawCard elevated className="border-raw-black">
                  <div className="border-b-2 border-raw-black pb-2 mb-4 flex items-center justify-between">
                    <h3 className="font-headline text-base text-raw-black">
                      RECORD TECHNICAL ARBITRATION DECISION
                    </h3>
                    <span className="font-mono text-xs bg-raw-sunken px-2 py-0.5 border-1 border-raw-black">
                      AI PROPOSAL: {activeProposal.predicted_relation}
                    </span>
                  </div>

                  {actionSuccess && (
                    <div className="mb-4 p-3 bg-[#EBFEEB] border-2 border-raw-success font-mono text-xs font-bold text-raw-success">
                      ✓ {actionSuccess}
                    </div>
                  )}

                  <div className="space-y-4">
                    {/* Relationship Override Radio Buttons */}
                    <div>
                      <label className="font-headline text-xs text-raw-black uppercase block mb-2">
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
                      <label className="font-headline text-xs text-raw-black uppercase block mb-2">
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
                                  : 'bg-raw-white text-[#444444] hover:bg-raw-sunken'
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
                      <label className="font-headline text-xs text-raw-black uppercase block mb-1">
                        ENGINEERING RATIONALE / JUSTIFICATION NOTES:
                      </label>
                      <textarea
                        rows={2}
                        value={reviewerNotes}
                        onChange={(e) => setReviewerNotes(e.target.value)}
                        placeholder="Explain technical reason for approval or conflict override..."
                        className="w-full bg-raw-sunken text-raw-black font-mono text-xs p-3 border-3 border-raw-black outline-none focus:border-5"
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

