import React from 'react';
import LoadingState from './LoadingState';
import EmptyState from './EmptyState';
import Pagination from './Pagination';

const DataTable = ({ 
  columns, 
  data, 
  isLoading, 
  emptyStateProps, 
  paginationProps 
}) => {
  if (isLoading) {
    return <div className="border border-light rounded-md bg-surface p-4"><LoadingState /></div>;
  }

  if (!data || data.length === 0) {
    return <EmptyState {...emptyStateProps} />;
  }

  return (
    <div className="card">
      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              {columns.map((col, idx) => (
                <th key={idx} className={col.align === 'right' ? 'text-right' : 'text-left'}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIndex) => (
              <tr key={row.id || rowIndex}>
                {columns.map((col, colIndex) => (
                  <td key={colIndex} className={col.align === 'right' ? 'text-right' : 'text-left'}>
                    {col.render ? col.render(row) : row[col.accessor]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {paginationProps && (
        <div className="px-4 border-t border-light bg-base">
          <Pagination {...paginationProps} />
        </div>
      )}
    </div>
  );
};

export default DataTable;
