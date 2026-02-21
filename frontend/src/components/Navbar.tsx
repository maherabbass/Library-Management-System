import { NavLink } from 'react-router-dom';
import { useAuth } from '../AuthContext';

export default function Navbar() {
  const { user, logout, isAdmin, isLibrarian } = useAuth();

  const roleBadgeClass =
    user?.role === 'ADMIN' ? 'badge badge-admin'
    : user?.role === 'LIBRARIAN' ? 'badge badge-librarian'
    : 'badge badge-member';

  return (
    <nav className="navbar">
      <span className="navbar-brand">📚 LibraryMS</span>

      <div className="navbar-links">
        <NavLink to="/books">Books</NavLink>
        <NavLink to="/ai-search">AI Search</NavLink>
        <NavLink to="/chat">Ask Library</NavLink>
        <NavLink to="/loans">My Loans</NavLink>
        {isLibrarian && <NavLink to="/books/new">+ Add Book</NavLink>}
        {isAdmin && <NavLink to="/admin">Admin</NavLink>}
      </div>

      {user && (
        <div className="navbar-user">
          <span className={roleBadgeClass}>{user.role}</span>
          <span style={{ color: '#94a3b8' }}>{user.name}</span>
          <button
            className="btn btn-ghost btn-sm"
            style={{ color: '#94a3b8' }}
            onClick={logout}
          >
            Logout
          </button>
        </div>
      )}
    </nav>
  );
}
