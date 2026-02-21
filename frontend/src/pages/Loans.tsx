import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api';
import { useAuth } from '../AuthContext';
import Pagination from '../components/Pagination';
import type { Loan, LoanListResponse } from '../types';

const PAGE_SIZE = 20;

export default function Loans() {
  const { isAdmin, isLibrarian } = useAuth();
  const [data, setData] = useState<LoanListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [actionId, setActionId] = useState<string | null>(null);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    setError('');
    try {
      setData(await api.listLoans(p, PAGE_SIZE));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to load loans');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(page); }, [load, page]);

  async function handleReturn(loan: Loan) {
    setActionId(loan.id);
    try {
      await api.returnBook(loan.id);
      load(page);
    } catch (e) {
      alert(e instanceof ApiError ? e.message : 'Return failed');
    } finally {
      setActionId(null);
    }
  }

  const pages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">
          {isAdmin || isLibrarian ? 'All Loans' : 'My Loans'}
        </h1>
        {data && (
          <span style={{ color: 'var(--text-muted)', fontSize: '.875rem' }}>
            {data.total} loan{data.total !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-center"><div className="spinner" /></div>
      ) : !data || (data.items?.length ?? 0) === 0 ? (
        <div className="empty-state">
          <h3>No loans</h3>
          <p>
            {isAdmin || isLibrarian
              ? 'No books have been borrowed yet.'
              : <>Browse <Link to="/books" style={{ color: 'var(--primary)' }}>available books</Link> to borrow one.</>}
          </p>
        </div>
      ) : (
        <>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Book ID</th>
                    {(isAdmin || isLibrarian) && <th>User ID</th>}
                    <th>Checked Out</th>
                    <th>Returned</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((loan) => (
                    <tr key={loan.id}>
                      <td>
                        <Link to={`/books/${loan.book_id}`} style={{ color: 'var(--primary)', fontFamily: 'monospace', fontSize: '.8rem' }}>
                          {loan.book_id.slice(0, 8)}…
                        </Link>
                      </td>
                      {(isAdmin || isLibrarian) && (
                        <td style={{ fontFamily: 'monospace', fontSize: '.8rem', color: 'var(--text-muted)' }}>
                          {loan.user_id.slice(0, 8)}…
                        </td>
                      )}
                      <td>{new Date(loan.checked_out_at).toLocaleString()}</td>
                      <td>{loan.returned_at ? new Date(loan.returned_at).toLocaleString() : '—'}</td>
                      <td>
                        <span className={`status-badge status-${loan.status === 'OUT' ? 'borrowed' : 'available'}`}>
                          {loan.status}
                        </span>
                      </td>
                      <td>
                        {loan.status === 'OUT' && (
                          <button
                            className="btn btn-outline btn-sm"
                            disabled={actionId === loan.id}
                            onClick={() => handleReturn(loan)}
                          >
                            {actionId === loan.id ? '…' : 'Return'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <Pagination page={page} pages={pages} onPage={(p) => setPage(p)} />
        </>
      )}
    </div>
  );
}
