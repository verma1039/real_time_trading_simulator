import React from 'react';

const PnLDisplay = ({ value, isPercentage = false, prefix = '' }) => {
  const numValue = Number(value);
  if (isNaN(numValue)) return <span>-</span>;
  
  const isPositive = numValue > 0;
  const isNegative = numValue < 0;
  
  let colorClass = 'text-muted';
  if (isPositive) colorClass = 'text-success';
  if (isNegative) colorClass = 'text-danger';
  
  const sign = isPositive ? '+' : '';
  const formattedValue = Math.abs(numValue).toFixed(2);
  const suffix = isPercentage ? '%' : '';

  return (
    <span className={`font-medium ${colorClass}`}>
      {isNegative ? '-' : sign}{prefix}{formattedValue}{suffix}
    </span>
  );
};

export default PnLDisplay;
