export type UserRole = 'ADMIN' | 'LIBRARIAN' | 'MEMBER';
export type BookStatus = 'AVAILABLE' | 'BORROWED';
export type LoanStatus = 'OUT' | 'RETURNED';
export type AISource = 'openai' | 'fallback';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  oauth_provider: string | null;
  created_at: string;
}

export interface Book {
  id: string;
  title: string;
  author: string;
  isbn: string | null;
  published_year: number | null;
  description: string | null;
  tags: string[] | null;
  status: BookStatus;
  created_at: string;
  updated_at: string;
}

export interface BookListResponse {
  items: Book[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface BookCreate {
  title: string;
  author: string;
  isbn?: string;
  published_year?: number;
  description?: string;
  tags?: string[];
}

export type BookUpdate = Partial<BookCreate> & { status?: BookStatus };

export interface Loan {
  id: string;
  book_id: string;
  user_id: string;
  checked_out_at: string;
  returned_at: string | null;
  status: LoanStatus;
}

export interface LoanListResponse {
  items: Loan[];
  total: number;
}

export interface EnrichRequest {
  title: string;
  author: string;
  description?: string;
}

export interface EnrichResponse {
  summary: string;
  tags: string[];
  keywords: string[];
  source: AISource;
}

export interface AISearchResponse {
  items: Book[];
  total: number;
  source: AISource;
  query: string;
}

export interface AskResponse {
  answer: string;
  books: Book[];
  source: AISource;
}

export interface BookListParams {
  q?: string;
  author?: string;
  tag?: string;
  status?: BookStatus;
  page?: number;
  page_size?: number;
}
