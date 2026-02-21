import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api';
import type { AskResponse, Book } from '../types';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  books?: Book[];
  source?: string;
}

export default function LibraryChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I can answer questions about the books in our library. Ask me anything — I\'ll only use real books in my answers.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question) return;

    setMessages((m) => [...m, { role: 'user', content: question }]);
    setInput('');
    setLoading(true);
    setError('');

    try {
      const res: AskResponse = await api.askLibrary(question);
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: res.answer, books: res.books, source: res.source },
      ]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to get response');
      setMessages((m) => [...m, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  }

  return (
    <div className="chat-container" style={{ maxWidth: 700 }}>
      <div className="page-header">
        <h1 className="page-title">Ask the Library</h1>
      </div>
      <div className="alert alert-info" style={{ marginBottom: '1.25rem' }}>
        This assistant only answers using books in our database — no hallucinated titles.
      </div>

      {/* Chat messages */}
      <div
        style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '1rem',
          minHeight: 300,
          maxHeight: 500,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          marginBottom: '1rem',
        }}
      >
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div
              style={{
                maxWidth: '85%',
                padding: '.6rem .9rem',
                borderRadius: msg.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                background: msg.role === 'user' ? 'var(--primary)' : 'var(--bg)',
                color: msg.role === 'user' ? '#fff' : 'var(--text)',
                fontSize: '.9rem',
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
              }}
            >
              {msg.content}
            </div>

            {msg.books && msg.books.length > 0 && (
              <div className="source-books" style={{ maxWidth: '85%', alignSelf: 'flex-start' }}>
                <h4>📚 Source books ({msg.source})</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '.35rem' }}>
                  {msg.books.map((b) => (
                    <Link
                      key={b.id}
                      to={`/books/${b.id}`}
                      style={{
                        fontSize: '.8rem',
                        color: 'var(--primary)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '.4rem',
                      }}
                    >
                      <span>→</span>
                      <span><strong>{b.title}</strong> by {b.author}</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', gap: '.5rem', alignItems: 'center', color: 'var(--text-muted)', fontSize: '.875rem' }}>
            <div className="spinner" style={{ width: 16, height: 16 }} />
            <span>Thinking…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={handleSend} style={{ display: 'flex', gap: '.75rem' }}>
        <input
          className="form-control"
          placeholder="Ask about books, authors, genres…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          maxLength={500}
          style={{ flex: 1 }}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>

      <p style={{ fontSize: '.75rem', color: 'var(--text-muted)', marginTop: '.5rem', textAlign: 'right' }}>
        {input.length}/500
      </p>
    </div>
  );
}
