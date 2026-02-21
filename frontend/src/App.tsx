import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './AuthContext';
import Navbar from './components/Navbar';
import Admin from './pages/Admin';
import AISearch from './pages/AISearch';
import AuthCallback from './pages/AuthCallback';
import BookDetail from './pages/BookDetail';
import Books from './pages/Books';
import CreateEditBook from './pages/CreateEditBook';
import LibraryChat from './pages/LibraryChat';
import Loans from './pages/Loans';
import Login from './pages/Login';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div className="loading-center"><div className="spinner" /></div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireLibrarian({ children }: { children: React.ReactNode }) {
  const { canManageBooks, loading } = useAuth();
  if (loading) return <div className="loading-center"><div className="spinner" /></div>;
  if (!canManageBooks) return <Navigate to="/books" replace />;
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { isAdmin, loading } = useAuth();
  if (loading) return <div className="loading-center"><div className="spinner" /></div>;
  if (!isAdmin) return <Navigate to="/books" replace />;
  return <>{children}</>;
}

export default function App() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-center" style={{ minHeight: '100vh' }}>
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="app-layout">
      {isAuthenticated && <Navbar />}
      <main className="main-content">
        <Routes>
          <Route path="/login" element={isAuthenticated ? <Navigate to="/books" replace /> : <Login />} />
          <Route path="/auth/callback" element={<AuthCallback />} />

          <Route path="/books" element={<Books />} />
          <Route path="/ai-search" element={<AISearch />} />

          <Route path="/books/new" element={
            <RequireLibrarian><CreateEditBook mode="create" /></RequireLibrarian>
          } />
          <Route path="/books/:id/edit" element={
            <RequireLibrarian><CreateEditBook mode="edit" /></RequireLibrarian>
          } />
          <Route path="/books/:id" element={<BookDetail />} />

          <Route path="/loans" element={
            <RequireAuth><Loans /></RequireAuth>
          } />
          <Route path="/chat" element={
            <RequireAuth><LibraryChat /></RequireAuth>
          } />
          <Route path="/admin" element={
            <RequireAdmin><Admin /></RequireAdmin>
          } />

          <Route path="/" element={<Navigate to="/books" replace />} />
          <Route path="*" element={<Navigate to="/books" replace />} />
        </Routes>
      </main>
    </div>
  );
}
