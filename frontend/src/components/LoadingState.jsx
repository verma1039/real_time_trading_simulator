import React from 'react';
import { Loader2 } from 'lucide-react';

const LoadingState = ({ message = 'Loading...' }) => (
  <div className="d-flex flex-col items-center justify-center p-8 gap-4 h-full w-full">
    <Loader2 size={32} className="text-primary" style={{ animation: 'spin 1s linear infinite' }} />
    <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
    <p className="text-sm font-medium text-secondary">{message}</p>
  </div>
);

export default LoadingState;
