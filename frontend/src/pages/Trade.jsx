import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { client } from '../api/client';
import PageHeader from '../components/PageHeader';
import SearchInput from '../components/SearchInput';
import ErrorState from '../components/ErrorState';
import LoadingState from '../components/LoadingState';
import ConfirmModal from '../components/ConfirmModal';
import PriceChange from '../components/PriceChange';
import QuoteFreshnessIndicator from '../components/QuoteFreshnessIndicator';
import { Search, Zap, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';

const Trade = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const instrumentIdFromUrl = searchParams.get('instrument');

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  const [selectedInstrument, setSelectedInstrument] = useState(null);
  const [quote, setQuote] = useState(null);
  const [isInstrumentLoading, setIsInstrumentLoading] = useState(false);
  const [instrumentError, setInstrumentError] = useState(null);

  const [side, setSide] = useState('BUY');
  const [quantity, setQuantity] = useState('');
  
  const [simulation, setSimulation] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationError, setSimulationError] = useState(null);
  const [idempotencyKey, setIdempotencyKey] = useState('');

  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

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

  // Fetch instrument & quote when URL param changes
  const fetchInstrumentData = useCallback(async (id) => {
    setIsInstrumentLoading(true);
    setInstrumentError(null);
    try {
      const [instRes, quoteRes] = await Promise.all([
        client.get(`/instruments/${id}`),
        client.get(`/market-data/quotes/${id}`)
      ]);
      setSelectedInstrument(instRes.data);
      setQuote(quoteRes.data);
      // Reset form
      setQuantity('');
      setSimulation(null);
      setSimulationError(null);
    } catch (err) {
      setInstrumentError('Failed to load instrument data. It may not exist.');
      setSelectedInstrument(null);
      setQuote(null);
    } finally {
      setIsInstrumentLoading(false);
    }
  }, []);

  useEffect(() => {
    if (instrumentIdFromUrl) {
      fetchInstrumentData(instrumentIdFromUrl);
    } else {
      setSelectedInstrument(null);
      setQuote(null);
    }
  }, [instrumentIdFromUrl, fetchInstrumentData]);

  const handleSelectInstrument = (inst) => {
    setSearchQuery('');
    setSearchResults([]);
    setSearchParams({ instrument: inst.id });
  };

  const handleSimulate = async (e) => {
    e.preventDefault();
    if (!selectedInstrument || !quantity || quantity <= 0) return;
    
    const key = crypto.randomUUID();
    setIdempotencyKey(key);
    
    setIsSimulating(true);
    setSimulationError(null);
    
    try {
      const res = await client.post('/trading/orders/simulate', {
        instrument_id: selectedInstrument.id,
        side: side,
        quantity: parseInt(quantity, 10),
        idempotency_key: key
      });
      setSimulation(res.data);
      setIsConfirmModalOpen(true);
    } catch (err) {
      setSimulationError(err.response?.data?.detail || 'Simulation failed');
    } finally {
      setIsSimulating(false);
    }
  };

  const handleExecute = async () => {
    if (!simulation || !idempotencyKey) return;
    
    setIsExecuting(true);
    try {
      await client.post('/trading/orders', {
        instrument_id: selectedInstrument.id,
        side: side,
        quantity: parseInt(quantity, 10),
        idempotency_key: idempotencyKey
      });
      
      toast.success('Order executed successfully');
      setIsConfirmModalOpen(false);
      setQuantity('');
      setSimulation(null);
      
      // Refresh quote
      const quoteRes = await client.get(`/market-data/quotes/${selectedInstrument.id}`);
      setQuote(quoteRes.data);
      
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Order execution failed');
      setIsConfirmModalOpen(false); // Close modal on error, force user to re-simulate if they want
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="d-flex flex-col gap-6">
      <PageHeader 
        title="Trade" 
        subtitle="Execute market orders instantly." 
      />

      <div className="d-grid grid-cols-1 lg-grid-cols-2 gap-6">
        
        {/* Left Column: Search & Selection */}
        <div className="d-flex flex-col gap-6">
          <div className="card">
            <div className="card-header border-b">
              <h3 className="text-md font-bold">Find Instrument</h3>
            </div>
            <div className="card-body">
              <div className="relative">
                <SearchInput 
                  value={searchQuery} 
                  onChange={(e) => setSearchQuery(e.target.value)} 
                  placeholder="Search NSE stocks (e.g., RELIANCE.NS)" 
                />
                {isSearching && <div className="absolute right-3 top-1/2 -translate-y-1/2"><div className="skeleton" style={{width: '20px', height: '20px', borderRadius: '50%'}}></div></div>}
                
                {searchResults.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-base border rounded-md shadow-lg max-h-[300px] overflow-y-auto">
                    {searchResults.map(inst => (
                      <div key={inst.id} className="d-flex justify-between items-center p-3 border-b hover-bg transition-default cursor-pointer" onClick={() => handleSelectInstrument(inst)}>
                        <div className="d-flex flex-col">
                          <span className="font-bold text-sm">{inst.symbol}</span>
                          <span className="text-xs text-secondary">{inst.name}</span>
                        </div>
                        <span className="badge badge-primary">{inst.instrument_type}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {isInstrumentLoading ? (
            <div className="card h-[200px]"><LoadingState message="Fetching market data..." /></div>
          ) : instrumentError ? (
            <ErrorState message={instrumentError} />
          ) : selectedInstrument && quote ? (
            <div className="card">
              <div className="card-header border-b d-flex justify-between items-start">
                <div className="d-flex flex-col">
                  <h2 className="text-2xl font-bold">{selectedInstrument.symbol}</h2>
                  <span className="text-sm text-secondary">{selectedInstrument.name}</span>
                </div>
                <QuoteFreshnessIndicator status={quote.is_market_open ? 'fresh' : 'stale'} />
              </div>
              <div className="card-body d-flex justify-between items-center">
                <div className="d-flex flex-col">
                  <span className="text-sm text-secondary mb-1">Current Price</span>
                  <span className="text-3xl font-bold">₹{quote.current_price.toFixed(2)}</span>
                </div>
                <div className="d-flex flex-col items-end">
                  <span className="text-sm text-secondary mb-1">Day Change</span>
                  {quote.previous_close ? (
                    <PriceChange currentPrice={quote.current_price} previousPrice={quote.previous_close} />
                  ) : (
                    <span className="text-md">N/A</span>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="card h-[200px] d-flex items-center justify-center p-6 text-center text-secondary border-dashed">
              <Search size={32} className="mb-2 opacity-50" />
              <p>Search and select an instrument to trade.</p>
            </div>
          )}
        </div>

        {/* Right Column: Order Entry */}
        <div className="d-flex flex-col gap-6">
          <div className="card">
            <div className="card-header border-b">
              <h3 className="text-md font-bold d-flex items-center gap-2"><Zap size={18} className="text-primary" /> Order Entry</h3>
            </div>
            
            {!selectedInstrument ? (
              <div className="card-body p-6 text-center text-secondary">
                Select an instrument first.
              </div>
            ) : (
              <div className="card-body">
                <form onSubmit={handleSimulate} className="d-flex flex-col gap-6">
                  
                  {/* Buy/Sell Toggle */}
                  <div className="d-flex bg-base-alt p-1 rounded-md">
                    <button 
                      type="button" 
                      className={`flex-1 py-2 text-sm font-bold rounded-sm transition-default border-none cursor-pointer ${side === 'BUY' ? 'bg-success text-white shadow-sm' : 'bg-transparent text-secondary hover-bg'}`}
                      onClick={() => setSide('BUY')}
                    >
                      BUY
                    </button>
                    <button 
                      type="button" 
                      className={`flex-1 py-2 text-sm font-bold rounded-sm transition-default border-none cursor-pointer ${side === 'SELL' ? 'bg-danger text-white shadow-sm' : 'bg-transparent text-secondary hover-bg'}`}
                      onClick={() => setSide('SELL')}
                    >
                      SELL
                    </button>
                  </div>

                  {/* Quantity Input */}
                  <div className="d-flex flex-col gap-2">
                    <label className="text-sm font-medium text-secondary">Quantity</label>
                    <input 
                      type="number" 
                      className="input w-full text-lg font-mono" 
                      placeholder="0" 
                      min="1"
                      step="1"
                      value={quantity}
                      onChange={(e) => setQuantity(e.target.value)}
                      required
                    />
                  </div>

                  {simulationError && (
                    <div className="p-3 bg-danger-light text-danger text-sm rounded-md border border-danger-light d-flex items-center gap-2">
                      <AlertTriangle size={16} /> {simulationError}
                    </div>
                  )}

                  <button 
                    type="submit" 
                    className={`btn ${side === 'BUY' ? 'bg-success hover:opacity-90 text-white' : 'bg-danger hover:opacity-90 text-white'} w-full font-bold py-3 text-md`}
                    disabled={isSimulating || !quantity || quantity <= 0}
                  >
                    {isSimulating ? 'Simulating...' : `Review ${side} Order`}
                  </button>

                  <div className="text-xs text-center text-secondary">
                    Market orders are executed immediately at the best available price.
                  </div>
                </form>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      <ConfirmModal 
        isOpen={isConfirmModalOpen}
        onClose={() => setIsConfirmModalOpen(false)}
        onConfirm={handleExecute}
        title="Confirm Order Details"
        confirmText={`Confirm ${side}`}
        confirmVariant={side === 'BUY' ? 'success' : 'danger'}
        isLoading={isExecuting}
        message={
          simulation ? (
            <div className="d-flex flex-col gap-4 mt-2">
              <div className="d-grid grid-cols-2 gap-y-3 gap-x-4 text-sm">
                <span className="text-secondary">Instrument</span>
                <span className="font-bold text-right">{selectedInstrument?.symbol}</span>
                
                <span className="text-secondary">Action</span>
                <span className={`font-bold text-right ${side === 'BUY' ? 'text-success' : 'text-danger'}`}>{side} {simulation.quantity}</span>
                
                <span className="text-secondary">Est. Exec. Price</span>
                <span className="text-right">₹{simulation.execution_price.toFixed(2)}</span>
                
                <span className="text-secondary">Gross Amount</span>
                <span className="text-right">₹{simulation.gross_amount.toFixed(2)}</span>
                
                <span className="text-secondary">Total Charges</span>
                <span className="text-right text-danger">₹{simulation.total_charges.toFixed(2)}</span>
                
                <div className="col-span-2 border-b my-1"></div>
                
                <span className="font-bold text-lg">{side === 'BUY' ? 'Total Cost' : 'Net Proceeds'}</span>
                <span className="font-bold text-lg text-right">₹{simulation.net_amount.toFixed(2)}</span>
              </div>
              
              {/* Validation Warnings */}
              {(!simulation.is_market_open || simulation.is_quote_stale) && (
                <div className="p-3 bg-warning-light text-warning text-sm rounded-md d-flex gap-2">
                  <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                  <span>Market is currently closed or quotes are stale. Estimated price may vary significantly from execution price at open.</span>
                </div>
              )}
              
              {side === 'BUY' && simulation.sufficient_funds === false && (
                <div className="p-3 bg-danger-light text-danger text-sm rounded-md d-flex gap-2">
                  <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                  <span>Insufficient virtual funds. Require ₹{simulation.net_amount.toFixed(2)}. Please deposit cash into your portfolio.</span>
                </div>
              )}
              
              {side === 'SELL' && simulation.sufficient_holdings === false && (
                <div className="p-3 bg-danger-light text-danger text-sm rounded-md d-flex gap-2">
                  <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                  <span>Insufficient holdings. You do not own enough quantity of this instrument to sell.</span>
                </div>
              )}
            </div>
          ) : 'Preparing order...'
        }
      />
    </div>
  );
};

export default Trade;
