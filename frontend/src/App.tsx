import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { GoogleOAuthProvider, GoogleLogin, useGoogleLogin } from '@react-oauth/google';
import axios from 'axios';

const clientId = "290750569862-gdc3l80ctskurtojh6sgkbs74ursl25l.apps.googleusercontent.com";

function LoginButton() {
  const login = useGoogleLogin({
    onSuccess: async tokenResponse => {
      // tokenResponse contains access_token and id_token
      // For @react-oauth/google v0.11.0, use access_token for API calls, not id_token
      const accessToken = tokenResponse.access_token;
      // Use accessToken in your API requests:
      const res = await axios.post(
        '/api/ask',
        { text: "What is Vertex AI?" },
        { headers: { Authorization: `Bearer ${accessToken}` } }
      );
      console.log(res.data);
    },
    onError: error => console.error(error),
    flow: 'implicit', // or 'auth-code'
  });

  return <button onClick={() => login()}>Sign in with Google</button>;
}

function App() {
  const [count, setCount] = useState(0)

  return (
    <GoogleOAuthProvider clientId={clientId}>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Vite + React</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.tsx</code> and save to test HMR
        </p>
      </div>
      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
      <LoginButton />
    </GoogleOAuthProvider>
  )
}

export default App
