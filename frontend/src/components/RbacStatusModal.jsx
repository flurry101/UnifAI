import React from 'react';
import RawCard from './RawCard';
import RawButton from './RawButton';
import StatusChip from './StatusChip';

export default function RbacStatusModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  const rbacAuditData = [
    {
      endpoint: "POST /api/v1/reviews/{id}/decision",
      method: "POST",
      roleRequired: "REVIEWER, NATIONAL_ADMIN, ADMIN",
      dbRole: "TECHNICAL_REVIEWER, NATIONAL_ADMIN",
      status: "warning",
      statusLabel: "MISMATCH FOUND",
      finding: "Backend requires 'REVIEWER' string while DB model defines 'TECHNICAL_REVIEWER'. The frontend auth adapter normalizes this to prevent 403 Forbidden errors."
    },
    {
      endpoint: "GET /api/v1/reviews/pending",
      method: "GET",
      roleRequired: "TECHNICAL_REVIEWER / NATIONAL_ADMIN",
      dbRole: "Unprotected",
      status: "warning",
      statusLabel: "OPEN READ",
      finding: "Endpoint responds without Bearer token verification. Frontend gates access to Reviewer & Admin personas."
    },
    {
      endpoint: "POST /api/v1/materials/{id}/matches",
      method: "POST",
      roleRequired: "CPSE_USER",
      dbRole: "Unprotected",
      status: "warning",
      statusLabel: "OPEN INFERENCE",
      finding: "Inference pipeline callable publicly. Recommended future patch: restrict to authenticated CPSE tenants."
    },
    {
      endpoint: "GET /api/v1/materials/{id}",
      method: "GET",
      roleRequired: "CPSE_USER, AUDITOR",
      dbRole: "Unprotected",
      status: "default",
      statusLabel: "CATALOG READ",
      finding: "Unrestricted read access to material_retrieval table by material_id."
    },
    {
      endpoint: "GET /api/v1/cnmc/",
      method: "GET",
      roleRequired: "ALL / NATIONAL_ADMIN",
      dbRole: "Unprotected",
      status: "active",
      statusLabel: "PUBLIC REGISTRY",
      finding: "Global catalog is read-only public by design for inter-CPSE discovery."
    }
  ];

  return (
    <div className="fixed inset-0 z-50 bg-raw-black bg-opacity-75 flex items-center justify-center p-4 overflow-y-auto">
      <div className="max-w-4xl w-full my-8">
        <RawCard elevated className="bg-raw-white">
          <div className="flex items-start justify-between border-b-3 border-raw-black pb-4 mb-4">
            <div>
              <div className="flex items-center gap-3">
                <h2 className="font-headline text-2xl text-raw-black">
                  ROLE-BASED ACCESS CONTROL (RBAC) AUDIT
                </h2>
                <StatusChip label="AUDIT COMPLETE" status="active" />
              </div>
              <p className="font-body text-xs text-[#555555] mt-1">
                SYSTEM INSPECTION REPORT • AUTOMATED ENDPOINT SECURITY & PERMISSIONS SCAN
              </p>
            </div>
            <RawButton variant="secondary" size="small" onClick={onClose}>
              CLOSE [ESC]
            </RawButton>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6 font-mono text-xs">
            <div className="p-3 bg-raw-sunken border-1 border-raw-black">
              <span className="font-bold block text-raw-black">DATABASE ROLES</span>
              <span className="text-[#444444] mt-1 block">
                CPSE_USER, TECHNICAL_REVIEWER, CPSE_ADMIN, NATIONAL_ADMIN, AUDITOR
              </span>
            </div>
            <div className="p-3 bg-raw-sunken border-1 border-raw-black">
              <span className="font-bold block text-raw-black">VISIBLE PERSONAS</span>
              <span className="text-[#444444] mt-1 block">
                USER (CPSE), REVIEWER (Technical), ADMIN (National)
              </span>
            </div>
            <div className="p-3 bg-raw-sunken border-1 border-raw-black">
              <span className="font-bold block text-raw-black">AUTH SCHEME</span>
              <span className="text-[#444444] mt-1 block">
                FastAPI OAuth2 Bearer JWT + Client Gating
              </span>
            </div>
          </div>

          <div className="overflow-x-auto border-3 border-raw-black mb-6">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="bg-raw-black text-raw-white uppercase font-bold tracking-wider">
                  <th className="p-2.5 border-r border-raw-white">Endpoint & Method</th>
                  <th className="p-2.5 border-r border-raw-white">Code Role Check</th>
                  <th className="p-2.5 border-r border-raw-white">Security Status</th>
                  <th className="p-2.5">Analysis & Mitigation</th>
                </tr>
              </thead>
              <tbody className="divide-y-1 divide-raw-black">
                {rbacAuditData.map((row, idx) => (
                  <tr key={idx} className={idx % 2 === 1 ? 'bg-raw-sunken' : 'bg-raw-white'}>
                    <td className="p-2.5 font-bold border-r border-raw-black whitespace-nowrap">
                      <span className="px-1.5 py-0.5 bg-raw-black text-raw-white mr-1.5">{row.method}</span>
                      {row.endpoint}
                    </td>
                    <td className="p-2.5 border-r border-raw-black text-[#333333]">
                      {row.roleRequired}
                    </td>
                    <td className="p-2.5 border-r border-raw-black">
                      <StatusChip label={row.statusLabel} status={row.status} />
                    </td>
                    <td className="p-2.5 font-body text-xs text-[#222222]">
                      {row.finding}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="bg-[#FFF8E7] border-3 border-raw-warning p-4 mb-4">
            <h4 className="font-headline text-sm text-raw-black uppercase mb-1">
              TENANCY ISOLATION SUMMARY
            </h4>
            <p className="font-body text-xs text-[#333333] leading-relaxed">
              While multi-tenant models (<code className="bg-raw-white px-1">cpse_tenant</code>, <code className="bg-raw-white px-1">cpse_id</code>) are present in the database, API query filters do not yet enforce tenant partition isolation on read operations. Frontend architecture cleanly scopes data presentation per selected CPSE context without requiring backend refactoring.
            </p>
          </div>

          <div className="flex justify-end">
            <RawButton variant="primary" size="medium" onClick={onClose}>
              ACKNOWLEDGE & RETURN
            </RawButton>
          </div>
        </RawCard>
      </div>
    </div>
  );
}

