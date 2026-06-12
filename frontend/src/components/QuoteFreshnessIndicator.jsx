import React from 'react';

const QuoteFreshnessIndicator = ({ status }) => {
  // status: 'fresh', 'delayed', 'stale'
  let color = 'bg-success';
  let label = 'Live';
  
  if (status === 'delayed') {
    color = 'bg-warning';
    label = 'Delayed';
  } else if (status === 'stale') {
    color = 'bg-danger';
    label = 'Market Closed';
  }

  return (
    <div className="d-flex items-center gap-1">
      <div className={`${color} rounded-full`} style={{ width: '8px', height: '8px' }}></div>
      <span className="text-xs text-muted">{label}</span>
    </div>
  );
};

export default QuoteFreshnessIndicator;
