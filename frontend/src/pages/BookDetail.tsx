import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, ApiError } from '../api';
import { useAuth } from '../AuthContext';
import type { Book, Loan } from '../types';

export default function BookDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, canManageBooks } = useAuth();

  const [book, setBook] = useState<Book | null>(null);
  const [loan, setLoan] = useState<Loan | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.getBook(id)
      .then(setBook)
      .catch((e) => setError(e instanceof ApiError ? e.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, [id]);

  // Find the active loan for this book (for authenticated users)
  useEffect(() => {
    if (!isAuthenticated || !id) return;
    api.listLoans(1, 100)
      .then((res) => {
        const active = res.items.find((l) => l.book_id === id && l.status === 'OUT');
        setLoan(active ?? null);
      })
      .catch(() => {}); // silently ignore if no auth
  }, [id, isAuthenticated]);

  async function handleCheckout() {
    if (!id) return;
    setActionLoading(true);
    setError('');
    try {
      const l = await api.checkout(id);
      setLoan(l);
      setBook((b) => b ? { ...b, status: 'BORROWED' } : b);
      setSuccess('Book checked out successfully!');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Checkout failed');
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReturn() {
    if (!loan) return;
    setActionLoading(true);
    setError('');
    try {
      await api.returnBook(loan.id);
      setLoan(null);
      setBook((b) => b ? { ...b, status: 'AVAILABLE' } : b);
      setSuccess('Book returned successfully!');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Return failed');
    } finally {
      setActionLoading(false);
    }
  }

  async function handleDelete() {
    if (!id || !confirm('Delete this book permanently?')) return;
    try {
      await api.deleteBook(id);
      navigate('/books');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Delete failed');
    }
  }

  if (loading) return <div className="loading-center"><div className="spinner" /></div>;
  if (!book) return <div className="alert alert-error">{error || 'Book not found'}</div>;

  return (
    <div style={{ maxWidth: 760 }}>
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/books" style={{ color: 'var(--text-muted)', fontSize: '.875rem' }}>
          ← Back to Books
        </Link>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '.25rem' }}>{book.title}</h1>
            <p style={{ color: 'var(--text-muted)' }}>by {book.author}</p>
          </div>
          <span className={`status-badge status-${book.status.toLowerCase()}`} style={{ fontSize: '.9rem', padding: '.25rem .75rem' }}>
            {book.status}
          </span>
        </div>

        <div className="meta-row" style={{ marginTop: '1.25rem' }}>
          {book.isbn && <span><strong>ISBN:</strong> {book.isbn}</span>}
          {book.published_year && <span><strong>Year:</strong> {book.published_year}</span>}
          <span><strong>Added:</strong> {new Date(book.created_at).toLocaleDateString()}</span>
        </div>

        {book.description && (
          <div style={{ marginTop: '.75rem', lineHeight: 1.7 }}>
            <strong style={{ fontSize: '.875rem' }}>Description</strong>
            <p style={{ marginTop: '.35rem', color: 'var(--text-muted)' }}>{book.description}</p>
          </div>
        )}

        {book.tags && book.tags.length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            <strong style={{ fontSize: '.875rem' }}>Tags</strong>
            <div className="book-card-tags" style={{ marginTop: '.4rem' }}>
              {book.tags.map((t) => <span key={t} className="tag">{t}</span>)}
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '.75rem', flexWrap: 'wrap' }}>
          {isAuthenticated && book.status === 'AVAILABLE' && !loan && (
            <button className="btn btn-success" onClick={handleCheckout} disabled={actionLoading}>
              {actionLoading ? 'Processing…' : 'Checkout'}
            </button>
          )}
          {isAuthenticated && loan && (
            <button className="btn btn-primary" onClick={handleReturn} disabled={actionLoading}>
              {actionLoading ? 'Processing…' : 'Return Book'}
            </button>
          )}
          {!isAuthenticated && book.status === 'AVAILABLE' && (
            <Link to="/login" className="btn btn-primary">Login to Checkout</Link>
          )}
          {canManageBooks && (
            <>
              <Link to={`/books/${book.id}/edit`} className="btn btn-outline">Edit</Link>
              <button className="btn btn-danger" onClick={handleDelete}>Delete</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
