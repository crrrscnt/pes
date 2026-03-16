import { useState, useEffect } from 'react';
import { adminApi, linucbApi } from '../api/endpoints';
import { Users, Settings, Trash2, Eye, UserCheck} from 'lucide-react';

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<'users' | 'jobs' | 'expert-requests' | 'linucb'>('users');
  const [linucbStats, setLinucbStats] = useState<any[]>([]);
  const [linucbLoading, setLinucbLoading] = useState(false);
  const [expertRequests, setExpertRequests] = useState<any[]>([]);
  const [expertLoading, setExpertLoading] = useState(false);
  const [usersPage, setUsersPage] = useState(1);
  const [jobsPage, setJobsPage] = useState(1);
  const [usersData, setUsersData] = useState<any>(null);
  const [jobsData, setJobsData] = useState<any>(null);
  const [usersLoading, setUsersLoading] = useState(false);
  const [jobsLoading, setJobsLoading] = useState(false);

  const fetchUsers = async () => {
    setUsersLoading(true);
    try {
      const response = await adminApi.listUsers({ page: usersPage, per_page: 10 });
      setUsersData(response.data);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setUsersLoading(false);
    }
  };

  const fetchJobs = async () => {
    setJobsLoading(true);
    try {
      const response = await adminApi.listAllJobs({ page: jobsPage, per_page: 10 });
      setJobsData(response.data);
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
    } finally {
      setJobsLoading(false);
    }
  };

  const fetchExpertRequests = async () => {
    setExpertLoading(true);
    try {
      const response = await adminApi.listExpertRequests();
      setExpertRequests(response.data);
    } catch (error) {
      console.error('Failed to fetch expert requests:', error);
    } finally {
      setExpertLoading(false);
    }
  };

  // Загружаем запросы на роль эксперта сразу при монтировании компонента
  useEffect(() => {
    fetchExpertRequests();
  }, []);

  const fetchLinucb = async () => {
    setLinucbLoading(true);
    try {
      const response = await linucbApi.getArmStats();
      setLinucbStats(response.data);
    } catch (error) {
      console.error('Failed to fetch LinUCB stats:', error);
    } finally {
      setLinucbLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [usersPage]);

  useEffect(() => {
    fetchJobs();
  }, [jobsPage]);

  const handleUserRoleChange = async (userId: string, newRole: 'user' | 'expert' | 'admin') => {
    try {
      await adminApi.updateUser(userId, { role: newRole });
      fetchUsers();
    } catch (error) {
      console.error('Failed to update user role:', error);
      alert('Failed to update user role');
    }
  };

  const handleUserUpdate = async (userId: string, updates: any) => {
    try {
      await adminApi.updateUser(userId, updates);
      fetchUsers();
    } catch (error) {
      console.error('Failed to update user:', error);
    }
  };

  const handleJobDelete = async (jobId: string) => {
    if (window.confirm('Are you sure you want to delete this job?')) {
      try {
        await adminApi.deleteJob(jobId);
        fetchJobs();
      } catch (error) {
        console.error('Failed to delete job:', error);
      }
    }
  };

  const handleExpertRequest = async (userId: string, action: 'approve' | 'reject') => {
    try {
      await adminApi.handleExpertRequest(userId, action);
      fetchExpertRequests();
      await fetchUsers();
    } catch (error) {
      console.error('Failed to handle expert request:', error);
      alert('Failed to process request');
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-purple-100 text-purple-800';
      case 'expert':
        return 'bg-blue-100 text-blue-800';
      case 'user':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Панель админа</h1>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('users')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'users'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
          >
            <Users className="w-4 h-4 inline mr-2" />
            Пользователи
          </button>

          <button
            onClick={() => setActiveTab('jobs')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'jobs'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
          >
            <Settings className="w-4 h-4 inline mr-2" />
            Все задания
          </button>

          <button
            onClick={() => setActiveTab('expert-requests')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'expert-requests'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
          >
            <UserCheck className="w-4 h-4 inline mr-2" />
            Запросы на роль эксперта
            {expertRequests.length > 0 && (
              <span className="ml-2 px-2 py-1 bg-red-500 text-white text-xs rounded-full">
                {expertRequests.length}
              </span>
            )}
          </button>
        </nav>
      </div>

      {/* Expert Requests Tab */}
      {activeTab === 'expert-requests' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Запросы на роль эксперта</h3>
          </div>

          {expertLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="spinner"></div>
              <span className="ml-2 text-gray-600">Загрузка запросов...</span>
            </div>
          ) : expertRequests.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">Нет ожидающих запросов на роль эксперта</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Email
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Дата запроса
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Действия
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {expertRequests.map((req) => (
                    <tr key={req.user_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {req.email}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(req.request_date).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleExpertRequest(req.user_id, 'approve')}
                            className="text-green-600 hover:text-green-900 px-3 py-1 rounded-md hover:bg-green-50 transition"
                          >
                            Одобрить
                          </button>
                          <button
                            onClick={() => handleExpertRequest(req.user_id, 'reject')}
                            className="text-red-600 hover:text-red-900 px-3 py-1 rounded-md hover:bg-red-50 transition"
                          >
                            Отклонить
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Пользователи</h3>
          </div>

          {usersLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="spinner"></div>
              <span className="ml-2 text-gray-600">Загрузка пользователей...</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Email
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Роль
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Статус
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Аккаунт создан
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Действия
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {usersData?.users.map((user) => (
                    <tr key={user.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {user.email}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <select
                          value={user.role}
                          onChange={(e) => handleUserRoleChange(user.id, e.target.value as 'user' | 'expert' | 'admin')}
                          className="form-select text-sm py-1 px-2 rounded-md border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                          style={{
                            minWidth: '120px',
                            backgroundColor: user.role === 'admin' ? '#f3e8ff' : user.role === 'expert' ? '#dbeafe' : '#f9fafb'
                          }}
                        >
                          <option value="user">Пользователь</option>
                          <option value="expert">Эксперт</option>
                          <option value="admin">Админ</option>
                        </select>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs rounded-full ${user.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                          }`}>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <button
                          onClick={() => handleUserUpdate(user.id, {
                            is_active: !user.is_active
                          })}
                          className={`${user.is_active
                            ? 'text-orange-600 hover:text-orange-900'
                            : 'text-green-600 hover:text-green-900'
                            } px-3 py-1 rounded-md hover:bg-gray-100 transition`}
                        >
                          {user.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Jobs Tab */}
      {activeTab === 'jobs' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Все задания</h3>
          </div>

          {jobsLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="spinner"></div>
              <span className="ml-2 text-gray-600">Загрузка заданий...</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Пользователь
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Молекула
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Статус
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Создан
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Действия
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {jobsData?.jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {job.user_id ? `User ${job.user_id.slice(0, 8)}...` : 'Anonymous'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {job.molecule}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`status-badge ${job.status === 'completed' ? 'status-completed' :
                          job.status === 'running' ? 'status-running' :
                            job.status === 'failed' ? 'status-failed' : 'status-queued'
                          }`}>
                          {job.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(job.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => window.open(`/?job=${job.id}`, '_blank')}
                            className="text-blue-600 hover:text-blue-900 flex items-center gap-1 px-3 py-1 rounded-md hover:bg-blue-50 transition"
                          >
                            <Eye className="w-4 h-4" />
                            Просмотр
                          </button>
                          <button
                            onClick={() => handleJobDelete(job.id)}
                            className="text-red-600 hover:text-red-900 flex items-center gap-1 px-3 py-1 rounded-md hover:bg-red-50 transition"
                          >
                            <Trash2 className="w-4 h-4" />
                            Удалить
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}