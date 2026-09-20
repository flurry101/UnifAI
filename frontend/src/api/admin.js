// Admin API helpers — role management
import { apiFetch } from './client';

export async function listUsers() {
  return await apiFetch('/api/v1/admin/users');
}

export async function updateUserRole(userId, role) {
  return await apiFetch(`/api/v1/admin/users/${userId}/role`, {
    method: 'PATCH',
    body: { role },
  });
}
