import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Navigate, useNavigate, Link } from 'react-router-dom';
import ErrorState from '../components/ErrorState';

const Login = () => {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="d-flex items-center justify-center h-screen bg-base">
      <div className="card w-full max-w-md p-8 shadow-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-primary">Antigravity</h1>
          <p className="text-secondary mt-2">Sign in to your account</p>
        </div>
        {error && <ErrorState title="Authentication Failed" message={error} />}
        <form onSubmit={handleSubmit} className="d-flex flex-col gap-5">
          <div>
            <label className="text-sm font-medium mb-1 d-block text-secondary">Email</label>
            <input 
              type="email" 
              className="input w-full" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              required 
            />
          </div>
          <div>
            <label className="text-sm font-medium mb-1 d-block text-secondary">Password</label>
            <input 
              type="password" 
              className="input w-full" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
            />
          </div>
          <button type="submit" className="btn btn-primary w-full mt-2" disabled={isLoading}>
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <div className="text-center mt-6">
          <p className="text-sm text-secondary">
            Don't have an account? <Link to="/signup" className="text-primary font-medium hover-underline">Sign up</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
