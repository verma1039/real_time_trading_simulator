import React, { useState, useEffect } from 'react';
import { client } from '../api/client';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import Badge from '../components/Badge';
import { FileText } from 'lucide-react';

const AdminAuditLogs = () => {
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 20;

  const fetchLogs = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await client.get('/admin/logs?limit=500');
      setLogs(res.data);
    } catch (err) {
      setError(err.message || 'Failed to load audit logs');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const totalPages = Math.ceil(logs.length / ITEMS_PER_PAGE);
  const paginatedLogs = logs.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  const columns = [
    { header: 'Time', render: (row) => new Date(row.created_at).toLocaleString() },
    { header: 'Actor ID', render: (row) => <span className="text-xs font-mono">{row.actor_user_id.split('-')[0]}...</span> },
    { header: 'Action', render: (row) => <Badge variant="secondary">{row.action}</Badge> },
    { header: 'Target Type', accessor: 'target_type' },
    { header: 'Target ID', render: (row) => row.target_id ? <span className="text-xs font-mono">{row.target_id.split('-')[0]}...</span> : '-' },
    { header: 'Reason', accessor: 'reason' }
  ];

  if (isLoading) return <LoadingState message="Loading audit logs..." />;
  if (error) return <ErrorState message={error} retryAction={fetchLogs} />;

  return (
    <div className="d-flex flex-col gap-6">
      <PageHeader 
        title="Admin Audit Logs" 
        subtitle="Review all administrative actions taken on the platform." 
      />

      <div className="card">
        <div className="card-header border-b">
          <h3 className="text-md font-bold d-flex items-center gap-2"><FileText size={18} /> Audit Trail</h3>
        </div>
        <DataTable 
          columns={columns} 
          data={paginatedLogs} 
          isLoading={false}
          emptyStateProps={{
            title: 'No logs found',
            message: 'No administrative actions have been recorded yet.',
            icon: FileText
          }}
          paginationProps={totalPages > 1 ? {
            currentPage,
            totalPages,
            onPageChange: setCurrentPage
          } : undefined}
        />
      </div>
    </div>
  );
};

export default AdminAuditLogs;
