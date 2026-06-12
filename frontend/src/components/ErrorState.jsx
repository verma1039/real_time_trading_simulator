import React from 'react';
import { AlertCircle } from 'lucide-react';

const ErrorState = ({ title = 'Something went wrong', message, retryAction }) => (
  <div className="d-flex flex-col items-center justify-center p-8 text-center bg-danger-bg rounded-md my-4 border border-light">
    <AlertCircle size={40} className="text-danger mb-4" />
    <h3 className="text-lg font-semibold text-danger mb-2">{title}</h3>
    <p className="text-danger-text text-sm mb-4">{message}</p>
    {retryAction && (
      <button onClick={retryAction} className="btn btn-outline text-danger-text">
        Try Again
      </button>
    )}
  </div>
);

export default ErrorState;
