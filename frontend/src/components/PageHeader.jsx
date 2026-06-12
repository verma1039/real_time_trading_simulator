import React from 'react';

const PageHeader = ({ title, subtitle, action }) => (
  <div className="d-flex flex-col md-d-flex md-flex-row md-items-center justify-between gap-4 mb-6">
    <div>
      <h1 className="text-2xl font-bold text-primary">{title}</h1>
      {subtitle && <p className="text-sm text-secondary mt-1">{subtitle}</p>}
    </div>
    {action && <div>{action}</div>}
  </div>
);

export default PageHeader;
