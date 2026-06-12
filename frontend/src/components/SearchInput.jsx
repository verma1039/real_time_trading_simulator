import React from 'react';
import { Search } from 'lucide-react';

const SearchInput = ({ value, onChange, placeholder = 'Search...' }) => (
  <div className="w-full relative">
    <div className="d-flex items-center absolute" style={{ left: '12px', top: '50%', transform: 'translateY(-50%)' }}>
      <Search size={16} className="text-muted" />
    </div>
    <input
      type="text"
      className="input"
      style={{ paddingLeft: '36px' }}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
    />
  </div>
);

export default SearchInput;
