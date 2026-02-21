import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, ApiError } from '../api';
import type { BookCreate, EnrichResponse } from '../types';

interface Props {
  mode: 'create' | 'edit';
}

const empty: BookCreate = { title: '', author: '', isbn: '', published_year: undefined, description: '', tags: [] };

export default function CreateEditBook({ mode }: Props) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [form, setForm] = useState<BookCreate>(empty);
  const [tagsInput, setTagsInput] = useState('');
  const [loading, setLoading] = useState(mode === 'edit');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [enriching, setEnriching] = useState(false);
  const [enrichResult, setEnrichResult] = useState<EnrichResponse | null>(null);

  useEffect(() => {
    if (mode === 'edit' && id) {
      api.getBook(id)
        .then((b) => {
          setForm({
            title: b.title,
            author: b.author,
            isbn: b.isbn ?? '',
            published_year: b.published_year ?? undefined,
            description: b.description ?? '',
            tags: b.tags ?? [],
          });
          setTagsInput((b.tags ?? []).join(', '));
        })
        .catch((e) => setError(e instanceof ApiError ? e.message : 'Failed to load'))
        .finally(() => setLoading(false));
    }
  }, [mode, id]);

  function set(field: keyof BookCreate, value: string | number | undefined) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleEnrich() {
    if (!form.title || !form.author) {
      setError('Title and author are required for AI enrichment.');
      return;
    }
    setEnriching(true);
    setError('');
    try {
      const res = await api.enrichBook({ title: form.title, author: form.author, description: form.description });
      setEnrichResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Enrichment failed');
    } finally {
      setEnriching(false);
    }
  }

  function applyEnrich() {
    if (!enrichResult) return;
    setForm((f) => ({ ...f, description: enrichResult.summary, tags: enrichResult.tags }));
    setTagsInput(enrichResult.tags.join(', '));
    setEnrichResult(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError('');
    const tags = tagsInput.split(',').map((t) => t.trim()).filter(Boolean);
    const payload: BookCreate = { ...form, tags: tags.length ? tags : undefined };
    // Clean optional empty strings
    if (!payload.isbn) delete payload.isbn;
    if (!payload.description) delete payload.description;
    if (!payload.published_year) delete payload.published_year;

    try {
      if (mode === 'create') {
        const book = await api.createBook(payload);
        navigate(`/books/${book.id}`);
      } else if (id) {
        await api.updateBook(id, payload);
        navigate(`/books/${id}`);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Save failed');
      setSaving(false);
    }
  }

  if (loading) return <div className="loading-center"><div className="spinner" /></div>;

  return (
    <div style={{ maxWidth: 680 }}>
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/books" style={{ color: 'var(--text-muted)', fontSize: '.875rem' }}>
          ← Back to Books
        </Link>
      </div>

      <div className="page-header">
        <h1 className="page-title">{mode === 'create' ? 'Add Book' : 'Edit Book'}</h1>
        <button
          type="button"
          className="btn btn-outline"
          onClick={handleEnrich}
          disabled={enriching || !form.title || !form.author}
          title="Generate AI summary, tags and keywords from title/author"
        >
          {enriching ? '✨ Generating…' : '✨ AI Enrich'}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {enrichResult && (
        <div className="ai-panel">
          <h4>✨ AI-generated metadata ({enrichResult.source})</h4>
          <p style={{ fontSize: '.875rem', marginBottom: '.5rem' }}>
            <strong>Summary:</strong> {enrichResult.summary}
          </p>
          <p style={{ fontSize: '.875rem', marginBottom: '.5rem' }}>
            <strong>Tags:</strong> {enrichResult.tags.join(', ')}
          </p>
          <p style={{ fontSize: '.875rem', marginBottom: '.75rem' }}>
            <strong>Keywords:</strong> {enrichResult.keywords.join(', ')}
          </p>
          <div style={{ display: 'flex', gap: '.5rem' }}>
            <button className="btn btn-primary btn-sm" onClick={applyEnrich}>Apply to form</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setEnrichResult(null)}>Dismiss</button>
          </div>
        </div>
      )}

      <form className="card" style={{ marginTop: '1.25rem' }} onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label">Title *</label>
            <input className="form-control" required value={form.title} onChange={(e) => set('title', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Author *</label>
            <input className="form-control" required value={form.author} onChange={(e) => set('author', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">ISBN</label>
            <input className="form-control" value={form.isbn ?? ''} onChange={(e) => set('isbn', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Published Year</label>
            <input
              className="form-control"
              type="number"
              min="1000"
              max="2100"
              value={form.published_year ?? ''}
              onChange={(e) => set('published_year', e.target.value ? parseInt(e.target.value) : undefined)}
            />
          </div>
        </div>

        <div className="form-group" style={{ marginTop: '1rem' }}>
          <label className="form-label">Description</label>
          <textarea className="form-control" value={form.description ?? ''} onChange={(e) => set('description', e.target.value)} />
        </div>

        <div className="form-group" style={{ marginTop: '1rem' }}>
          <label className="form-label">Tags (comma-separated)</label>
          <input
            className="form-control"
            placeholder="fiction, mystery, classic"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
          />
        </div>

        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '.75rem' }}>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving…' : mode === 'create' ? 'Create Book' : 'Save Changes'}
          </button>
          <Link to="/books" className="btn btn-outline">Cancel</Link>
        </div>
      </form>
    </div>
  );
}
