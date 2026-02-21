import { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../AuthContext';

export default function AuthCallback() {
  const [params] = useSearchParams();
  const { login } = useAuth();
  const navigate = useNavigate();
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    const token = params.get('token');
    if (!token) {
      navigate('/login?error=no_token', { replace: true });
      return;
    }
    login(token).then(() => navigate('/books', { replace: true }));
  }, [params, login, navigate]);

  return (
    <div className="loading-center" style={{ minHeight: '80vh' }}>
      <div style={{ textAlign: 'center' }}>
        <div className="spinner" style={{ width: 36, height: 36, margin: '0 auto 1rem' }} />
        <p style={{ color: 'var(--text-muted)' }}>Completing sign-in…</p>
      </div>
    </div>
  );
}
