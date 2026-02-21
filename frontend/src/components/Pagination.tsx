interface Props {
  page: number;
  pages: number;
  onPage: (p: number) => void;
}

export default function Pagination({ page, pages, onPage }: Props) {
  if (pages <= 1) return null;

  const items: (number | '...')[] = [];
  if (pages <= 7) {
    for (let i = 1; i <= pages; i++) items.push(i);
  } else {
    items.push(1);
    if (page > 3) items.push('...');
    for (let i = Math.max(2, page - 1); i <= Math.min(pages - 1, page + 1); i++) items.push(i);
    if (page < pages - 2) items.push('...');
    items.push(pages);
  }

  return (
    <div className="pagination">
      <button onClick={() => onPage(page - 1)} disabled={page === 1}>← Prev</button>
      {items.map((item, i) =>
        item === '...' ? (
          <span key={`ellipsis-${i}`} style={{ padding: '0 .25rem', color: 'var(--text-muted)' }}>…</span>
        ) : (
          <button
            key={item}
            onClick={() => onPage(item as number)}
            className={page === item ? 'active' : ''}
          >
            {item}
          </button>
        ),
      )}
      <button onClick={() => onPage(page + 1)} disabled={page === pages}>Next →</button>
    </div>
  );
}
