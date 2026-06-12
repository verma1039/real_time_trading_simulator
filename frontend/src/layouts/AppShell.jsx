import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Briefcase, 
  Eye, 
  ArrowRightLeft, 
  ListOrdered, 
  History, 
  Settings,
  LogOut,
  ShieldAlert,
  Users,
  FileText
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Badge from '../components/Badge';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/portfolio', label: 'Portfolio', icon: Briefcase },
  { path: '/watchlists', label: 'Watchlists', icon: Eye },
  { path: '/trade', label: 'Trade', icon: ArrowRightLeft },
  { path: '/orders', label: 'Orders', icon: ListOrdered },
  { path: '/history', label: 'History', icon: History },
  { path: '/settings', label: 'Settings', icon: Settings },
];

const adminNavItems = [
  { path: '/admin', label: 'Admin Stats', icon: ShieldAlert },
  { path: '/admin/users', label: 'Users', icon: Users },
  { path: '/admin/logs', label: 'Audit Logs', icon: FileText },
];

const AppShell = () => {
  const { logout, user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';

  return (
    <div className="d-flex flex-col md-d-flex flex-row h-screen bg-base">
      
      {/* Desktop Sidebar */}
      <aside className="d-none md-d-flex flex-col w-full max-w-xs bg-surface border-r h-full p-4 overflow-y-auto">
        <div className="d-flex items-center gap-3 mb-8 px-2">
          <div className="bg-primary rounded-md p-2">
            <ArrowRightLeft color="white" size={20} />
          </div>
          <span className="text-lg font-bold text-primary">Antigravity</span>
        </div>

        <nav className="d-flex flex-col gap-2 flex-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) => 
                  `d-flex items-center gap-3 px-4 py-3 rounded-md font-medium transition-default ${
                    isActive ? 'bg-primary text-surface shadow-sm' : 'text-secondary hover-bg'
                  }`
                }
              >
                <Icon size={20} />
                {item.label}
              </NavLink>
            );
          })}

          {isAdmin && (
            <>
              <div className="mt-4 mb-2 px-4 text-xs font-bold text-muted uppercase tracking-wider">
                Admin Section
              </div>
              {adminNavItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === '/admin'}
                    className={({ isActive }) => 
                      `d-flex items-center gap-3 px-4 py-3 rounded-md font-medium transition-default ${
                        isActive ? 'bg-danger text-surface shadow-sm' : 'text-danger hover-bg'
                      }`
                    }
                  >
                    <Icon size={20} />
                    {item.label}
                  </NavLink>
                );
              })}
            </>
          )}
        </nav>

        <div className="mt-auto pt-4 border-t">
          <div className="d-flex items-center gap-3 px-2 mb-4">
            <div className="w-full">
              <p className="text-sm font-bold text-primary">{user?.display_name || 'Trader'}</p>
              <p className="text-xs text-muted">{user?.email}</p>
            </div>
          </div>
          <button 
            onClick={logout}
            className="w-full d-flex items-center gap-3 px-4 py-2 rounded-md text-danger font-medium hover-bg btn-ghost"
          >
            <LogOut size={20} />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 d-flex flex-col h-screen overflow-hidden">
        
        {/* Mobile Header */}
        <header className="d-flex md-d-none items-center justify-between p-4 bg-surface border-b sticky top-0 z-sticky">
          <div className="d-flex items-center gap-2">
            <div className="bg-primary rounded-md p-1.5">
              <ArrowRightLeft color="white" size={16} />
            </div>
            <span className="font-bold text-primary">Antigravity</span>
          </div>
          <div className="d-flex items-center gap-2">
            {isAdmin && <Badge variant="danger">ADMIN</Badge>}
            <NavLink to="/settings" className="p-2 text-secondary hover-bg rounded-md">
              <Settings size={20} />
            </NavLink>
          </div>
        </header>

        {/* Top Header (Desktop) */}
        <header className="d-none md-d-flex items-center justify-between p-4 bg-surface border-b z-sticky">
          <h2 className="text-lg font-semibold text-primary d-flex items-center gap-3">
            Trading Simulator
            {isAdmin && <Badge variant="danger">ADMIN MODE</Badge>}
          </h2>
        </header>

        {/* Scrollable Main Content */}
        <main className="flex-1 overflow-y-auto p-4 md-p-8 bg-base">
          <Outlet />
        </main>

        {/* Mobile Bottom Navigation */}
        <nav className="d-flex md-d-none justify-between items-center bg-surface border-t p-2 z-sticky pb-4">
          {navItems.filter(item => ['/', '/portfolio', '/trade', '/watchlists', '/settings'].includes(item.path)).map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => 
                  `d-flex flex-col items-center gap-1 p-2 flex-1 rounded-md transition-default ${
                    isActive ? 'text-primary' : 'text-muted'
                  }`
                }
              >
                <Icon size={20} />
                <span className="text-xs font-medium">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>
    </div>
  );
};

export default AppShell;
