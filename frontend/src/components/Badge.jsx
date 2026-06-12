import React from 'react';

const Badge = ({ variant = 'primary', children }) => {
  const variantClass = `badge-${variant}`;
  return (
    <span className={`badge ${variantClass}`}>
      {children}
    </span>
  );
};

export default Badge;
