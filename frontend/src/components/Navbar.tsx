import { useNavigate, useLocation } from 'react-router-dom';

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  const navLinkStyle = (path: string) => ({
    background: location.pathname === path ? '#555' : 'transparent',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    padding: '0.5rem 1rem',
    cursor: 'pointer',
    marginRight: '0.5rem',
    transition: 'background-color 0.2s'
  });

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
      
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <button 
          onClick={() => navigate('/home')} 
          style={navLinkStyle('/home')}
        >
          Home
        </button>
        <button 
          onClick={() => navigate('/testing')} 
          style={navLinkStyle('/testing')}
        >
          Testing
        </button>
        <button 
          onClick={handleLogout} 
          style={{ 
            background: '#d73a49', 
            color: '#fff', 
            border: 'none', 
            borderRadius: '4px', 
            padding: '0.5rem 1rem', 
            cursor: 'pointer',
            marginLeft: '1rem'
          }}
        >
          Log out
        </button>
      </div>
    </nav>
  );
};

export default Navbar; 