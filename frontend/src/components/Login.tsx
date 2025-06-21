import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '@/contexts/AuthContext';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  // Get the redirect path from location state or default to home
  const from = (location.state as any)?.from?.pathname || '/';

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-zinc-900 to-zinc-800 p-4">
      <div className="bg-zinc-800 rounded-xl p-8 md:p-12 max-w-md w-full shadow-xl border border-zinc-700">
        <h2 className="text-2xl font-bold text-white mb-2 text-center">
          Welcome to NYC Monitor
        </h2>
        <p className="text-zinc-300 mb-8 text-center">
          Sign in to access the dashboard
        </p>
        
        <div className="flex justify-center">
          <GoogleLogin
            onSuccess={async (credentialResponse) => {
              const token = credentialResponse.credential;
              if (token) {
                try {
                  await login(token);
                  navigate(from, { replace: true });
                } catch (error) {
                  console.error('Login failed:', error);
                  // You might want to show an error message to the user here
                }
              }
            }}
            onError={() => {
              console.error('Login failed');
              // You might want to show an error message to the user here
            }}
            useOneTap
            theme="filled_black"
            text="signin_with"
            shape="rectangular"
          />
        </div>

        <p className="mt-6 text-sm text-zinc-400 text-center">
          By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </div>
  );
};

export default Login; 