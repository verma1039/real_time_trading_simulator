import React, { useState, useEffect } from 'react';
import { client } from '../api/client';
import PageHeader from '../components/PageHeader';
import StatCard from '../components/StatCard';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import { ShieldAlert, Users, Briefcase, Activity, Download } from 'lucide-react';

const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStats = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await client.get('/admin/stats');
      setStats(res.data);
    } catch (err) {
      setError(err.message || 'Failed to load admin stats');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleExport = async (entity) => {
    try {
      const res = await client.get(`/admin/export/${entity}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${entity}_export_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      alert(`Export failed: ${err.message}`);
    }
  };

  if (isLoading) return <LoadingState message="Loading platform statistics..." />;
  if (error) return <ErrorState message={error} retryAction={fetchStats} />;

  return (
    <div className="d-flex flex-col gap-8">
      <PageHeader 
        title="Admin Dashboard" 
        subtitle="Platform statistics and data exports." 
      />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md-grid-cols-2 lg-grid-cols-4 gap-4">
        <StatCard 
          title="Active Users" 
          value={stats.active_users} 
          icon={Users}
        />
        <StatCard 
          title="Suspended Users" 
          value={stats.suspended_users} 
          icon={ShieldAlert}
          trend={stats.suspended_users > 0 ? "negative" : "neutral"}
        />
        <StatCard 
          title="Total Portfolios" 
          value={stats.total_portfolios} 
          icon={Briefcase}
        />
        <StatCard 
          title="Total Trades" 
          value={stats.total_trades} 
          icon={Activity}
        />
      </div>

      {/* Exports Section */}
      <div className="card">
        <div className="card-header border-b">
          <h3 className="text-md font-bold d-flex items-center gap-2">
            <Download size={18} /> Data Exports (CSV)
          </h3>
        </div>
        <div className="card-body d-flex flex-wrap gap-4">
          <button 
            onClick={() => handleExport('users')}
            className="btn btn-secondary d-flex items-center gap-2"
          >
            <Download size={16} /> Export Users
          </button>
          <button 
            onClick={() => handleExport('trades')}
            className="btn btn-secondary d-flex items-center gap-2"
          >
            <Download size={16} /> Export Trades
          </button>
          <button 
            onClick={() => handleExport('admin_logs')}
            className="btn btn-secondary d-flex items-center gap-2"
          >
            <Download size={16} /> Export Admin Logs
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
