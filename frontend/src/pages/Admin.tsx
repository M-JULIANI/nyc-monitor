import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { ApiClient } from '@/lib/api';
import { User } from '@/types';

const Admin: React.FC = () => {
  const { user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const api = new ApiClient();

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Fetch users and stats in parallel
        const [usersResponse] = await Promise.all([
          api.get<User[]>('/admin/users'),
        ]);

        if (usersResponse.error) throw new Error(usersResponse.error);

        setUsers(usersResponse.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch admin data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleRoleChange = async (userId: string, newRole: User['role']) => {
    try {
      const response = await api.put<User>(`/admin/users/${userId}/role`, { role: newRole });
      if (response.error) throw new Error(response.error);

      // Update local state
      setUsers(prev => prev.map(u => 
        u.id === userId ? { ...u, role: newRole } : u
      ));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user role');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center bg-zinc-900 h-full">
        <div className="text-white">Loading admin data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-zinc-900">
        <div className="text-white text-center">
          <h1 className="text-2xl font-bold mb-4">Error</h1>
          <p className="text-zinc-300">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full p-4 md:p-8 bg-zinc-900 text-white">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-2xl md:text-3xl font-bold">Admin Dashboard</h1>
          <div className="text-sm text-zinc-300">
            Logged in as: {user?.name} ({user?.role})
          </div>
        </div>

        {/* User Management */}
        <div className="card mb-8">
          <h2 className="text-xl font-semibold mb-4">User Management</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left border-b border-zinc-700">
                  <th className="pb-2">Name</th>
                  <th className="pb-2">Email</th>
                  <th className="pb-2">Role</th>
                  <th className="pb-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id} className="border-b border-zinc-800">
                    <td className="py-3">{user.name}</td>
                    <td className="py-3">{user.email}</td>
                    <td className="py-3">
                      <select
                        value={user.role}
                        onChange={(e) => handleRoleChange(user.id, e.target.value as User['role'])}
                        className="bg-zinc-700 text-white px-2 py-1 rounded text-sm"
                      >
                        <option value="admin">Admin</option>
                        <option value="judge">Judge</option>
                        <option value="viewer">Viewer</option>
                      </select>
                    </td>
                    <td className="py-3">
                      <button
                        onClick={() => {/* TODO: Implement user actions */}}
                        className="text-sm text-zinc-300 hover:text-white"
                      >
                        More actions
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Admin; 