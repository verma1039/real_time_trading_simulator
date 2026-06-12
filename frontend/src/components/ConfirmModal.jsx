import React from 'react';
import { X } from 'lucide-react';

const ConfirmModal = ({ isOpen, onClose, onConfirm, title, message, confirmText = 'Confirm', confirmVariant = 'primary', isLoading = false }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop">
      <div className="modal-content">
        <div className="card-header d-flex justify-between items-center">
          <h3 className="text-lg font-bold">{title}</h3>
          <button onClick={onClose} className="text-muted hover-bg p-1 rounded-sm border-none bg-transparent cursor-pointer" disabled={isLoading}>
            <X size={20} />
          </button>
        </div>
        <div className="card-body">
          <p className="text-secondary">{message}</p>
        </div>
        <div className="card-footer d-flex justify-end gap-3">
          <button onClick={onClose} className="btn btn-outline" disabled={isLoading}>Cancel</button>
          <button onClick={onConfirm} className={`btn btn-${confirmVariant}`} disabled={isLoading}>
            {isLoading ? 'Processing...' : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmModal;
