import { Link } from 'react-router-dom';
import type { Book } from '../types';

interface Props {
  book: Book;
  onDelete?: (id: string) => void;
  canManage?: boolean;
}

export default function BookCard({ book, onDelete, canManage }: Props) {
  return (
    <div className="book-card">
      <div className="book-card-title">{book.title}</div>
      <div className="book-card-author">by {book.author}</div>

      {book.tags && book.tags.length > 0 && (
        <div className="book-card-tags">
          {book.tags.slice(0, 4).map((t) => (
            <span key={t} className="tag">{t}</span>
          ))}
        </div>
      )}

      <div style={{ marginTop: 'auto', paddingTop: '.5rem' }}>
        <span className={`status-badge status-${book.status.toLowerCase()}`}>
          {book.status}
        </span>
      </div>

      <div className="book-card-actions">
        <Link to={`/books/${book.id}`} className="btn btn-outline btn-sm">
          View
        </Link>
        {canManage && (
          <>
            <Link to={`/books/${book.id}/edit`} className="btn btn-ghost btn-sm">
              Edit
            </Link>
            <button
              className="btn btn-danger btn-sm"
              onClick={() => onDelete?.(book.id)}
            >
              Delete
            </button>
          </>
        )}
      </div>
    </div>
  );
}
