import React, { useState, useEffect } from 'react';
import { client } from '../api/client';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';
import DataTable from '../components/DataTable';
import Badge from '../components/Badge';
import { ListOrdered } from 'lucide-react';

const Orders = () => {
  const [orders, setOrders] = useState([]);
  const [symbols, setSymbols] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchOrders = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await client.get('/trading/orders');
      const orderData = res.data || [];
      
      // Extract unique instrument IDs
      const uniqueIds = [...new Set(orderData.map(o => o.instrument_id))];
      
      // Fetch symbols via batch quotes
      const symMap = {};
      if (uniqueIds.length > 0) {
        const quoteRes = await client.post('/market-data/quotes/batch', { instrument_ids: uniqueIds });
        quoteRes.data.forEach(q => {
          symMap[q.instrument_id] = q.symbol;
        });
      }
      
      setSymbols(symMap);
      setOrders(orderData);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load orders.');
    } finally {
      setIsLoading(false);
    }
  };

  const ITEMS_PER_PAGE = 10;
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    fetchOrders();
  }, []);

  if (isLoading) return <LoadingState message="Loading orders..." />;
  if (error) return <ErrorState message={error} retryAction={fetchOrders} />;

  const getStatusColor = (status) => {
    switch(status) {
      case 'FILLED': return 'success';
      case 'REJECTED': return 'danger';
      case 'CANCELLED': return 'warning';
      default: return 'secondary';
    }
  };

  const columns = [
    { header: 'Time', render: (row) => new Date(row.created_at).toLocaleString() },
    { header: 'Symbol', render: (row) => <span className="font-bold">{symbols[row.instrument_id] || 'Unknown'}</span> },
    { header: 'Type', render: (row) => (
      <span className={row.side === 'BUY' ? 'text-success font-medium' : 'text-danger font-medium'}>
        {row.side} {row.order_type}
      </span>
    )},
    { header: 'Qty', accessor: 'quantity', align: 'right' },
    { header: 'Price', render: (row) => (
      row.execution_price ? `₹${row.execution_price.toFixed(2)}` : (row.limit_price ? `₹${row.limit_price.toFixed(2)}` : 'MKT')
    ), align: 'right' },
    { header: 'Status', render: (row) => (
      <Badge variant={getStatusColor(row.status)}>{row.status}</Badge>
    )}
  ];

  const totalPages = Math.ceil(orders.length / ITEMS_PER_PAGE);
  const paginatedOrders = orders.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  return (
    <div className="d-flex flex-col gap-6">
      <PageHeader 
        title="Orders" 
        subtitle="Track your market and limit orders." 
      />

      <div className="card">
        <DataTable 
          columns={columns} 
          data={paginatedOrders} 
          isLoading={false}
          emptyStateProps={{
            title: 'No orders found',
            message: 'Your order history will appear here once you start trading.',
            icon: ListOrdered
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

export default Orders;
