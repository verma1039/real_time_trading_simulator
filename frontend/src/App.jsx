import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import AuthGuard from './components/AuthGuard';
import AppShell from './layouts/AppShell';

// Pages
import Login from './pages/Login';
import Signup from './pages/Signup';
import VerifyEmail from './pages/VerifyEmail';
import ResetPassword from './pages/ResetPassword';
import Dashboard from './pages/Dashboard';
import Portfolio from './pages/Portfolio';
import Watchlists from './pages/Watchlists';
import Trade from './pages/Trade';
import Orders from './pages/Orders';
import History from './pages/History';
import Settings from './pages/Settings';

import AdminGuard from './components/AdminGuard';

import AdminDashboard from './pages/AdminDashboard';
import AdminUsers from './pages/AdminUsers';
import AdminUserDetails from './pages/AdminUserDetails';
import AdminAuditLogs from './pages/AdminAuditLogs';

// Temporary dummy page generator for incomplete routes
const DummyPage = ({ title }) => (
  <div className="card max-w-4xl mx-auto mt-4">
    <div className="card-header">
      <h1 className="text-xl font-bold">{title}</h1>
    </div>
    <div className="card-body">
      <p className="text-secondary mb-4">This page is under construction.</p>
      <div className="skeleton skeleton-text"></div>
      <div className="skeleton skeleton-text" style={{ width: '80%' }}></div>
      <div className="skeleton skeleton-text" style={{ width: '60%' }}></div>
    </div>
  </div>
);

const App = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/reset-password" element={<ResetPassword />} />

          {/* Protected Routes inside AppShell */}
          <Route element={<AuthGuard><AppShell /></AuthGuard>}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/watchlists" element={<Watchlists />} />
            <Route path="/trade" element={<Trade />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/history" element={<History />} />
            <Route path="/settings" element={<Settings />} />
            
            {/* Admin Routes */}
            <Route element={<AdminGuard />}>
              <Route path="/admin" element={<AdminDashboard />} />
              <Route path="/admin/users" element={<AdminUsers />} />
              <Route path="/admin/users/:userId" element={<AdminUserDetails />} />
              <Route path="/admin/logs" element={<AdminAuditLogs />} />
            </Route>
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
