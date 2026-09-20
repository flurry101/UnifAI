// Admin API helpers — role management
import { apiFetch } from './client';

export async function listUsers() {
  const resp = await apiFetch('/api/v1/admin/users');
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch users.');
  }
  return resp.json();
}

export async function updateUserRole(userId, role) {
  const resp = await apiFetch(`/api/v1/admin/users/${userId}/role`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update role.');
  }
  return resp.json();
}

