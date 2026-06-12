import React, { useState, useEffect, useCallback } from 'react';
import { client } from '../api/client';
import PageHeader from '../components/PageHeader';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';
import DataTable from '../components/DataTable';
import SearchInput from '../components/SearchInput';
import ConfirmModal from '../components/ConfirmModal';
import PriceChange from '../components/PriceChange';
import QuoteFreshnessIndicator from '../components/QuoteFreshnessIndicator';
import { Eye, Plus, Trash2, List, TrendingUp, Search } from 'lucide-react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';

const Watchlists = () => {
  const [watchlists, setWatchlists] = useState([]);
  const [activeWatchlistId, setActiveWatchlistId] = useState(null);
  const [activeWatchlist, setActiveWatchlist] = useState(null);
  const [quotes, setQuotes] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Create Watchlist State
  const [newWatchlistName, setNewWatchlistName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // Delete Watchlist State
  const [watchlistToDelete, setWatchlistToDelete] = useState(null);

  // Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  // Fetch all watchlists
  const fetchWatchlists = async () => {
    try {
      const res = await client.get('/watchlists');
      setWatchlists(res.data);
      if (res.data.length > 0 && !activeWatchlistId) {
        setActiveWatchlistId(res.data[0].id);
      } else if (res.data.length === 0) {
        setActiveWatchlistId(null);
        setActiveWatchlist(null);
        setIsLoading(false);
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load watchlists.');
      setIsLoading(false);
    }
  };

  // Fetch active watchlist details and quotes
  const fetchActiveWatchlistData = async (id) => {
    setIsLoading(true);
    try {
      const [wlRes, quotesRes] = await Promise.all([
        client.get(`/watchlists/${id}`),
        client.get(`/watchlists/${id}/quotes`)
      ]);
      
      setActiveWatchlist(wlRes.data);
      
      const quotesMap = {};
      quotesRes.data.forEach(q => {
        quotesMap[q.instrument_id] = q;
      });
      setQuotes(quotesMap);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load watchlist details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchWatchlists();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (activeWatchlistId) {
      fetchActiveWatchlistData(activeWatchlistId);
    }
  }, [activeWatchlistId]);

  // Debounced Search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    
    const delayDebounceFn = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await client.get('/instruments/search', { params: { query: searchQuery, limit: 5 } });
        setSearchResults(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery]);

  const handleCreateWatchlist = async (e) => {
    e.preventDefault();
    if (!newWatchlistName.trim()) return;
    setIsCreating(true);
    try {
      const res = await client.post('/watchlists', { name: newWatchlistName });
      setNewWatchlistName('');
      toast.success('Watchlist created');
      await fetchWatchlists();
      setActiveWatchlistId(res.data.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create watchlist');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteWatchlist = async () => {
    if (!watchlistToDelete) return;
    try {
      await client.delete(`/watchlists/${watchlistToDelete}`);
      toast.success('Watchlist deleted');
      setWatchlistToDelete(null);
      if (activeWatchlistId === watchlistToDelete) {
        setActiveWatchlistId(null);
      }
      fetchWatchlists();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete watchlist');
    }
  };

  const handleAddInstrument = async (instrumentId) => {
    try {
      await client.post(`/watchlists/${activeWatchlistId}/items`, { instrument_id: instrumentId });
      toast.success('Added to watchlist');
      setSearchQuery('');
      setSearchResults([]);
      fetchActiveWatchlistData(activeWatchlistId);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add instrument');
    }
  };

  const handleRemoveInstrument = async (instrumentId) => {
    try {
      await client.delete(`/watchlists/${activeWatchlistId}/items/${instrumentId}`);
      toast.success('Removed from watchlist');
      fetchActiveWatchlistData(activeWatchlistId);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to remove instrument');
    }
  };

  if (error) return <ErrorState message={error} retryAction={fetchWatchlists} />;

  const enrichedItems = activeWatchlist?.items.map(item => {
    const quote = quotes[item.instrument.id];
    return {
      ...item.instrument,
      currentPrice: quote ? quote.current_price : null,
      previousClose: quote ? quote.previous_close : null,
      quoteStatus: quote ? (quote.is_market_open ? 'fresh' : 'stale') : 'delayed',
    };
  }) || [];

  const columns = [
    { header: 'Symbol', render: (row) => (
      <div className="d-flex flex-col">
        <span className="font-bold">{row.symbol}</span>
        <span className="text-sm text-secondary truncate max-w-[150px]" title={row.name}>{row.name}</span>
      </div>
    )},
    { header: 'LTP', render: (row) => (
      row.currentPrice !== null ? `₹${row.currentPrice.toFixed(2)}` : 'N/A'
    ), align: 'right' },
    { header: 'Change', render: (row) => (
      row.currentPrice !== null && row.previousClose !== null ? (
        <PriceChange currentPrice={row.currentPrice} previousPrice={row.previousClose} />
      ) : 'N/A'
    ), align: 'right' },
    { header: 'Status', render: (row) => <QuoteFreshnessIndicator status={row.quoteStatus} /> },
    { header: 'Actions', align: 'right', render: (row) => (
      <div className="d-flex items-center gap-2 justify-end">
        <Link to={`/trade?instrument=${row.id}`} className="btn btn-primary btn-sm px-3 py-1">Trade</Link>
        <button className="btn btn-outline btn-sm text-danger px-2 py-1" onClick={() => handleRemoveInstrument(row.id)}>
          <Trash2 size={16} />
        </button>
      </div>
    )}
  ];

  return (
    <div className="d-flex flex-col gap-6">
      <PageHeader 
        title="Watchlists" 
        subtitle="Track your favorite instruments across custom lists." 
      />

      <div className="d-grid grid-cols-1 lg-grid-cols-4 gap-6">
        
        {/* Sidebar / Top area for Watchlist selection */}
        <div className="card h-fit">
          <div className="card-header border-b">
            <h3 className="text-md font-bold d-flex items-center gap-2"><List size={18} /> My Lists</h3>
          </div>
          <div className="card-body p-0">
            {watchlists.length > 0 ? (
              <ul className="d-flex flex-col m-0 p-0 list-none">
                {watchlists.map(wl => (
                  <li key={wl.id} className={`p-4 border-b cursor-pointer transition-default d-flex justify-between items-center ${activeWatchlistId === wl.id ? 'bg-primary-light text-primary border-primary-light font-medium' : 'hover-bg'}`}
                      onClick={() => setActiveWatchlistId(wl.id)}>
                    <span>{wl.name}</span>
                    {activeWatchlistId === wl.id && (
                      <button className="text-danger hover-text-danger p-1" onClick={(e) => { e.stopPropagation(); setWatchlistToDelete(wl.id); }}>
                        <Trash2 size={16} />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="p-6 text-center text-secondary text-sm">No watchlists found.</div>
            )}
          </div>
          <div className="card-footer bg-base-alt p-4">
            <form onSubmit={handleCreateWatchlist} className="d-flex flex-col gap-2">
              <input 
                type="text" 
                className="input text-sm" 
                placeholder="New watchlist name" 
                value={newWatchlistName}
                onChange={(e) => setNewWatchlistName(e.target.value)}
                required
              />
              <button type="submit" className="btn btn-outline btn-sm w-full d-flex items-center justify-center gap-2" disabled={isCreating}>
                <Plus size={16} /> {isCreating ? 'Creating...' : 'Create List'}
              </button>
            </form>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="lg-col-span-3 d-flex flex-col gap-4">
          
          {!activeWatchlistId ? (
            <div className="card h-full d-flex items-center justify-center p-8">
              <EmptyState 
                title="No Watchlist Selected" 
                message="Select a watchlist from the menu or create a new one to start tracking instruments." 
                icon={Eye} 
              />
            </div>
          ) : isLoading ? (
            <div className="card h-full"><LoadingState message="Loading watchlist data..." /></div>
          ) : (
            <>
              {/* Search to add */}
              <div className="card">
                <div className="card-body">
                  <div className="relative">
                    <SearchInput 
                      value={searchQuery} 
                      onChange={(e) => setSearchQuery(e.target.value)} 
                      placeholder="Search to add instruments (e.g., RELIANCE.NS)" 
                    />
                    {isSearching && <div className="absolute right-3 top-1/2 -translate-y-1/2"><div className="skeleton" style={{width: '20px', height: '20px', borderRadius: '50%'}}></div></div>}
                    
                    {searchResults.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-base border rounded-md shadow-lg max-h-[300px] overflow-y-auto">
                        {searchResults.map(inst => (
                          <div key={inst.id} className="d-flex justify-between items-center p-3 border-b hover-bg transition-default cursor-pointer" onClick={() => handleAddInstrument(inst.id)}>
                            <div className="d-flex flex-col">
                              <span className="font-bold text-sm">{inst.symbol}</span>
                              <span className="text-xs text-secondary">{inst.name}</span>
                            </div>
                            <button className="btn btn-primary btn-sm px-2 py-1"><Plus size={16} /></button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Data Table */}
              <div className="card">
                <div className="card-header border-b d-flex justify-between items-center">
                  <h3 className="text-md font-bold">{activeWatchlist?.name}</h3>
                  <span className="badge badge-primary">{enrichedItems.length} items</span>
                </div>
                <DataTable 
                  columns={columns} 
                  data={enrichedItems} 
                  isLoading={false}
                  emptyStateProps={{
                    title: 'Watchlist is empty',
                    message: 'Search and add instruments to track them here.',
                    icon: TrendingUp
                  }}
                />
              </div>
            </>
          )}

        </div>
      </div>

      <ConfirmModal 
        isOpen={!!watchlistToDelete}
        onClose={() => setWatchlistToDelete(null)}
        onConfirm={handleDeleteWatchlist}
        title="Delete Watchlist"
        message="Are you sure you want to delete this watchlist? This action cannot be undone."
        confirmText="Delete"
        isDestructive={true}
      />
    </div>
  );
};

export default Watchlists;
