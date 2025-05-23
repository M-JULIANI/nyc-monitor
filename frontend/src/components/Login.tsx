import { GoogleLogin } from '@react-oauth/google';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Login = () => {
  const navigate = useNavigate();

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#222'
    }}>
      <h2 style={{ color: '#fff', marginBottom: '2rem' }}>Sign in to continue</h2>
      <GoogleLogin
        onSuccess={credentialResponse => {
          const idToken = credentialResponse.credential;
          localStorage.setItem('idToken', idToken || '');
          axios.post(
            '/api/ask',
            { text: 'What is Vertex AI?' },
            { headers: { Authorization: `Bearer ${idToken}` } }
          ).then(() => {
            navigate('/home');
          });
        }}
        onError={() => {
          alert('Login Failed');
        }}
      />
    </div>
  );
};

export default Login; 