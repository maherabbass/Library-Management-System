import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api';
import type { AISearchResponse } from '../types';

export default function AISearch() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(10);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AISearchResponse | null>(null);
  const [error, setError] = useState('');

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      setResult(await api.aiSearch(query.trim(), topK));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 800 }}>
      <div className="page-header">
        <h1 className="page-title">AI Semantic Search</h1>
      </div>
      <div className="alert alert-info" style={{ marginBottom: '1.25rem' }}>
        Search books using natural language. Uses OpenAI embeddings when configured, otherwise falls back to keyword search.
      </div>

      <form className="search-bar" onSubmit={handleSearch}>
        <div className="form-group" style={{ flex: 3 }}>
          <label className="form-label">Natural language query</label>
          <input
            className="form-control"
            placeholder='e.g. "dystopian society with a rebellious hero"'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label className="form-label">Max results</label>
          <select className="form-control" value={topK} onChange={(e) => setTopK(Number(e.target.value))}>
            {[5, 10, 20, 50].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div style={{ alignSelf: 'flex-end' }}>
          <button type="submit" className="btn btn-primary" disabled={loading || !query.trim()}>
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {loading && <div className="loading-center"><div className="spinner" /></div>}

      {result && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: '.875rem' }}>
              {result.total} result{result.total !== 1 ? 's' : ''} for &ldquo;{result.query}&rdquo;
              {' '}
              <span className={`badge ${result.source === 'openai' ? 'badge-librarian' : 'badge-member'}`}>
                {result.source === 'openai' ? '✨ OpenAI' : 'Keyword fallback'}
              </span>
            </p>
          </div>

          {result.items.length === 0 ? (
            <div className="empty-state">
              <h3>No results found</h3>
              <p>Try a different query or browse <Link to="/books" style={{ color: 'var(--primary)' }}>all books</Link>.</p>
            </div>
          ) : (
            <div className="book-grid">
              {result.items.map((book, idx) => (
                <div key={book.id} className="book-card">
                  <div style={{ fontSize: '.75rem', color: 'var(--text-muted)', marginBottom: '.25rem' }}>#{idx + 1}</div>
                  <div className="book-card-title">{book.title}</div>
                  <div className="book-card-author">by {book.author}</div>
                  {book.description && (
                    <p style={{ fontSize: '.8rem', color: 'var(--text-muted)', lineHeight: 1.5, marginTop: '.25rem' }}>
                      {book.description.slice(0, 120)}{book.description.length > 120 ? '…' : ''}
                    </p>
                  )}
                  {book.tags && book.tags.length > 0 && (
                    <div className="book-card-tags">
                      {book.tags.slice(0, 3).map((t) => <span key={t} className="tag">{t}</span>)}
                    </div>
                  )}
                  <div style={{ marginTop: 'auto', paddingTop: '.5rem', display: 'flex', gap: '.5rem', alignItems: 'center' }}>
                    <span className={`status-badge status-${book.status.toLowerCase()}`}>{book.status}</span>
                    <Link to={`/books/${book.id}`} className="btn btn-outline btn-sm" style={{ marginLeft: 'auto' }}>View</Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
