import { useNavigate } from 'react-router-dom';

const Navbar = () => {
  const navigate = useNavigate();
  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };
  return (
    <nav style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100%',
      height: '60px',
      background: '#222',
      color: '#fff',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 2rem',
      zIndex: 1000,
      boxSizing: 'border-box'
    }}>
      <div style={{ fontWeight: 'bold', fontSize: '1.2rem' }}>nyc monitor</div>
      <button onClick={handleLogout} style={{ background: '#444', color: '#fff', border: 'none', borderRadius: '4px', padding: '0.5rem 1rem', cursor: 'pointer' }}>Log out</button>
    </nav>
  );
};

export default Navbar; 