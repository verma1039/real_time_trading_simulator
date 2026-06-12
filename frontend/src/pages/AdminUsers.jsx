import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '../api/client';
import PageHeader from '../components/PageHeader';
import DataTable from '../components/DataTable';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import SearchInput from '../components/SearchInput';
import Badge from '../components/Badge';
import { Users, Eye } from 'lucide-react';

const AdminUsers = () => {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 15;
  const navigate = useNavigate();

  const fetchUsers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await client.get('/admin/users');
      setUsers(res.data);
    } catch (err) {
      setError(err.message || 'Failed to fetch users');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const filteredUsers = users.filter(u => 
    u.email.toLowerCase().includes(searchQuery.toLowerCase()) || 
    (u.display_name && u.display_name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const totalPages = Math.ceil(filteredUsers.length / ITEMS_PER_PAGE);
  const paginatedUsers = filteredUsers.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  const columns = [
    { header: 'Email', accessor: 'email' },
    { header: 'Name', render: (row) => row.display_name || '-' },
    { header: 'Role', render: (row) => (
      <Badge variant={row.role === 'ADMIN' ? 'danger' : 'secondary'}>{row.role}</Badge>
    )},
    { header: 'Status', render: (row) => (
      row.is_suspended ? <Badge variant="danger">Suspended</Badge> : <Badge variant="success">Active</Badge>
    )},
    { header: 'Joined', render: (row) => new Date(row.created_at).toLocaleDateString() },
    { header: 'Actions', render: (row) => (
      <button 
        onClick={() => navigate(`/admin/users/${row.id}`)}
        className="btn btn-sm btn-secondary d-flex items-center gap-1"
      >
        <Eye size={14} /> Inspect
      </button>
    ), align: 'right' }
  ];

  if (isLoading) return <LoadingState message="Loading users..." />;
  if (error) return <ErrorState message={error} retryAction={fetchUsers} />;

  return (
    <div className="d-flex flex-col gap-6">
      <PageHeader 
        title="User Management" 
        subtitle="Search and inspect platform users." 
      />

      <div className="card">
        <div className="card-header border-b d-flex flex-col md-d-flex flex-row justify-between items-start md-items-center gap-4">
          <h3 className="text-md font-bold d-flex items-center gap-2"><Users size={18} /> Directory</h3>
          <div className="w-full md-w-auto">
            <SearchInput 
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
              placeholder="Search by name or email..."
            />
          </div>
        </div>
        <DataTable 
          columns={columns} 
          data={paginatedUsers} 
          isLoading={false}
          emptyStateProps={{
            title: 'No users found',
            message: 'Try adjusting your search query.',
            icon: Users
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

export default AdminUsers;
