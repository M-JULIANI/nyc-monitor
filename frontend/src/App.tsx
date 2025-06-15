import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider } from '@/contexts/AuthContext';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import Login from '@/components/Login';
import Admin from '@/pages/Admin';
import Layout from '@/components/Layout';
import Home from './pages/Home';

// Get client ID from environment
const clientId = "290750569862-gdc3l80ctskurtojh6sgkbs74ursl25l.apps.googleusercontent.com";
const App: React.FC = () => (
  <GoogleOAuthProvider clientId={clientId}>
      <Router>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/admin" element={
            <ProtectedRoute requiredRole="admin">
              <Layout>
                <Admin />
              </Layout>
            </ProtectedRoute>
          } />
          <Route path="/" element={<Layout><Home /></Layout>} />
          {/* Optionally, redirect all unknown routes to / */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  </GoogleOAuthProvider>
);


export default App;
