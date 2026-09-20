import React, { useEffect, useState } from 'react';
import RawCard from './RawCard';
import RawButton from './RawButton';
import { listUsers, updateUserRole } from '../api/admin';

const VALID_ROLES = ['CPSE_USER', 'TECHNICAL_REVIEWER', 'NATIONAL_ADMIN', 'AUDITOR'];

const ROLE_BADGE = {
  CPSE_USER:          { label: 'USER',      color: 'bg-gray-100 text-gray-700' },
  TECHNICAL_REVIEWER: { label: 'REVIEWER',  color: 'bg-blue-100 text-blue-800' },
  NATIONAL_ADMIN:     { label: 'NATL ADMIN',color: 'bg-red-100 text-red-800' },
  AUDITOR:            { label: 'AUDITOR',   color: 'bg-purple-100 text-purple-800' },
};

/**
 * AdminUserManager — visible only to NATIONAL_ADMIN.
 * Lists all users and allows role changes via the admin API.
 */
export default function AdminUserManager({ currentUserRole }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState({}); // { [userId]: true }
  const [feedback, setFeedback] = useState({}); // { [userId]: 'ok' | 'err' }

  useEffect(() => {
    listUsers()
      .then(setUsers)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleRoleChange = async (userId, newRole) => {
    setSaving((s) => ({ ...s, [userId]: true }));
    setFeedback((f) => ({ ...f, [userId]: null }));
    try {
      const updated = await updateUserRole(userId, newRole);
      setUsers((prev) => prev.map((u) => (u.id === userId ? updated : u)));
      setFeedback((f) => ({ ...f, [userId]: 'ok' }));
    } catch (e) {
      setFeedback((f) => ({ ...f, [userId]: e.message || 'Error' }));
    } finally {
      setSaving((s) => ({ ...s, [userId]: false }));
      setTimeout(() => setFeedback((f) => ({ ...f, [userId]: null })), 3000);
    }
  };

  // What roles can the current admin assign?
  const assignableRoles = currentUserRole === 'NATIONAL_ADMIN'
    ? VALID_ROLES
    : VALID_ROLES.filter((r) => !['NATIONAL_ADMIN'].includes(r));

  return (
    <RawCard elevated className="bg-raw-white p-6">
      <div className="border-b-3 border-raw-black pb-3 mb-5">
        <h2 className="font-headline text-lg text-raw-black uppercase tracking-tight">
          USER MANAGEMENT — ROLE CONTROL
        </h2>
        <p className="font-mono text-xs text-[#666] mt-1">
          NATIONAL_ADMIN: You can promote or demote any user.
        </p>
      </div>

      {loading && (
        <p className="font-mono text-xs text-[#888] animate-pulse">LOADING REGISTRY...</p>
      )}

      {error && (
        <div className="p-3 bg-[#FFEBEB] border-2 border-raw-error font-mono text-xs font-bold text-raw-error">
          [ERROR] {error}
        </div>
      )}

      {!loading && !error && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono border-collapse">
            <thead>
              <tr className="border-b-2 border-raw-black">
                <th className="text-left py-2 pr-4 font-bold text-raw-black uppercase">User</th>
                <th className="text-left py-2 pr-4 font-bold text-raw-black uppercase">Email</th>
                <th className="text-left py-2 pr-4 font-bold text-raw-black uppercase">CPSE</th>
                <th className="text-left py-2 pr-4 font-bold text-raw-black uppercase">Current Role</th>
                <th className="text-left py-2 pr-4 font-bold text-raw-black uppercase">Change Role</th>
                <th className="text-left py-2 font-bold text-raw-black uppercase">Status</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const badge = ROLE_BADGE[u.role] || { label: u.role, color: 'bg-gray-100 text-gray-700' };
                return (
                  <tr key={u.id} className="border-b border-gray-200 hover:bg-raw-sunken">
                    <td className="py-2 pr-4 font-bold">{u.username}</td>
                    <td className="py-2 pr-4 text-[#555]">{u.email || '—'}</td>
                    <td className="py-2 pr-4 text-[#555]">{u.cpse_id || '—'}</td>
                    <td className="py-2 pr-4">
                      <span className={`px-2 py-0.5 rounded font-bold text-[10px] uppercase ${badge.color}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="py-2 pr-4">
                      <select
                        value={u.role}
                        disabled={saving[u.id]}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        className="border-2 border-raw-black bg-white px-2 py-1 text-xs font-mono font-bold uppercase cursor-pointer disabled:opacity-50"
                      >
                        {assignableRoles.map((r) => (
                          <option key={r} value={r}>{r}</option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2 text-[10px]">
                      {saving[u.id] && <span className="text-[#888] animate-pulse">SAVING...</span>}
                      {feedback[u.id] === 'ok' && <span className="text-raw-success font-bold">✓ SAVED</span>}
                      {feedback[u.id] && feedback[u.id] !== 'ok' && (
                        <span className="text-raw-error font-bold">{feedback[u.id]}</span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {users.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-[#888]">No users found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </RawCard>
  );
}

