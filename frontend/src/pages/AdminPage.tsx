import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { adminApi, linucbApi, authApi } from '../api/endpoints';
import { Users, Settings, Trash2, Eye, UserCheck, BarChart3 } from 'lucide-react';
import type {
  User,
  Job,
  ExpertRequest,
  LinUCBArmStats,
  UserListResponse,
  JobListResponse,
} from '../types';

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<'users' | 'jobs' | 'expert-requests' | 'linucb'>('users');

  // Expert requests
  const [expertRequests, setExpertRequests] = useState<ExpertRequest[]>([]);
  const [expertLoading, setExpertLoading] = useState(false);

  // Users
  const [usersPage, setUsersPage] = useState(1);
  const [usersData, setUsersData] = useState<UserListResponse | null>(null);
  const [usersLoading, setUsersLoading] = useState(false);

  // Jobs
  const [jobsPage, setJobsPage] = useState(1);
  const [jobsData, setJobsData] = useState<JobListResponse | null>(null);
  const [jobsLoading, setJobsLoading] = useState(false);

  // LinUCB FOR FUTURE USE
  // const [linucbStats, setLinucbStats] = useState<LinUCBArmStats[]>([]);
  // const [linucbLoading, setLinucbLoading] = useState(false);

  // Current user (to prevent self-deactivation / self-role-change)
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  // Fetch current user once on mount
  useEffect(() => {
    authApi
      .me()
      .then((res) => setCurrentUser(res.data))
      .catch((err) => console.error('Failed to fetch current user:', err));
  }, []);

  const fetchExpertRequests = useCallback(async () => {
    setExpertLoading(true);
    try {
      const response = await adminApi.listExpertRequests();
      setExpertRequests(response.data);
    } catch (error) {
      console.error('Failed to fetch expert requests:', error);
    } finally {
      setExpertLoading(false);
    }
  }, []);

  const fetchUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const response = await adminApi.listUsers({ page: usersPage, per_page: 10 });
      setUsersData(response.data);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setUsersLoading(false);
    }
  }, [usersPage]);

  const fetchJobs = useCallback(async () => {
    setJobsLoading(true);
    try {
      const response = await adminApi.listAllJobs({ page: jobsPage, per_page: 10 });
      setJobsData(response.data);
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
    } finally {
      setJobsLoading(false);
    }
  }, [jobsPage]);

  // linucb FOR FUTURE USE
  // const fetchLinucb = useCallback(async () => {
  //   setLinucbLoading(true);
  //   try {
  //     const response = await linucbApi.getArmStats();
  //     setLinucbStats(response.data);
  //   } catch (error) {
  //     console.error('Failed to fetch LinUCB stats:', error);
  //   } finally {
  //     setLinucbLoading(false);
  //   }
  // }, []);

  // Load expert requests once on mount
  useEffect(() => {
    fetchExpertRequests();
  }, [fetchExpertRequests]);

  // Refresh data when entering specific tabs or changing pages
  useEffect(() => {
    if (activeTab === 'users') fetchUsers();
  }, [activeTab, fetchUsers]);

  useEffect(() => {
    if (activeTab === 'jobs') fetchJobs();
  }, [activeTab, fetchJobs]);

  // linucb FOR FUTURE USE
  // useEffect(() => {
  //   if (activeTab === 'linucb') fetchLinucb();
  // }, [activeTab, fetchLinucb]);

  const handleUserRoleChange = useCallback(
    async (userId: string, newRole: 'user' | 'expert' | 'admin') => {
      try {
        await adminApi.updateUser(userId, { role: newRole });
        fetchUsers();
      } catch (error) {
        console.error('Failed to update user role:', error);
      }
    },
    [fetchUsers]
  );

  const handleUserUpdate = useCallback(
    async (userId: string, updates: Partial<User>) => {
      try {
        await adminApi.updateUser(userId, updates);
        fetchUsers();
      } catch (error) {
        console.error('Failed to update user:', error);
      }
    },
    [fetchUsers]
  );

  const handleJobDelete = useCallback(
    async (jobId: string) => {
      if (window.confirm('Are you sure you want to delete this job?')) {
        try {
          await adminApi.deleteJob(jobId);
          fetchJobs();
        } catch (error) {
          console.error('Failed to delete job:', error);
        }
      }
    },
    [fetchJobs]
  );

  const handleExpertRequest = useCallback(
    async (userId: string, action: 'approve' | 'reject') => {
      try {
        await adminApi.handleExpertRequest(userId, action);
        fetchExpertRequests();
        await fetchUsers();
      } catch (error) {
        console.error('Failed to handle expert request:', error);
        alert('Failed to process request');
      }
    },
    [fetchExpertRequests, fetchUsers]
  );

  const usersTotalPages = usersData ? Math.ceil(usersData.total / usersData.per_page) : 1;
  const jobsTotalPages = jobsData ? Math.ceil(jobsData.total / jobsData.per_page) : 1;

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
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'users'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Users className="w-4 h-4 inline mr-2" />
            Пользователи
          </button>

          <button
            onClick={() => setActiveTab('jobs')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'jobs'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Settings className="w-4 h-4 inline mr-2" />
            Все задания
          </button>

          <button
            onClick={() => setActiveTab('expert-requests')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'expert-requests'
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

            {/*linucb FOR FUTURE USE*/}
          {/* <button
            onClick={() => setActiveTab('linucb')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'linucb'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <BarChart3 className="w-4 h-4 inline mr-2" />
            LinUCB
          </button> */}
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
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Email
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Дата запроса
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
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
          ) : !usersData || usersData.users.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">Пользователи не найдены</p>
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
                  {usersData.users.map((user) => {
                    const isSelf = user.id === currentUser?.id;
                    return (
                      <tr key={user.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {user.email}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <select
                            value={user.role}
                            onChange={(e) =>
                              handleUserRoleChange(user.id, e.target.value as 'user' | 'expert' | 'admin')
                            }
                            disabled={isSelf}
                            className="form-select text-sm py-1 px-2 rounded-md border-gray-300 focus:border-blue-500 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                            style={{
                              minWidth: '120px',
                              backgroundColor:
                                user.role === 'admin'
                                  ? '#f3e8ff'
                                  : user.role === 'expert'
                                    ? '#dbeafe'
                                    : '#f9fafb',
                            }}
                          >
                            <option value="user">Пользователь</option>
                            <option value="expert">Эксперт</option>
                            <option value="admin">Админ</option>
                          </select>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`px-2 py-1 text-xs rounded-full ${
                              user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {user.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(user.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <button
                            onClick={() => handleUserUpdate(user.id, { is_active: !user.is_active })}
                            disabled={isSelf}
                            title={isSelf ? 'Вы не можете деактивировать собственный аккаунт' : undefined}
                            className={`px-3 py-1 rounded-md transition ${
                              isSelf
                                ? 'text-gray-400 bg-gray-100 cursor-not-allowed'
                                : user.is_active
                                  ? 'text-orange-600 hover:text-orange-900 hover:bg-orange-50'
                                  : 'text-green-600 hover:text-green-900 hover:bg-green-50'
                            }`}
                          >
                            {user.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Users Pagination */}
          {usersData && usersTotalPages > 1 && (
            <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
              <button
                onClick={() => setUsersPage((p) => Math.max(1, p - 1))}
                disabled={usersPage === 1}
                className="px-3 py-1 rounded-md border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Предыдущая
              </button>
              <span className="text-sm text-gray-700">
                Страница {usersPage} из {usersTotalPages}
              </span>
              <button
                onClick={() => setUsersPage((p) => Math.min(usersTotalPages, p + 1))}
                disabled={usersPage >= usersTotalPages}
                className="px-3 py-1 rounded-md border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Следующая
              </button>
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
          ) : !jobsData || jobsData.jobs.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">Задания не найдены</p>
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
                  {jobsData.jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {job.user_id ? `User ${job.user_id.slice(0, 8)}...` : 'Anonymous'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {job.molecule}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`status-badge ${
                            job.status === 'completed'
                              ? 'status-completed'
                              : job.status === 'running'
                                ? 'status-running'
                                : job.status === 'failed'
                                  ? 'status-failed'
                                  : 'status-queued'
                          }`}
                        >
                          {job.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(job.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex items-center gap-2">
                          <Link
                            to={`/scan?job=${job.id}`}
                            className="text-blue-600 hover:text-blue-900 flex items-center gap-1 px-3 py-1 rounded-md hover:bg-blue-50 transition"
                          >
                            <Eye className="w-4 h-4" />
                            Просмотр
                          </Link>
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

          {/* Jobs Pagination */}
          {jobsData && jobsTotalPages > 1 && (
            <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
              <button
                onClick={() => setJobsPage((p) => Math.max(1, p - 1))}
                disabled={jobsPage === 1}
                className="px-3 py-1 rounded-md border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Предыдущая
              </button>
              <span className="text-sm text-gray-700">
                Страница {jobsPage} из {jobsTotalPages}
              </span>
              <button
                onClick={() => setJobsPage((p) => Math.min(jobsTotalPages, p + 1))}
                disabled={jobsPage >= jobsTotalPages}
                className="px-3 py-1 rounded-md border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Следующая
              </button>
            </div>
          )}
        </div>
      )}

      {/* LinUCB Tab FOR FUTURE USE*/}
      {/* {activeTab === 'linucb' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">LinUCB статистика</h3>
          </div>

          {linucbLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="spinner"></div>
              <span className="ml-2 text-gray-600">Загрузка статистики...</span>
            </div>
          ) : linucbStats.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">Нет данных по рукам LinUCB</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Arm ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Mapper
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Optimizer
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Pulls
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Avg Reward
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {linucbStats.map((stat) => (
                    <tr key={stat.arm_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {stat.arm_id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{stat.mapper}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{stat.optimizer}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{stat.n_pulls}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {stat.avg_reward !== null ? stat.avg_reward.toFixed(4) : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>}
      )*/}
    </div>
  );
}