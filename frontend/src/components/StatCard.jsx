import React from 'react';

const StatCard = ({ title, value, subtitle, icon: Icon, valueClass = '' }) => (
  <div className="card">
    <div className="card-body d-flex flex-col gap-2">
      <div className="d-flex items-center justify-between">
        <h3 className="text-sm font-medium text-secondary">{title}</h3>
        {Icon && <Icon size={16} className="text-muted" />}
      </div>
      <p className={`text-2xl font-bold ${valueClass}`}>{value}</p>
      {subtitle && <p className="text-xs text-muted">{subtitle}</p>}
    </div>
  </div>
);

export default StatCard;
