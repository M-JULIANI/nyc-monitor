import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import axios from 'axios';

const clientId = "290750569862-gdc3l80ctskurtojh6sgkbs74ursl25l.apps.googleusercontent.com";

function LoginButton() {
  return (
    <GoogleLogin
      onSuccess={credentialResponse => {
        const idToken = credentialResponse.credential;
        // Now send this as the Bearer token
        axios.post(
          '/api/ask',
          { text: "What is Vertex AI?" },
          { headers: { Authorization: `Bearer ${idToken}` } }
        ).then(res => {
          console.log(res.data);
        });
      }}
      onError={() => {
        console.log('Login Failed');
      }}
    />
  );
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
