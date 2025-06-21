import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout, user } = useAuth();

  const navLinkClass = (path: string) =>
    `px-4 py-2 rounded text-sm font-medium transition-colors duration-200 ${
      location.pathname === path
        ? 'bg-zinc-800 text-zinc-100'
        : 'text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100'
    }`;

  return (
    <nav className="fixed top-0 left-0 w-full h-14 bg-zinc-950 text-zinc-100 flex items-center justify-between px-8 z-50 border-b border-zinc-800">
      <button
        onClick={() => {
          if (location.pathname !== '/') {
            navigate('/');
          }
        }}
        className="font-bold text-lg tracking-tight hover:text-zinc-300 transition-colors duration-200 cursor-pointer"
      >
        nyc monitor
      </button>
      <div className="flex items-center gap-2">
        <button
          onClick={() => navigate('/')}
          className={navLinkClass('/')}
        >
          Home
        </button>
        {user?.role === 'admin' && (
        <button
          onClick={() => navigate('/admin')}
          className={navLinkClass('/admin')}
        >
          Admin
        </button>)}
        <button
          onClick={() => {
            logout();
            navigate('/login');
          }}
          className="ml-4 px-4 py-2 rounded bg-red-600 text-white font-semibold text-sm hover:bg-red-700 transition-colors duration-200"
        >
          Log out
        </button>
      </div>
    </nav>
  );
};

export default Navbar; 