import React, { useState, useEffect } from 'react';
import RawCard from '../components/RawCard';
import StatusChip from '../components/StatusChip';
import { apiFetch } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function AuditorView() {
  const { session } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterQuery, setFilterQuery] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    loadAuditLogs();
  }, []);

  const loadAuditLogs = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await apiFetch('/api/v1/reviews/audit-logs');
      setLogs(data || []);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Failed to load audit logs.');
    } finally {
      setLoading(false);
    }
  };

  const filteredLogs = logs.filter((log) => {
    const q = filterQuery.toLowerCase();
    return (
      (log.action || '').toLowerCase().includes(q) ||
      (log.entity_name || '').toLowerCase().includes(q) ||
      (log.actor_id || '').toLowerCase().includes(q) ||
      (log.entity_id || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="border-b-3 border-raw-black pb-4 mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-headline text-3xl md:text-4xl text-raw-black">
              AUDIT &amp; COMPLIANCE DASHBOARD
            </h1>
            <span className="font-mono text-xs bg-raw-black text-raw-white px-2.5 py-1 font-bold">
              ROLE: CPSE USER
            </span>
          </div>
          <p className="font-body text-sm text-[#444444] mt-1 uppercase">
            IMMUTABLE GOVERNANCE AUDIT TRAIL — AI MATCH DECISIONS &amp; CROSS-CPSE HARMONIZATION LOGS
          </p>
        </div>
      </div>

      {/* Tagline / Explainer for Stakeholders */}
      <div className="mb-6 p-4 bg-raw-sunken border-2 border-raw-black">
        <div className="font-mono text-xs text-raw-black leading-relaxed">
          <strong>STAKEHOLDER NOTICE:</strong> Every deduplication proposal, AI confidence rating, and dual-human review action is permanently recorded here for CAG / CVC regulatory transparency.
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 font-mono text-xs">
        <RawCard className="p-4 bg-raw-sunken">
          <span className="text-[#666666] block font-bold uppercase">Total Events</span>
          <span className="font-headline text-2xl text-raw-black mt-1 block">
            {logs.length}
          </span>
        </RawCard>
        <RawCard className="p-4 bg-raw-sunken">
          <span className="text-[#666666] block font-bold uppercase">Approvals</span>
          <span className="font-headline text-2xl text-raw-success mt-1 block">
            {logs.filter((l) => l.action?.includes('APPROVE') || l.action?.includes('HUMAN')).length}
          </span>
        </RawCard>
        <RawCard className="p-4 bg-raw-sunken">
          <span className="text-[#666666] block font-bold uppercase">Overrides / Rejections</span>
          <span className="font-headline text-2xl text-raw-warning mt-1 block">
            {logs.filter((l) => l.action?.includes('REJECT') || l.action?.includes('OVERRIDE')).length}
          </span>
        </RawCard>
        <RawCard className="p-4 bg-raw-sunken">
          <span className="text-[#666666] block font-bold uppercase">System Actor</span>
          <span className="font-headline text-2xl text-raw-black mt-1 block">
            AI-GOV
          </span>
        </RawCard>
      </div>

      {/* Filter and Table */}
      <RawCard elevated className="bg-raw-white p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b-2 border-raw-black pb-3 mb-4 gap-2">
          <h2 className="font-headline text-lg text-raw-black uppercase">
            REGULATORY AUDIT JOURNAL
          </h2>
          <input
            type="text"
            placeholder="FILTER BY ACTOR, ENTITY, ACTION..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            className="font-mono text-xs p-1.5 border-2 border-raw-black bg-raw-sunken outline-none w-72"
          />
        </div>

        {loading && (
          <div className="p-6 font-mono text-xs text-center animate-pulse">
            LOADING AUDIT JOURNAL FROM POSTGRES...
          </div>
        )}

        {error && (
          <div className="p-3 bg-[#FFEBEB] border-2 border-raw-error font-mono text-xs font-bold text-raw-error mb-4">
            [ERROR] {error}
          </div>
        )}

        {!loading && !error && (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="bg-raw-black text-raw-white uppercase font-bold">
                  <th className="p-2 border-r border-raw-white">Timestamp</th>
                  <th className="p-2 border-r border-raw-white">Actor ID</th>
                  <th className="p-2 border-r border-raw-white">Action Taken</th>
                  <th className="p-2 border-r border-raw-white">Entity Name</th>
                  <th className="p-2 border-r border-raw-white">Entity Ref</th>
                  <th className="p-2">State Change</th>
                </tr>
              </thead>
              <tbody className="divide-y-1 divide-raw-black">
                {filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-raw-sunken">
                    <td className="p-2 border-r border-raw-black whitespace-nowrap text-[#555]">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                    </td>
                    <td className="p-2 border-r border-raw-black font-bold">
                      {log.actor_id}
                    </td>
                    <td className="p-2 border-r border-raw-black">
                      <span className="px-1.5 py-0.5 bg-raw-black text-raw-white font-bold text-[10px]">
                        {log.action}
                      </span>
                    </td>
                    <td className="p-2 border-r border-raw-black">
                      {log.entity_name}
                    </td>
                    <td className="p-2 border-r border-raw-black font-mono text-[11px] truncate max-w-xs">
                      {log.entity_id}
                    </td>
                    <td className="p-2 font-mono text-[10px] text-[#444] max-w-xs truncate">
                      {log.new_state ? JSON.stringify(log.new_state) : '—'}
                    </td>
                  </tr>
                ))}
                {filteredLogs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-[#666]">
                      No audit events matching criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </RawCard>
    </div>
  );
}
