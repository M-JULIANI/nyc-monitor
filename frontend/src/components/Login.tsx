import { GoogleLogin } from '@react-oauth/google';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Login = () => {
  const navigate = useNavigate();

  return (
    <div style={{
      minHeight: '100vh',
      width: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px'
    }}>
      <div style={{
        background: '#fff',
        borderRadius: '12px',
        padding: '3rem 2.5rem',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        maxWidth: '400px',
        width: '100%',
        textAlign: 'center'
      }}>
        <h2 style={{ 
          color: '#1f2937', 
          marginBottom: '0.5rem',
          fontSize: '1.875rem',
          fontWeight: '700'
        }}>
          Welcome to nyc-monitor
        </h2>
        <p style={{
          color: '#6b7280',
          marginBottom: '2rem',
          fontSize: '1rem'
        }}>
          Sign in to continue to your dashboard
        </p>
        <GoogleLogin
          onSuccess={credentialResponse => {
            const idToken = credentialResponse.credential;
            localStorage.setItem('idToken', idToken || '');
            
            // Navigate immediately on successful login
            navigate('/home');
            
            // Optional: Test API connection in background (non-blocking)
            axios.post(
              '/api/chat',
              { text: 'What is Vertex AI?' },
              { headers: { Authorization: `Bearer ${idToken}` } }
            ).catch(error => {
              console.warn('API connection test failed:', error);
              // Don't block the user experience
            });
          }}
          onError={() => {
            alert('Login Failed');
          }}
        />
      </div>
    </div>
  );
};

export default Login; 