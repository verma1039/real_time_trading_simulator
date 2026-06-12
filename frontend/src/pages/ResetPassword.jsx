import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { client } from '../api/client';
import ErrorState from '../components/ErrorState';
import { CheckCircle } from 'lucide-react';

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);

  // Flow 1: Request Reset Link
  const handleRequestLink = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await client.post('/auth/forgot-password', { email });
      setIsSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to request password reset.');
    } finally {
      setIsLoading(false);
    }
  };

  // Flow 2: Set New Password
  const handleSetPassword = async (e) => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      return setError('Passwords do not match.');
    }
    if (password.length < 8) {
      return setError('Password must be at least 8 characters long.');
    }

    setIsLoading(true);
    try {
      await client.post('/auth/reset-password', { token, new_password: password });
      setIsSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reset password. The link may have expired.');
    } finally {
      setIsLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="d-flex items-center justify-center h-screen bg-base p-4">
        <div className="card w-full max-w-md p-8 text-center shadow-md">
          <div className="d-flex justify-center mb-4"><CheckCircle size={48} className="text-success" /></div>
          <h2 className="text-xl font-bold mb-2">{token ? 'Password Reset' : 'Link Sent'}</h2>
          <p className="text-secondary mb-6">
            {token 
              ? 'Your password has been successfully updated.' 
              : 'If an account exists, a password reset link has been sent to your email.'}
          </p>
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
          <p className="text-secondary mt-2">{token ? 'Set New Password' : 'Reset Password'}</p>
        </div>
        
        {error && <ErrorState message={error} />}
        
        {token ? (
          <form onSubmit={handleSetPassword} className="d-flex flex-col gap-4 mt-4">
            <div>
              <label className="text-sm font-medium mb-1 d-block text-secondary">New Password</label>
              <input type="password" placeholder="At least 8 characters" className="input w-full" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 d-block text-secondary">Confirm Password</label>
              <input type="password" placeholder="Re-enter new password" className="input w-full" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} required />
            </div>
            <button type="submit" className="btn btn-primary w-full mt-2" disabled={isLoading}>
              {isLoading ? 'Resetting...' : 'Update Password'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRequestLink} className="d-flex flex-col gap-4 mt-4">
            <div>
              <label className="text-sm font-medium mb-1 d-block text-secondary">Account Email</label>
              <input type="email" placeholder="you@example.com" className="input w-full" value={email} onChange={e => setEmail(e.target.value)} required />
            </div>
            <button type="submit" className="btn btn-primary w-full mt-2" disabled={isLoading}>
              {isLoading ? 'Sending...' : 'Send Reset Link'}
            </button>
            <div className="text-center mt-4">
              <Link to="/login" className="text-sm text-secondary hover-underline">Back to Login</Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default ResetPassword;
