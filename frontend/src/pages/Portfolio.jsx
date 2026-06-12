import React, { useState, useEffect } from 'react';
import { client } from '../api/client';
import PageHeader from '../components/PageHeader';
import StatCard from '../components/StatCard';
import PnLDisplay from '../components/PnLDisplay';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import QuoteFreshnessIndicator from '../components/QuoteFreshnessIndicator';
import { Wallet, PieChart, TrendingUp, Briefcase } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip as LineTooltip, ResponsiveContainer, CartesianGrid, PieChart as RePieChart, Pie, Cell, Tooltip as PieTooltip } from 'recharts';

const COLORS = ['#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#ef4444', '#6366f1'];

const Portfolio = () => {
  const [data, setData] = useState({
    portfolio: null,
    holdings: [],
    snapshots: [],
    quotes: {}
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const pfRes = await client.get('/portfolios');
      const portfolios = pfRes.data;
      if (portfolios.length === 0) {
        throw new Error('No portfolio found. Please create one.');
      }
      const portfolioId = portfolios[0].id;

      // Fetch details (which includes holdings)
      const detailRes = await client.get(`/portfolios/${portfolioId}`);
      const portfolioData = detailRes.data;
      const rawHoldings = portfolioData.holdings || [];

      // Fetch snapshots
      const snapRes = await client.get(`/portfolios/${portfolioId}/snapshots`);

      // Fetch live quotes for holdings using the batch endpoint
      let quotesMap = {};
      if (rawHoldings.length > 0) {
        const instrumentIds = rawHoldings.map(h => h.instrument_id);
        const quoteRes = await client.post('/market-data/quotes/batch', { instrument_ids: instrumentIds });
        const quotesArray = quoteRes.data || [];
        quotesMap = quotesArray.reduce((acc, q) => {
          acc[q.instrument_id] = q;
          return acc;
        }, {});
      }

      setData({
        portfolio: portfolioData,
        holdings: rawHoldings,
        snapshots: snapRes.data || [],
        quotes: quotesMap
      });
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || 'Failed to load portfolio data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (isLoading) return <LoadingState message="Loading portfolio..." />;
  if (error) return <ErrorState message={error} retryAction={fetchData} />;

  const { portfolio, holdings, snapshots, quotes } = data;

  // Recalculate metrics using live prices (Frontend aggregation strategy)
  let investedCost = 0;
  let totalMarketValue = 0;
  let totalUnrealizedPnL = 0;

  const enrichedHoldings = holdings.map(h => {
    const quote = quotes[h.instrument_id];
    // Fallback to average_cost if quote is missing for any reason
    const currentPrice = quote ? quote.current_price : h.average_cost;
    const marketValue = h.quantity * currentPrice;
    const costValue = h.quantity * h.average_cost;
    const unrealizedPnL = marketValue - costValue;
    const unrealizedPnLPercent = costValue > 0 ? (unrealizedPnL / costValue) * 100 : 0;
    
    investedCost += costValue;
    totalMarketValue += marketValue;
    totalUnrealizedPnL += unrealizedPnL;

    return {
      ...h,
      currentPrice,
      marketValue,
      unrealizedPnL,
      unrealizedPnLPercent,
      quoteStatus: quote ? (quote.is_market_open ? 'fresh' : 'stale') : 'delayed'
    };
  });

  const cashBalance = portfolio.cash_balance;
  const portfolioValue = cashBalance + totalMarketValue;
  const openingBalance = portfolio.opening_balance;
  
  // Total P&L = Current Value - Original Capital
  const totalPnL = portfolioValue - openingBalance;
  
  // Realized P&L = Total P&L - Unrealized P&L
  const realizedPnL = totalPnL - totalUnrealizedPnL;

  // Table Columns
  const holdingColumns = [
    { header: 'Symbol', render: (row) => (
      <div className="d-flex flex-col">
        <span className="font-bold">{row.symbol}</span>
        <QuoteFreshnessIndicator status={row.quoteStatus} />
      </div>
    )},
    { header: 'Qty', accessor: 'quantity', align: 'right' },
    { header: 'Avg Cost', render: (row) => `₹${row.average_cost.toFixed(2)}`, align: 'right' },
    { header: 'LTP', render: (row) => `₹${row.currentPrice.toFixed(2)}`, align: 'right' },
    { header: 'Market Value', render: (row) => `₹${row.marketValue.toFixed(2)}`, align: 'right' },
    { header: 'Unrealized P&L', align: 'right', render: (row) => (
      <div className="d-flex flex-col items-end">
        <PnLDisplay value={row.unrealizedPnL} prefix="₹" />
        <PnLDisplay value={row.unrealizedPnLPercent} isPercentage={true} />
      </div>
    )}
  ];

  // Chart Data
  const chartData = [...snapshots].map(s => ({
    date: new Date(s.snapshot_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    value: s.total_value,
    timestamp: new Date(s.snapshot_date).getTime()
  })).sort((a, b) => a.timestamp - b.timestamp);

  // Pie Chart Data
  const allocationData = enrichedHoldings.map(h => ({
    name: h.symbol,
    value: h.marketValue
  })).sort((a, b) => b.value - a.value);

  if (cashBalance > 0) {
    // Cash is always Green
    allocationData.push({ name: 'Cash', value: cashBalance, isCash: true });
  }

  return (
    <div className="d-flex flex-col gap-6">
      <PageHeader 
        title="Portfolio" 
        subtitle="Detailed analysis of your assets and performance." 
      />

      {/* Portfolio Summary Cards */}
      <div className="d-grid grid-cols-1 md-grid-cols-2 lg-grid-cols-3 gap-4">
        <StatCard title="Portfolio Value" value={`₹${portfolioValue.toFixed(2)}`} icon={PieChart} />
        <StatCard title="Cash Balance" value={`₹${cashBalance.toFixed(2)}`} icon={Wallet} />
        <StatCard title="Invested Cost" value={`₹${investedCost.toFixed(2)}`} icon={Briefcase} />
        <StatCard 
          title="Realized P&L" 
          value={<PnLDisplay value={realizedPnL} prefix="₹" />} 
          icon={TrendingUp} 
        />
        <StatCard 
          title="Unrealized P&L" 
          value={<PnLDisplay value={totalUnrealizedPnL} prefix="₹" />} 
          icon={TrendingUp} 
        />
        <StatCard 
          title="Total P&L" 
          value={<PnLDisplay value={totalPnL} prefix="₹" />} 
          subtitle={<PnLDisplay value={(totalPnL / openingBalance) * 100} isPercentage={true} />}
          icon={TrendingUp} 
        />
      </div>

      <div className="d-grid grid-cols-1 lg-grid-cols-3 gap-6">
        {/* Performance Chart */}
        <div className="card lg-col-span-2">
          <div className="card-header border-b">
            <h3 className="text-md font-bold">Historical Performance</h3>
          </div>
          <div className="card-body" style={{ height: '300px', padding: '16px 16px 16px 0' }}>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} tickFormatter={(val) => `₹${val}`} width={80} />
                  <LineTooltip 
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

        {/* Allocation Pie Chart */}
        <div className="card">
          <div className="card-header border-b">
            <h3 className="text-md font-bold">Asset Allocation</h3>
          </div>
          <div className="card-body" style={{ height: '300px' }}>
            {allocationData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <RePieChart>
                  <Pie
                    data={allocationData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {allocationData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.isCash ? '#10b981' : COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <PieTooltip 
                    formatter={(value) => [`₹${value.toFixed(2)}`, 'Value']}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                </RePieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full d-flex items-center justify-center">
                <EmptyState title="No assets" message="Fund your account to see allocation." icon={Briefcase} />
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="card mb-8">
        <div className="card-header border-b">
          <h3 className="text-md font-bold">Current Holdings</h3>
        </div>
        <DataTable 
          columns={holdingColumns} 
          data={enrichedHoldings} 
          isLoading={false}
          emptyStateProps={{
            title: 'No holdings',
            message: 'You have not purchased any instruments yet.',
            icon: Briefcase
          }}
        />
      </div>

    </div>
  );
};

export default Portfolio;
