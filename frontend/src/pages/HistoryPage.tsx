import { useState } from 'react';
import { useJobHistory } from '../hooks/useJobHistory';
import { Link } from 'react-router-dom';
import { Eye, Download, Calendar, FlaskConical } from 'lucide-react';

export default function HistoryPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [moleculeFilter, setMoleculeFilter] = useState<string>('');

  const { jobs, total, loading, error } = useJobHistory({
    page,
    perPage: 10,
    statusFilter: statusFilter || undefined,
    moleculeFilter: moleculeFilter || undefined,
  });

  const totalPages = Math.ceil(total / 10);

  const getStatusBadge = (status: string) => {
    const statusClasses = {
      queued: 'status-queued',
      running: 'status-running',
      completed: 'status-completed',
      failed: 'status-failed',
    };
    return `status-badge ${statusClasses[status as keyof typeof statusClasses] || ''}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="spinner"></div>
        <span className="ml-2 text-gray-600">Загрузка истории...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Ошибка</h1>
        <p className="text-gray-600">{error}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">История заданий</h1>
        <Link to="/" className="btn btn-primary">
          Новый скан
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="status-filter" className="form-label">
              Статус
            </label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="form-select"
            >
              <option value="">Все статусы</option>
              <option value="queued">В очереди</option>
              <option value="running">Выполняется</option>
              <option value="completed">Завершено</option>
              <option value="failed">Ошибка</option>
            </select>
          </div>

          <div>
            <label htmlFor="molecule-filter" className="form-label">
              Молекула
            </label>
            <select
              id="molecule-filter"
              value={moleculeFilter}
              onChange={(e) => setMoleculeFilter(e.target.value)}
              className="form-select"
            >
              <option value="">Все молекулы</option>
              <option value="H2">H₂</option>
              <option value="LiH">LiH</option>
              <option value="BH">BH</option>
              <option value="BeH">BeH</option>
              <option value="CH">CH</option>
              <option value="NH">NH</option>
              <option value="OH">OH</option>
              <option value="FH">FH</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => {
                setStatusFilter('');
                setMoleculeFilter('');
                setPage(1);
              }}
              className="btn btn-secondary w-full"
            >
              Очистить
            </button>
          </div>
        </div>
      </div>

      {/* Jobs Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {jobs.length === 0 ? (
          <div className="text-center py-12">
            <FlaskConical className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Задания не найдены</h3>
            <p className="text-gray-600">
              {statusFilter || moleculeFilter
                ? 'No jobs match your current filters.'
                : 'You haven\'t run any PES scans yet.'}
            </p>
            <Link to="/" className="btn btn-primary mt-4">
              Начать первый скан
            </Link>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Молекула
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Параметры
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Статус
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Создано
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Действия
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <FlaskConical className="w-5 h-5 text-gray-400 mr-2" />
                          <span className="text-sm font-medium text-gray-900">
                            {job.molecule}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div>
                          <div>Оптимизатор: {job.optimizer}</div>
                          <div>Мэппер: {job.mapper}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={getStatusBadge(job.status)}>
                          {job.status}
                        </span>
                        {job.progress > 0 && job.status === 'running' && (
                          <div className="mt-1 text-xs text-gray-500">
                            {job.progress}%
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div className="flex items-center">
                          <Calendar className="w-4 h-4 mr-1" />
                          {formatDate(job.created_at)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <div className="flex items-center gap-2">
                          <Link
                            to={`/?job=${job.id}`}
                            className="text-blue-600 hover:text-blue-900 flex items-center gap-1"
                          >
                            <Eye className="w-4 h-4" />
                            Просмотр
                          </Link>
                          {job.status === 'completed' && job.results && (
                            <button
                              onClick={() => {
                                const dataStr = JSON.stringify(job.results, null, 2);
                                const dataBlob = new Blob([dataStr], { type: 'application/json' });
                                const url = URL.createObjectURL(dataBlob);
                                const link = document.createElement('a');
                                link.href = url;
                                link.download = `pes-scan-${job.molecule}-${job.id}.json`;
                                link.click();
                                URL.revokeObjectURL(url);
                              }}
                              className="text-green-600 hover:text-green-900 flex items-center gap-1"
                            >
                              <Download className="w-4 h-4" />
                              Скачать
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
                <div className="flex-1 flex justify-between sm:hidden">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="btn btn-secondary"
                  >
                    Предыдущая
                  </button>
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page === totalPages}
                    className="btn btn-secondary"
                  >
                    Следующая
                  </button>
                </div>
                <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm text-gray-700">
                      Показаны от {' '}
                      <span className="font-medium">{(page - 1) * 10 + 1}</span>
                      {' '}до{' '}
                      <span className="font-medium">
                        {Math.min(page * 10, total)}
                      </span>
                      {' '}из{' '}
                      <span className="font-medium">{total}</span>
                      {' '}результатов
                    </p>
                  </div>
                  <div>
                    <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                      <button
                        onClick={() => setPage(Math.max(1, page - 1))}
                        disabled={page === 1}
                        className="btn btn-secondary"
                      >
                        Предыдущая
                      </button>
                      <button
                        onClick={() => setPage(Math.min(totalPages, page + 1))}
                        disabled={page === totalPages}
                        className="btn btn-secondary"
                      >
                        Следующая
                      </button>
                    </nav>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
