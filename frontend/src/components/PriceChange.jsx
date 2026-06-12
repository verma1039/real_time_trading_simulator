import React from 'react';
import PnLDisplay from './PnLDisplay';

const PriceChange = ({ price, previousClose, currencyPrefix = '₹' }) => {
  if (!price || !previousClose) return null;
  
  const diff = price - previousClose;
  const pct = (diff / previousClose) * 100;

  return (
    <div className="d-flex items-center gap-2 text-sm">
      <PnLDisplay value={diff} prefix={currencyPrefix} />
      <span className="text-muted">(</span>
      <PnLDisplay value={pct} isPercentage={true} />
      <span className="text-muted">)</span>
    </div>
  );
};

export default PriceChange;
