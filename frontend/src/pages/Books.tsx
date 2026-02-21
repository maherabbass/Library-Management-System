import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '../api';
import { useAuth } from '../AuthContext';
import BookCard from '../components/BookCard';
import Pagination from '../components/Pagination';
import type { Book, BookListParams, BookListResponse, BookStatus } from '../types';

const PAGE_SIZE = 12;

export default function Books() {
  const { canManageBooks } = useAuth();

  const [data, setData] = useState<BookListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [params, setParams] = useState<BookListParams>({ page_size: PAGE_SIZE });

  // search form state
  const [q, setQ] = useState('');
  const [author, setAuthor] = useState('');
  const [tag, setTag] = useState('');
  const [status, setStatus] = useState<BookStatus | ''>('');

  const load = useCallback(
    async (p: number, filters: BookListParams) => {
      setLoading(true);
      setError('');
      try {
        const res = await api.listBooks({ ...filters, page: p, page_size: PAGE_SIZE });
        setData(res);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : 'Failed to load books');
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    load(page, params);
  }, [load, page, params]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const filters: BookListParams = { page_size: PAGE_SIZE };
    if (q) filters.q = q;
    if (author) filters.author = author;
    if (tag) filters.tag = tag;
    if (status) filters.status = status as BookStatus;
    setParams(filters);
    setPage(1);
  }

  function handleReset() {
    setQ(''); setAuthor(''); setTag(''); setStatus('');
    setParams({ page_size: PAGE_SIZE });
    setPage(1);
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this book?')) return;
    try {
      await api.deleteBook(id);
      load(page, params);
    } catch (e) {
      alert(e instanceof ApiError ? e.message : 'Delete failed');
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Books</h1>
        {data && (
          <span style={{ color: 'var(--text-muted)', fontSize: '.875rem' }}>
            {data.total} book{data.total !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Search bar */}
      <form className="search-bar" onSubmit={handleSearch}>
        <div className="form-group">
          <label className="form-label">Search</label>
          <input
            className="form-control"
            placeholder="Title, author, ISBN…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Author</label>
          <input
            className="form-control"
            placeholder="Author name"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Tag</label>
          <input
            className="form-control"
            placeholder="Tag"
            value={tag}
            onChange={(e) => setTag(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Status</label>
          <select
            className="form-control"
            value={status}
            onChange={(e) => setStatus(e.target.value as BookStatus | '')}
          >
            <option value="">All</option>
            <option value="AVAILABLE">Available</option>
            <option value="BORROWED">Borrowed</option>
          </select>
        </div>
        <div style={{ display: 'flex', gap: '.5rem', alignItems: 'flex-end' }}>
          <button type="submit" className="btn btn-primary">Search</button>
          <button type="button" className="btn btn-outline" onClick={handleReset}>Reset</button>
        </div>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-center"><div className="spinner" /></div>
      ) : data && (data.items?.length ?? 0) === 0 ? (
        <div className="empty-state">
          <h3>No books found</h3>
          <p>Try adjusting your search filters.</p>
        </div>
      ) : (
        <>
          <div className="book-grid">
            {data?.items?.map((book: Book) => (
              <BookCard
                key={book.id}
                book={book}
                canManage={canManageBooks}
                onDelete={handleDelete}
              />
            ))}
          </div>
          {data && (
            <Pagination page={data.page} pages={data.pages} onPage={(p) => setPage(p)} />
          )}
        </>
      )}
    </div>
  );
}
