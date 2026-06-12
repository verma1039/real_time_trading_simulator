import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { client } from '../api/client';
import PageHeader from '../components/PageHeader';
import ConfirmModal from '../components/ConfirmModal';
import { User, Shield, LogOut, Key } from 'lucide-react';
import toast from 'react-hot-toast';

const Settings = () => {
  const { user, logout } = useAuth();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);

  const [isLogoutAllModalOpen, setIsLogoutAllModalOpen] = useState(false);
  const [isLoggingOutAll, setIsLoggingOutAll] = useState(false);

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      return toast.error('New passwords do not match.');
    }
    if (newPassword.length < 8) {
      return toast.error('Password must be at least 8 characters long.');
    }

    setIsChangingPassword(true);
    try {
      await client.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      toast.success('Password changed successfully. Please log in again.');
      setIsPasswordModalOpen(false);
      // The backend invalidates all sessions, so the next API call will 401 and redirect to login,
      // but we can proactively log out here to be clean.
      setTimeout(() => {
        logout();
      }, 2000);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to change password.');
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleLogoutAll = async () => {
    setIsLoggingOutAll(true);
    try {
      await client.post('/auth/logout-all');
      toast.success('All sessions revoked. Logging out...');
      setTimeout(() => {
        logout();
      }, 1500);
    } catch (err) {
      toast.error('Failed to revoke sessions.');
    } finally {
      setIsLoggingOutAll(false);
    }
  };

  return (
    <div className="d-flex flex-col gap-6 max-w-4xl mx-auto">
      <PageHeader 
        title="Settings" 
        subtitle="Manage your profile, security, and preferences." 
      />

      {/* Profile Section */}
      <div className="card">
        <div className="card-header border-b">
          <h3 className="text-md font-bold d-flex items-center gap-2"><User size={18} /> Profile</h3>
        </div>
        <div className="card-body">
          <div className="d-flex flex-col gap-4">
            <div>
              <label className="text-sm font-medium text-secondary mb-1 d-block">Full Name</label>
              <div className="p-3 bg-base-alt rounded-md border">{user?.display_name || 'N/A'}</div>
            </div>
            <div>
              <label className="text-sm font-medium text-secondary mb-1 d-block">Email Address</label>
              <div className="p-3 bg-base-alt rounded-md border">{user?.email || 'N/A'}</div>
            </div>
            <p className="text-xs text-secondary mt-2">Profile editing is currently disabled in the simulator.</p>
          </div>
        </div>
      </div>

      {/* Security Section */}
      <div className="card">
        <div className="card-header border-b">
          <h3 className="text-md font-bold d-flex items-center gap-2"><Shield size={18} /> Security</h3>
        </div>
        <div className="card-body d-flex flex-col gap-6">
          
          <div className="d-flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b pb-6">
            <div>
              <h4 className="font-bold mb-1">Change Password</h4>
              <p className="text-sm text-secondary">Update your password to keep your account secure. This will log you out of all devices.</p>
            </div>
            <button className="btn btn-outline d-flex items-center gap-2 whitespace-nowrap" onClick={() => setIsPasswordModalOpen(true)}>
              <Key size={16} /> Update Password
            </button>
          </div>

          <div className="d-flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h4 className="font-bold mb-1">Active Sessions</h4>
              <p className="text-sm text-secondary">Revoke access from all other devices and browsers immediately.</p>
            </div>
            <button className="btn btn-outline text-warning border-warning hover-bg whitespace-nowrap" onClick={() => setIsLogoutAllModalOpen(true)}>
              Revoke All Sessions
            </button>
          </div>

        </div>
      </div>

      {/* Account Section */}
      <div className="card border-danger-light mb-8">
        <div className="card-header border-b border-danger-light bg-danger-light text-danger">
          <h3 className="text-md font-bold d-flex items-center gap-2"><LogOut size={18} /> Account Actions</h3>
        </div>
        <div className="card-body d-flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <p className="text-sm text-secondary">Log out of your current session on this device.</p>
          <button className="btn btn-danger d-flex items-center gap-2 whitespace-nowrap" onClick={logout}>
            <LogOut size={16} /> Logout
          </button>
        </div>
      </div>

      {/* Change Password Modal */}
      <ConfirmModal 
        isOpen={isPasswordModalOpen}
        onClose={() => {
          setIsPasswordModalOpen(false);
          setCurrentPassword('');
          setNewPassword('');
          setConfirmPassword('');
        }}
        onConfirm={handleChangePassword}
        title="Change Password"
        confirmText="Update Password"
        confirmVariant="primary"
        isLoading={isChangingPassword}
        message={
          <div className="d-flex flex-col gap-4 mt-2">
            <input 
              type="password" 
              placeholder="Current Password" 
              className="input w-full" 
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
            <input 
              type="password" 
              placeholder="New Password (min 8 chars)" 
              className="input w-full" 
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <input 
              type="password" 
              placeholder="Confirm New Password" 
              className="input w-full" 
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>
        }
      />

      {/* Logout All Sessions Modal */}
      <ConfirmModal 
        isOpen={isLogoutAllModalOpen}
        onClose={() => setIsLogoutAllModalOpen(false)}
        onConfirm={handleLogoutAll}
        title="Revoke All Sessions"
        message="Are you sure you want to log out of all devices? You will need to sign in again everywhere."
        confirmText="Revoke Access"
        confirmVariant="warning"
        isLoading={isLoggingOutAll}
      />

    </div>
  );
};

export default Settings;
