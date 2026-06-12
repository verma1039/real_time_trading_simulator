import React, { useState, useEffect } from 'react';
import { client } from '../api/client';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';
import DataTable from '../components/DataTable';
import PnLDisplay from '../components/PnLDisplay';
import { History as HistoryIcon, Wallet } from 'lucide-react';

const History = () => {
  const [data, setData] = useState({
    trades: [],
    ledger: [],
    symbols: {}
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // 1. Get portfolio ID
      const pfRes = await client.get('/portfolios');
      if (pfRes.data.length === 0) throw new Error('No portfolio found.');
      const portfolioId = pfRes.data[0].id;

      // 2. Fetch Trades & Ledger
      const [tradesRes, ledgerRes] = await Promise.all([
        client.get('/trading/trades'),
        client.get(`/portfolios/${portfolioId}/ledger`, { params: { limit: 50 } })
      ]);

      const tradesData = tradesRes.data || [];
      const ledgerData = ledgerRes.data || [];

      // 3. Resolve symbols for trades
      const uniqueIds = [...new Set(tradesData.map(t => t.instrument_id))];
      const symMap = {};
      if (uniqueIds.length > 0) {
        const quoteRes = await client.post('/market-data/quotes/batch', { instrument_ids: uniqueIds });
        quoteRes.data.forEach(q => {
          symMap[q.instrument_id] = q.symbol;
        });
      }

      setData({
        trades: tradesData,
        ledger: ledgerData,
        symbols: symMap
      });
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load history.');
    } finally {
      setIsLoading(false);
    }
  };

  const ITEMS_PER_PAGE = 10;
  
  // Trade state
  const [tradeFilter, setTradeFilter] = useState('ALL');
  const [tradePage, setTradePage] = useState(1);
  
  // Ledger state
  const [ledgerFilter, setLedgerFilter] = useState('ALL');
  const [ledgerPage, setLedgerPage] = useState(1);

  useEffect(() => {
    fetchData();
  }, []);

  if (isLoading) return <LoadingState message="Loading account history..." />;
  if (error) return <ErrorState message={error} retryAction={fetchData} />;

  const { trades, ledger, symbols } = data;

  const tradeColumns = [
    { header: 'Time', render: (row) => new Date(row.created_at).toLocaleString() },
    { header: 'Symbol', render: (row) => <span className="font-bold">{symbols[row.instrument_id] || 'Unknown'}</span> },
    { header: 'Side', render: (row) => (
      <span className={row.side === 'BUY' ? 'text-success font-medium' : 'text-danger font-medium'}>
        {row.side}
      </span>
    )},
    { header: 'Qty', accessor: 'quantity', align: 'right' },
    { header: 'Exec Price', render: (row) => `₹${row.execution_price.toFixed(2)}`, align: 'right' },
    { header: 'Charges', render: (row) => `₹${row.total_charges.toFixed(2)}`, align: 'right' },
    { header: 'Realized P&L', align: 'right', render: (row) => (
      row.realized_pnl !== 0 ? <PnLDisplay value={row.realized_pnl} prefix="₹" /> : '-'
    )}
  ];

  const ledgerColumns = [
    { header: 'Time', render: (row) => new Date(row.created_at).toLocaleString() },
    { header: 'Type', render: (row) => (
      <span className={row.entry_type === 'DEPOSIT' || row.entry_type === 'SELL' ? 'text-success' : 'text-danger'}>
        {row.entry_type}
      </span>
    )},
    { header: 'Description', accessor: 'description' },
    { header: 'Amount', render: (row) => (
      <span className={row.amount > 0 ? 'text-success' : 'text-danger'}>
        {row.amount > 0 ? '+' : ''}₹{row.amount.toFixed(2)}
      </span>
    ), align: 'right' },
    { header: 'Balance', render: (row) => `₹${row.balance_after.toFixed(2)}`, align: 'right' }
  ];

  // Apply filters
  const filteredTrades = trades.filter(t => tradeFilter === 'ALL' || t.side === tradeFilter);
  const filteredLedger = ledger.filter(l => ledgerFilter === 'ALL' || l.entry_type === ledgerFilter);

  // Apply pagination
  const tradeTotalPages = Math.ceil(filteredTrades.length / ITEMS_PER_PAGE);
  const paginatedTrades = filteredTrades.slice((tradePage - 1) * ITEMS_PER_PAGE, tradePage * ITEMS_PER_PAGE);

  const ledgerTotalPages = Math.ceil(filteredLedger.length / ITEMS_PER_PAGE);
  const paginatedLedger = filteredLedger.slice((ledgerPage - 1) * ITEMS_PER_PAGE, ledgerPage * ITEMS_PER_PAGE);

  return (
    <div className="d-flex flex-col gap-8">
      <PageHeader 
        title="Account History" 
        subtitle="Review your past trades and cash ledger." 
      />

      {/* Trades Section */}
      <div className="card">
        <div className="card-header border-b d-flex justify-between items-center">
          <h3 className="text-md font-bold d-flex items-center gap-2"><HistoryIcon size={18} /> Trade History</h3>
          <select 
            className="input py-1 px-2 text-sm max-w-[120px]" 
            value={tradeFilter} 
            onChange={(e) => { setTradeFilter(e.target.value); setTradePage(1); }}
          >
            <option value="ALL">All Trades</option>
            <option value="BUY">Buy</option>
            <option value="SELL">Sell</option>
          </select>
        </div>
        <DataTable 
          columns={tradeColumns} 
          data={paginatedTrades} 
          isLoading={false}
          emptyStateProps={{
            title: 'No trades found',
            message: 'Your executed trades will appear here.',
            icon: HistoryIcon
          }}
          paginationProps={tradeTotalPages > 1 ? {
            currentPage: tradePage,
            totalPages: tradeTotalPages,
            onPageChange: setTradePage
          } : undefined}
        />
      </div>

      {/* Ledger Section */}
      <div className="card mb-8">
        <div className="card-header border-b d-flex justify-between items-center">
          <h3 className="text-md font-bold d-flex items-center gap-2"><Wallet size={18} /> Cash Ledger</h3>
          <select 
            className="input py-1 px-2 text-sm max-w-[150px]" 
            value={ledgerFilter} 
            onChange={(e) => { setLedgerFilter(e.target.value); setLedgerPage(1); }}
          >
            <option value="ALL">All Entries</option>
            <option value="DEPOSIT">Deposit</option>
            <option value="WITHDRAWAL">Withdrawal</option>
            <option value="TRADE">Trade</option>
            <option value="RESET">Reset</option>
          </select>
        </div>
        <DataTable 
          columns={ledgerColumns} 
          data={paginatedLedger} 
          isLoading={false}
          emptyStateProps={{
            title: 'No transactions found',
            message: 'Your deposits, withdrawals, and trade settlements will appear here.',
            icon: Wallet
          }}
          paginationProps={ledgerTotalPages > 1 ? {
            currentPage: ledgerPage,
            totalPages: ledgerTotalPages,
            onPageChange: setLedgerPage
          } : undefined}
        />
      </div>
    </div>
  );
};

export default History;
