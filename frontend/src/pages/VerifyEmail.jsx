import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { client } from '../api/client';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import { CheckCircle } from 'lucide-react';

const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [status, setStatus] = useState('loading'); // loading, success, error
  const [errorMsg, setErrorMsg] = useState('');
  const hasCalled = useRef(false);

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setErrorMsg('Invalid or missing verification token.');
      return;
    }

    if (hasCalled.current) return;
    hasCalled.current = true;

    const verify = async () => {
      try {
        await client.post('/auth/verify-email', { token });
        setStatus('success');
      } catch (err) {
        setStatus('error');
        setErrorMsg(err.response?.data?.detail || 'Verification failed. The link may have expired.');
      }
    };

    verify();
  }, [token]);

  if (status === 'loading') {
    return <div className="h-screen bg-base"><LoadingState message="Verifying your email..." /></div>;
  }

  return (
    <div className="d-flex items-center justify-center h-screen bg-base p-4">
      <div className="card w-full max-w-md p-8 text-center shadow-md">
        {status === 'success' ? (
          <>
            <div className="d-flex justify-center mb-4"><CheckCircle size={48} className="text-success" /></div>
            <h2 className="text-xl font-bold mb-2">Email Verified</h2>
            <p className="text-secondary mb-6">Your account has been successfully activated. You can now log in.</p>
            <Link to="/login" className="btn btn-primary w-full d-block text-center text-inherit decoration-none">Go to Login</Link>
          </>
        ) : (
          <>
            <ErrorState title="Verification Failed" message={errorMsg} />
            <div className="mt-6">
              <Link to="/login" className="btn btn-outline w-full d-block text-center text-inherit decoration-none">Return to Login</Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default VerifyEmail;
