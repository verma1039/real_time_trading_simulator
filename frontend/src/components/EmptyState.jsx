import React from 'react';

const EmptyState = ({ icon: Icon, title, message, action }) => (
  <div className="d-flex flex-col items-center justify-center p-8 text-center border-light rounded-md bg-surface my-4">
    {Icon && <div className="mb-4 text-muted"><Icon size={48} /></div>}
    <h3 className="text-lg font-semibold mb-2">{title}</h3>
    <p className="text-secondary text-sm mb-4 max-w-sm mx-auto">{message}</p>
    {action && <div>{action}</div>}
  </div>
);

export default EmptyState;
