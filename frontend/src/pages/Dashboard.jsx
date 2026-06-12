import React, { useState, useEffect } from 'react';
import { client } from '../api/client';
import PageHeader from '../components/PageHeader';
import StatCard from '../components/StatCard';
import PnLDisplay from '../components/PnLDisplay';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import { Wallet, TrendingUp, PieChart, History, Eye, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

const Dashboard = () => {
  const [data, setData] = useState({
    portfolio: null,
    snapshots: [],
    trades: [],
    watchlists: []
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Fetch default portfolio
      const pfRes = await client.get('/portfolios');
      const portfolios = pfRes.data;
      if (portfolios.length === 0) {
        throw new Error('No portfolio found. Please create one.');
      }
      const portfolio = portfolios[0];

      // Fetch snapshots for charting
      const snapRes = await client.get(`/portfolios/${portfolio.id}/snapshots`);
      
      // Fetch recent trades
      const tradeRes = await client.get('/trading/trades', { params: { limit: 5 } });

      // Fetch watchlists
      const wlRes = await client.get('/market-data/watchlists');

      setData({
        portfolio,
        snapshots: snapRes.data || [],
        trades: tradeRes.data.items || tradeRes.data || [],
        watchlists: wlRes.data || []
      });
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (isLoading) return <LoadingState message="Loading dashboard..." />;
  if (error) return <ErrorState message={error} retryAction={fetchData} />;

  const { portfolio, snapshots, trades, watchlists } = data;
  
  // Trades columns
  const tradeColumns = [
    { header: 'Date', render: (row) => new Date(row.execution_time).toLocaleDateString() },
    { header: 'Symbol', accessor: 'symbol' },
    { header: 'Side', render: (row) => (
      <span className={row.side === 'BUY' ? 'text-success font-medium' : 'text-danger font-medium'}>{row.side}</span>
    )},
    { header: 'Qty', accessor: 'quantity', align: 'right' },
    { header: 'Price', render: (row) => `₹${row.execution_price.toFixed(2)}`, align: 'right' }
  ];

  // Prepare chart data (sort chronologically)
  const chartData = [...snapshots].map(s => ({
    date: new Date(s.snapshot_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    value: s.total_value,
    timestamp: new Date(s.snapshot_date).getTime()
  })).sort((a, b) => a.timestamp - b.timestamp);

  return (
    <div className="d-flex flex-col gap-6">
      <PageHeader 
        title="Dashboard" 
        subtitle="Overview of your portfolio and recent activity." 
      />

      {/* Portfolio Summary Cards */}
      <div className="d-grid grid-cols-1 md-grid-cols-2 lg-grid-cols-4 gap-4">
        <StatCard 
          title="Portfolio Value" 
          value={`₹${portfolio.total_value.toFixed(2)}`} 
          icon={PieChart} 
        />
        <StatCard 
          title="Cash Balance" 
          value={`₹${portfolio.cash_balance.toFixed(2)}`} 
          icon={Wallet} 
        />
        <StatCard 
          title="Invested Cost" 
          value={`₹${portfolio.invested_amount.toFixed(2)}`} 
          icon={TrendingUp} 
        />
        <StatCard 
          title="Total P&L" 
          value={<PnLDisplay value={portfolio.total_pnl} prefix="₹" />} 
          subtitle={<PnLDisplay value={portfolio.total_pnl_percent} isPercentage={true} />}
          icon={TrendingUp} 
        />
      </div>

      <div className="d-grid grid-cols-1 lg-grid-cols-3 gap-6">
        
        {/* Performance Chart */}
        <div className="card lg-col-span-2">
          <div className="card-header border-b">
            <h3 className="text-md font-bold">Portfolio Performance</h3>
          </div>
          <div className="card-body" style={{ height: '350px', padding: '16px 16px 16px 0' }}>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} tickFormatter={(val) => `₹${val}`} width={80} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    formatter={(value) => [`₹${value.toFixed(2)}`, 'Value']}
                  />
                  <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full d-flex items-center justify-center">
                <EmptyState title="No snapshot data" message="Performance charts require daily portfolio snapshots." icon={TrendingUp} />
              </div>
            )}
          </div>
        </div>

        {/* Watchlist Preview */}
        <div className="card d-flex flex-col">
          <div className="card-header border-b d-flex justify-between items-center">
            <h3 className="text-md font-bold d-flex items-center gap-2"><Eye size={18} className="text-secondary" /> Watchlists</h3>
            <Link to="/watchlists" className="text-primary text-sm font-medium d-flex items-center gap-1 hover-underline">
              View All <ArrowRight size={14} />
            </Link>
          </div>
          <div className="card-body p-0 flex-1 d-flex flex-col">
            {watchlists.length > 0 ? (
              <div className="d-flex flex-col">
                {watchlists.slice(0, 5).map(wl => (
                  <Link key={wl.id} to={`/watchlists/${wl.id}`} className="d-flex items-center justify-between p-4 border-b hover-bg transition-default text-inherit decoration-none">
                    <span className="font-medium text-sm">{wl.name}</span>
                    <span className="badge badge-primary">{wl.instruments?.length || 0} items</span>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="flex-1 d-flex items-center justify-center p-4">
                <EmptyState title="No watchlists" message="Create a watchlist to track instruments." icon={Eye} />
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Recent Trades */}
      <div className="card mb-8">
        <div className="card-header border-b d-flex justify-between items-center">
          <h3 className="text-md font-bold d-flex items-center gap-2"><History size={18} className="text-secondary" /> Recent Trades</h3>
          <Link to="/history" className="text-primary text-sm font-medium d-flex items-center gap-1 hover-underline">
            View All <ArrowRight size={14} />
          </Link>
        </div>
        <DataTable 
          columns={tradeColumns} 
          data={trades} 
          isLoading={false}
          emptyStateProps={{
            title: 'No recent trades',
            message: 'Your recent trading activity will appear here.',
            icon: History
          }}
        />
      </div>

    </div>
  );
};

export default Dashboard;
