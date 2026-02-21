import { useEffect, useState } from 'react';
import { api, ApiError } from '../api';
import type { User, UserRole } from '../types';

const ROLES: UserRole[] = ['MEMBER', 'LIBRARIAN', 'ADMIN'];

export default function Admin() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [updating, setUpdating] = useState<string | null>(null);

  useEffect(() => {
    api.listUsers()
      .then(setUsers)
      .catch((e) => setError(e instanceof ApiError ? e.message : 'Failed to load users'))
      .finally(() => setLoading(false));
  }, []);

  async function handleRoleChange(user: User, newRole: UserRole) {
    if (newRole === user.role) return;
    setUpdating(user.id);
    setError('');
    setSuccess('');
    try {
      const updated = await api.updateUserRole(user.id, newRole);
      setUsers((u) => u.map((x) => (x.id === updated.id ? updated : x)));
      setSuccess(`${user.name}'s role updated to ${newRole}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Update failed');
    } finally {
      setUpdating(null);
    }
  }

  const badgeClass = (role: UserRole) =>
    role === 'ADMIN' ? 'badge badge-admin'
    : role === 'LIBRARIAN' ? 'badge badge-librarian'
    : 'badge badge-member';

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">User Management</h1>
        <span style={{ color: 'var(--text-muted)', fontSize: '.875rem' }}>
          {users.length} user{users.length !== 1 ? 's' : ''}
        </span>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {loading ? (
        <div className="loading-center"><div className="spinner" /></div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Provider</th>
                  <th>Role</th>
                  <th>Joined</th>
                  <th>Change Role</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td style={{ fontWeight: 500 }}>{user.name}</td>
                    <td style={{ color: 'var(--text-muted)' }}>{user.email}</td>
                    <td>
                      {user.oauth_provider ? (
                        <span style={{ textTransform: 'capitalize' }}>{user.oauth_provider}</span>
                      ) : '—'}
                    </td>
                    <td><span className={badgeClass(user.role)}>{user.role}</span></td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '.875rem' }}>
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td>
                      <select
                        className="form-control"
                        style={{ padding: '.25rem .5rem', width: 'auto', minWidth: 120 }}
                        value={user.role}
                        disabled={updating === user.id}
                        onChange={(e) => handleRoleChange(user, e.target.value as UserRole)}
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>{r}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
