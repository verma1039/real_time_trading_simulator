import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const Pagination = ({ currentPage, totalPages, onPageChange }) => {
  if (totalPages <= 1) return null;

  return (
    <div className="d-flex items-center justify-between py-3">
      <span className="text-sm text-muted">
        Page {currentPage} of {totalPages}
      </span>
      <div className="d-flex items-center gap-2">
        <button 
          className="btn btn-outline btn-sm" 
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
        >
          <ChevronLeft size={16} />
        </button>
        <button 
          className="btn btn-outline btn-sm" 
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(currentPage + 1)}
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
};

export default Pagination;
