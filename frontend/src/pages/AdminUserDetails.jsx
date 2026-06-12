import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { client } from '../api/client';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import Badge from '../components/Badge';
import ConfirmModal from '../components/ConfirmModal';
import { User as UserIcon, ShieldAlert, CheckCircle, Wallet } from 'lucide-react';

const AdminUserDetails = () => {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Modals state
  const [isSuspendModalOpen, setIsSuspendModalOpen] = useState(false);
  const [isBalanceModalOpen, setIsBalanceModalOpen] = useState(false);
  
  // Form state
  const [reason, setReason] = useState('');
  const [adjustAmount, setAdjustAmount] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await client.get(`/admin/users/${userId}`);
      setData(res.data);
    } catch (err) {
      setError(err.message || 'Failed to fetch user details');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [userId]);

  const handleToggleSuspend = async () => {
    if (!reason.trim()) return alert("Reason is required");
    setIsSubmitting(true);
    try {
      const endpoint = data.user.is_suspended ? 'reactivate' : 'suspend';
      await client.post(`/admin/users/${userId}/${endpoint}`, { reason });
      setIsSuspendModalOpen(false);
      setReason('');
      fetchData();
    } catch (err) {
      alert(`Operation failed: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAdjustBalance = async () => {
    if (!reason.trim() || !adjustAmount) return alert("Amount and Reason are required");
    setIsSubmitting(true);
    try {
      await client.post(`/admin/portfolios/${data.portfolio.id}/adjust-balance`, {
        amount: parseFloat(adjustAmount),
        reason
      });
      setIsBalanceModalOpen(false);
      setAdjustAmount('');
      setReason('');
      fetchData();
    } catch (err) {
      alert(`Adjustment failed: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) return <LoadingState message="Loading user profile..." />;
  if (error) return <ErrorState message={error} retryAction={fetchData} />;

  const { user, portfolio } = data;

  return (
    <div className="d-flex flex-col gap-6">
      <div className="d-flex flex-col md-d-flex flex-row justify-between items-start md-items-center gap-4">
        <PageHeader 
          title="User Inspection" 
          subtitle={`Details for ${user.email}`} 
        />
        <div className="d-flex gap-2">
          {user.is_suspended ? (
            <button 
              onClick={() => setIsSuspendModalOpen(true)}
              className="btn btn-success d-flex items-center gap-2"
            >
              <CheckCircle size={16} /> Reactivate User
            </button>
          ) : (
            <button 
              onClick={() => setIsSuspendModalOpen(true)}
              className="btn btn-danger d-flex items-center gap-2"
            >
              <ShieldAlert size={16} /> Suspend User
            </button>
          )}
        </div>
      </div>

      {/* User Info Card */}
      <div className="card">
        <div className="card-header border-b">
          <h3 className="text-md font-bold d-flex items-center gap-2"><UserIcon size={18} /> User Identity</h3>
        </div>
        <div className="card-body grid grid-cols-1 md-grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-muted">ID</p>
            <p className="font-mono text-sm">{user.id}</p>
          </div>
          <div>
            <p className="text-sm text-muted">Email</p>
            <p className="font-medium">{user.email}</p>
          </div>
          <div>
            <p className="text-sm text-muted">Name</p>
            <p className="font-medium">{user.display_name || '-'}</p>
          </div>
          <div>
            <p className="text-sm text-muted">Status</p>
            {user.is_suspended ? <Badge variant="danger">Suspended</Badge> : <Badge variant="success">Active</Badge>}
          </div>
        </div>
      </div>

      {/* Portfolio Overview */}
      {portfolio ? (
        <>
          <div className="card border-primary border-opacity-50">
            <div className="card-header border-b d-flex justify-between items-center bg-primary bg-opacity-5">
              <h3 className="text-md font-bold text-primary d-flex items-center gap-2">
                <Wallet size={18} /> Portfolio & Balance
              </h3>
              <button 
                onClick={() => setIsBalanceModalOpen(true)}
                className="btn btn-sm btn-primary"
              >
                Adjust Balance
              </button>
            </div>
            <div className="card-body grid grid-cols-1 md-grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-muted">Portfolio ID</p>
                <p className="font-mono text-xs">{portfolio.id}</p>
              </div>
              <div>
                <p className="text-sm text-muted">Cash Balance</p>
                <p className="font-bold text-lg text-success">₹{portfolio.cash_balance.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-sm text-muted">Total Invested</p>
                <p className="font-medium">₹{portfolio.total_invested.toFixed(2)}</p>
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 lg-grid-cols-2 gap-6">
            <div className="card">
              <div className="card-header border-b">
                <h3 className="text-md font-bold text-primary">Recent Orders</h3>
              </div>
              <DataTable 
                columns={[
                  { header: 'Time', render: (row) => new Date(row.created_at).toLocaleString() },
                  { header: 'Type', render: (row) => <Badge variant={row.side === 'BUY' ? 'success' : 'danger'}>{row.side}</Badge> },
                  { header: 'Qty', accessor: 'quantity', align: 'right' },
                  { header: 'Status', render: (row) => <Badge variant="secondary">{row.status}</Badge> }
                ]}
                data={data.orders || []}
                isLoading={false}
                emptyStateProps={{ title: 'No orders', message: 'User has no recent orders.' }}
              />
            </div>
            
            <div className="card">
              <div className="card-header border-b">
                <h3 className="text-md font-bold text-primary">Recent Trades</h3>
              </div>
              <DataTable 
                columns={[
                  { header: 'Time', render: (row) => new Date(row.created_at).toLocaleString() },
                  { header: 'Side', render: (row) => <Badge variant={row.side === 'BUY' ? 'success' : 'danger'}>{row.side}</Badge> },
                  { header: 'Qty', accessor: 'quantity', align: 'right' },
                  { header: 'Price', render: (row) => `₹${row.execution_price.toFixed(2)}`, align: 'right' }
                ]}
                data={data.trades || []}
                isLoading={false}
                emptyStateProps={{ title: 'No trades', message: 'User has no recent trades.' }}
              />
            </div>
          </div>
          
          <div className="card">
            <div className="card-header border-b">
              <h3 className="text-md font-bold text-primary">Recent Ledger Entries</h3>
            </div>
            <DataTable 
              columns={[
                { header: 'Time', render: (row) => new Date(row.created_at).toLocaleString() },
                { header: 'Type', render: (row) => <Badge variant="secondary">{row.entry_type}</Badge> },
                { header: 'Description', accessor: 'description' },
                { header: 'Amount', render: (row) => (
                  <span className={row.amount > 0 ? 'text-success' : 'text-danger'}>
                    {row.amount > 0 ? '+' : ''}₹{row.amount.toFixed(2)}
                  </span>
                ), align: 'right' },
                { header: 'Balance', render: (row) => `₹${row.balance_after.toFixed(2)}`, align: 'right' }
              ]}
              data={data.ledger || []}
              isLoading={false}
              emptyStateProps={{ title: 'No ledger entries', message: 'User ledger is empty.' }}
            />
          </div>
        </>
      ) : (
        <div className="card p-6 text-center text-muted">
          User does not have a portfolio yet.
        </div>
      )}

      {/* Modals */}
      <ConfirmModal
        isOpen={isSuspendModalOpen}
        title={user.is_suspended ? "Reactivate User" : "Suspend User"}
        message={`Are you sure you want to ${user.is_suspended ? "reactivate" : "suspend"} this user?`}
        confirmText={user.is_suspended ? "Reactivate" : "Suspend"}
        cancelText="Cancel"
        variant={user.is_suspended ? "success" : "danger"}
        onConfirm={handleToggleSuspend}
        onCancel={() => { setIsSuspendModalOpen(false); setReason(''); }}
        isLoading={isSubmitting}
      >
        <div className="mt-4">
          <label className="label">Reason for Action (Required for Audit Log)</label>
          <input 
            type="text" 
            className="input" 
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g., Terms of service violation"
            required
          />
        </div>
      </ConfirmModal>

      <ConfirmModal
        isOpen={isBalanceModalOpen}
        title="Adjust Cash Balance"
        message="This action will directly modify the user's cash balance and create an ADMIN_ADJUSTMENT ledger entry. This cannot be undone."
        confirmText="Confirm Adjustment"
        cancelText="Cancel"
        variant="warning"
        onConfirm={handleAdjustBalance}
        onCancel={() => { setIsBalanceModalOpen(false); setReason(''); setAdjustAmount(''); }}
        isLoading={isSubmitting}
      >
        <div className="mt-4 d-flex flex-col gap-4">
          <div>
            <label className="label">Adjustment Amount (₹)</label>
            <input 
              type="number" 
              className="input" 
              value={adjustAmount}
              onChange={(e) => setAdjustAmount(e.target.value)}
              placeholder="e.g., 5000 or -5000"
              required
            />
            <p className="text-xs text-muted mt-1">Use negative numbers to deduct balance.</p>
          </div>
          <div>
            <label className="label">Reason (Required for Audit Log)</label>
            <input 
              type="text" 
              className="input" 
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g., Contest winner reward"
              required
            />
          </div>
        </div>
      </ConfirmModal>

    </div>
  );
};

export default AdminUserDetails;
