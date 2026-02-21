import type {
  AISearchResponse,
  AskResponse,
  Book,
  BookCreate,
  BookListParams,
  BookListResponse,
  BookUpdate,
  EnrichRequest,
  EnrichResponse,
  Loan,
  LoanListResponse,
  User,
} from './types';

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) || '';

function getToken(): string | null {
  return localStorage.getItem('access_token');
}

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 204) return undefined as T;

  // Only attempt to parse JSON when the server actually sends it.
  // If we get HTML back (e.g. Vite serving index.html for unproxied routes)
  // we treat it as an error rather than silently passing garbage data through.
  const contentType = res.headers.get('content-type') ?? '';
  const isJson = contentType.includes('application/json');

  if (!isJson) {
    throw new ApiError(`Unexpected response (${res.status}) — is VITE_API_URL or the proxy configured?`, res.status);
  }

  const data = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
  if (!res.ok) {
    throw new ApiError(
      typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail),
      res.status,
    );
  }
  return data as T;
}

export { ApiError };

export const api = {
  // ── Health ────────────────────────────────────────────────────────────────
  health: () => request<{ status: string; version: string }>('/health'),

  // ── Auth ──────────────────────────────────────────────────────────────────
  loginUrl: (provider: 'google' | 'github') => `${API_BASE}/api/v1/auth/login/${provider}`,
  getMe: () => request<User>('/api/v1/auth/me'),

  // ── Books ─────────────────────────────────────────────────────────────────
  listBooks: (params: BookListParams = {}) => {
    const q = new URLSearchParams();
    if (params.q) q.set('q', params.q);
    if (params.author) q.set('author', params.author);
    if (params.tag) q.set('tag', params.tag);
    if (params.status) q.set('status', params.status);
    if (params.page) q.set('page', String(params.page));
    if (params.page_size) q.set('page_size', String(params.page_size));
    return request<BookListResponse>(`/api/v1/books?${q}`);
  },

  getBook: (id: string) => request<Book>(`/api/v1/books/${id}`),

  createBook: (data: BookCreate) =>
    request<Book>('/api/v1/books', { method: 'POST', body: JSON.stringify(data) }),

  updateBook: (id: string, data: BookUpdate) =>
    request<Book>(`/api/v1/books/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  deleteBook: (id: string) =>
    request<void>(`/api/v1/books/${id}`, { method: 'DELETE' }),

  // ── AI ────────────────────────────────────────────────────────────────────
  enrichBook: (data: EnrichRequest) =>
    request<EnrichResponse>('/api/v1/books/enrich', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  aiSearch: (q: string, top_k = 10) =>
    request<AISearchResponse>(
      `/api/v1/books/ai-search?q=${encodeURIComponent(q)}&top_k=${top_k}`,
    ),

  askLibrary: (question: string) =>
    request<AskResponse>('/api/v1/books/ask', {
      method: 'POST',
      body: JSON.stringify({ question }),
    }),

  // ── Loans ─────────────────────────────────────────────────────────────────
  listLoans: (page = 1, page_size = 20) =>
    request<LoanListResponse>(`/api/v1/loans?page=${page}&page_size=${page_size}`),

  checkout: (book_id: string) =>
    request<Loan>('/api/v1/loans/checkout', {
      method: 'POST',
      body: JSON.stringify({ book_id }),
    }),

  returnBook: (loan_id: string) =>
    request<Loan>('/api/v1/loans/return', {
      method: 'POST',
      body: JSON.stringify({ loan_id }),
    }),

  // ── Admin ─────────────────────────────────────────────────────────────────
  listUsers: () => request<User[]>('/api/v1/admin/users'),

  updateUserRole: (user_id: string, role: string) =>
    request<User>(`/api/v1/admin/users/${user_id}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    }),
};
