import { useJobStatus } from '../hooks/useJobStatus';
import { Download, Clock, CheckCircle, XCircle, AlertCircle,  RefreshCw } from 'lucide-react';

interface JobDetailsProps {
  jobId: string | null;
  isPublic?: boolean;
}

export default function JobDetails({ jobId, isPublic = false }: JobDetailsProps) {
  const { job, loading, error } = useJobStatus(jobId, { isPublic });

  if (!jobId) return (
    <div className="text-center py-8">
      <p className="text-gray-500">Задание не выбрано</p>
      <p className="text-sm text-gray-400 mt-1">Начните сканирование PES, чтобы увидеть результаты</p>
    </div>
  );

  if (loading) return (
    <div className="flex items-center justify-center py-8">
      <div className="spinner" />
      <span className="ml-2 text-gray-600">Загрузка...</span>
    </div>
  );

  if (error) return (
    <div className="text-center py-8">
      <XCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
      <p className="text-red-600 mb-1">Ошибка загрузки</p>
      <p className="text-sm text-gray-500">{error}</p>
    </div>
  );

  if (!job) return (
    <div className="text-center py-8"><p className="text-gray-500">Задание не найдено</p></div>
  );

  const statusIcon = (s: string) => {
    switch (s) {
      case 'queued':    return <Clock className="w-4 h-4" />;
      case 'running':   return <div className="spinner w-4 h-4" />;
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':    return <XCircle className="w-4 h-4 text-red-500" />;
      default:          return <AlertCircle className="w-4 h-4" />;
    }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case 'queued':    return 'text-yellow-600 bg-yellow-50';
      case 'running':   return 'text-blue-600 bg-blue-50';
      case 'completed': return 'text-green-600 bg-green-50';
      case 'failed':    return 'text-red-600 bg-red-50';
      default:          return 'text-gray-600 bg-gray-50';
    }
  };

  const fmt = (s: string) => new Date(s).toLocaleString();

  const downloadResults = () => {
    if (!job.results) return;
    const blob = new Blob([JSON.stringify(job.results, null, 2)],
                          { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `pes-${job.molecule}-${job.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const meta         = job.job_metadata;
  const roundHistory = meta?.round_history as any[] | undefined;
  const finalErrHa   = meta?.final_avg_error_ha as number | undefined;
  const roundsDone   = meta?.rounds_completed as number | undefined;

  return (
    <div className="space-y-4">
      {/* ── Информация о задании ── */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="font-medium text-gray-900 mb-3">Информация</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Молекула:</span>
            <span className="font-medium">{job.molecule}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Оптимизатор:</span>
            <span className="font-medium">
              {job.optimizer === 'linucb_pending' ? 'выбирается…' : job.optimizer}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Мэппер:</span>
            <span className="font-medium">
              {job.mapper === 'linucb_pending' ? 'выбирается…' : job.mapper}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Создано:</span>
            <span className="font-medium">{fmt(job.created_at)}</span>
          </div>
        </div>
      </div>

      {/* ── Статус ── */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="font-medium text-gray-900 mb-3">Статус</h3>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {statusIcon(job.status)}
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor(job.status)}`}>
              {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
            </span>
          </div>
          {job.progress > 0 && (
            <span className="text-sm text-gray-600">{job.progress}%</span>
          )}
        </div>

        {job.status === 'running' && job.progress > 0 && (
          <div className="mt-3">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                   style={{ width: `${job.progress}%` }} />
            </div>
          </div>
        )}

        {job.status === 'failed' && job.error_message && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{job.error_message}</p>
          </div>
        )}

        {job.started_at && (
          <div className="mt-3 text-sm text-gray-600 space-y-1">
            <div className="flex justify-between">
              <span>Начато:</span><span>{fmt(job.started_at)}</span>
            </div>
            {job.completed_at && (
              <div className="flex justify-between">
                <span>Завершено:</span><span>{fmt(job.completed_at)}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── LinUCB: многораундовая история ── */}
      {job.use_linucb && job.status !== 'queued' && (
        <div className="bg-violet-50 border border-violet-200 rounded-lg p-4">
          <h3 className="font-medium text-violet-900 mb-3 flex items-center gap-2">
            LinUCB — авто-выбор метода
          </h3>

          {/* Текущий выбор */}
          {job.mapper && job.mapper !== 'linucb_pending' ? (
            <div className="space-y-1 text-sm mb-3">
              <div className="flex justify-between">
                <span className="text-violet-700">Финальный маппер:</span>
                <span className="font-medium text-violet-900">{job.mapper}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-violet-700">Финальный оптимизатор:</span>
                <span className="font-medium text-violet-900">{job.optimizer}</span>
              </div>
              {job.linucb_arm_id && (
                <div className="flex justify-between">
                  <span className="text-violet-700">Рука бандита:</span>
                  <span className="font-mono text-xs text-violet-800">{job.linucb_arm_id}</span>
                </div>
              )}
            </div>
          ) : (
            <p className="text-violet-600 text-xs mb-3">⏳ LinUCB выбирает метод…</p>
          )}

          {/* История раундов */}
          {roundHistory && roundHistory.length > 0 && (
            <div className="mt-2">
              <p className="text-xs font-medium text-violet-800 mb-2 flex items-center gap-1">
                <RefreshCw className="w-3 h-3" />
                Раунды ({roundsDone} из 3)
              </p>
              <div className="space-y-2">
                {roundHistory.map((r: any) => {
                  const errMHa = r.avg_error_ha != null
                    ? (r.avg_error_ha * 1000).toFixed(2) : '—';
                  const isGood = r.avg_error_ha != null && r.avg_error_ha < 0.005;
                  return (
                    <div key={r.round}
                         className="bg-white rounded border border-violet-100 p-2 text-xs">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-medium text-violet-900">
                          Раунд {r.round}
                        </span>
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                          isGood
                            ? 'bg-green-100 text-green-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}>
                          {isGood ? '✓ OK' : '↻ улучшаем'}
                        </span>
                      </div>
                      <div className="text-gray-600 space-y-0.5">
                        <div className="flex justify-between">
                          <span>{r.mapper} / {r.optimizer}</span>
                          <span className={isGood ? 'text-green-600 font-medium' : 'text-orange-600'}>
                            Δ={errMHa} мHa
                          </span>
                        </div>
                        <div className="flex justify-between text-gray-400">
                          <span>Точек: {r.n_points}</span>
                          <span>r={r.reward}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Финальная ошибка */}
              {finalErrHa != null && job.status === 'completed' && (
                <div className="mt-2 pt-2 border-t border-violet-200">
                  <div className="flex justify-between text-xs">
                    <span className="text-violet-700 font-medium">Итоговая ошибка:</span>
                    <span className={`font-bold ${
                      finalErrHa < 0.005 ? 'text-green-600' : 'text-orange-600'
                    }`}>
                      {(finalErrHa * 1000).toFixed(3)} мHa
                      {finalErrHa < 0.005 ? ' ✓' : ''}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Сводка результатов ── */}
      {job.status === 'completed' && meta && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 mb-3">Сводка</h3>
          <div className="space-y-2 text-sm">
            {meta.min_distance != null && (
              <div className="flex justify-between">
                <span className="text-gray-600">Min расстояние:</span>
                <span className="font-medium">{Number(meta.min_distance).toFixed(4)} Å</span>
              </div>
            )}
            {meta.total_points != null && (
              <div className="flex justify-between">
                <span className="text-gray-600">Точек:</span>
                <span className="font-medium">
                  {meta.successful_points}/{meta.total_points}
                </span>
              </div>
            )}
            {meta.elapsed_time != null && (
              <div className="flex justify-between">
                <span className="text-gray-600">Время:</span>
                <span className="font-medium">{Number(meta.elapsed_time).toFixed(1)}s</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Скачать ── */}
      {job.status === 'completed' && job.results && (
        <button onClick={downloadResults}
                className="btn btn-secondary w-full flex items-center justify-center gap-2">
          <Download className="w-4 h-4" />
          Скачать JSON
        </button>
      )}
    </div>
  );
}
