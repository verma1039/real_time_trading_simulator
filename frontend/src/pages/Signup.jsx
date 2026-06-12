import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Navigate, Link } from 'react-router-dom';
import ErrorState from '../components/ErrorState';
import { client } from '../api/client';
import { CheckCircle } from 'lucide-react';

const Signup = () => {
  const { isAuthenticated } = useAuth();
  const [formData, setFormData] = useState({ name: '', email: '', password: '', confirmPassword: '' });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  if (isAuthenticated) return <Navigate to="/" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (formData.password !== formData.confirmPassword) {
      return setError('Passwords do not match.');
    }
    if (formData.password.length < 8) {
      return setError('Password must be at least 8 characters long.');
    }

    setIsLoading(true);
    try {
      await client.post('/auth/signup', {
        display_name: formData.name,
        email: formData.email,
        password: formData.password
      });
      setIsSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e) => setFormData(p => ({ ...p, [e.target.name]: e.target.value }));

  if (isSuccess) {
    return (
      <div className="d-flex items-center justify-center h-screen bg-base p-4">
        <div className="card w-full max-w-md p-8 text-center shadow-md">
          <div className="d-flex justify-center mb-4"><CheckCircle size={48} className="text-success" /></div>
          <h2 className="text-xl font-bold mb-2">Check your email</h2>
          <p className="text-secondary mb-6">We've sent a verification link to {formData.email}. Please click the link to activate your account.</p>
          <Link to="/login" className="btn btn-primary w-full text-center d-block text-inherit decoration-none">Go to Login</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="d-flex items-center justify-center h-screen bg-base p-4">
      <div className="card w-full max-w-md p-8 shadow-md">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-primary">Antigravity</h1>
          <p className="text-secondary mt-2">Create a new account</p>
        </div>
        {error && <ErrorState message={error} />}
        <form onSubmit={handleSubmit} className="d-flex flex-col gap-4">
          <div>
            <label className="text-sm font-medium mb-1 d-block text-secondary">Full Name</label>
            <input type="text" name="name" className="input w-full" value={formData.name} onChange={handleChange} required />
          </div>
          <div>
            <label className="text-sm font-medium mb-1 d-block text-secondary">Email</label>
            <input type="email" name="email" className="input w-full" value={formData.email} onChange={handleChange} required />
          </div>
          <div>
            <label className="text-sm font-medium mb-1 d-block text-secondary">Password</label>
            <input type="password" name="password" placeholder="At least 8 characters" className="input w-full" value={formData.password} onChange={handleChange} required minLength={8} />
          </div>
          <div>
            <label className="text-sm font-medium mb-1 d-block text-secondary">Confirm Password</label>
            <input type="password" name="confirmPassword" placeholder="Re-enter password" className="input w-full" value={formData.confirmPassword} onChange={handleChange} required />
          </div>
          <button type="submit" className="btn btn-primary w-full mt-2" disabled={isLoading}>
            {isLoading ? 'Creating account...' : 'Sign Up'}
          </button>
        </form>
        <div className="text-center mt-6">
          <p className="text-sm text-secondary">
            Already have an account? <Link to="/login" className="text-primary font-medium hover-underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Signup;
