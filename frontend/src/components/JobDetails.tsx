import { useState, type ChangeEvent } from 'react';
import { useJobStatus } from '../hooks/useJobStatus';
import { useAuth } from '../hooks/useAuth';
import { jobsApi } from '../api/endpoints';
import { Download, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface JobDetailsProps {
  jobId: string | null;
  isPublic?: boolean;
}

export default function JobDetails({ jobId, isPublic = false }: JobDetailsProps) {
  const { user } = useAuth();
  const { job, loading, error, setJob } = useJobStatus(jobId, { isPublic });
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const isOwner = Boolean(user && job?.user_id === user.id);
  const canUploadCover = isOwner && job?.status === 'completed';

  const handleCoverChange = (event: ChangeEvent<HTMLInputElement>) => {
    setUploadError(null);
    setUploadSuccess(null);
    const file = event.target.files?.[0] ?? null;
    if (!file) {
      setCoverFile(null);
      return;
    }

    if (file.size > 2 * 1024 * 1024) {
      setUploadError('Файл слишком большой. Максимум 2 МБ.');
      setCoverFile(null);
      return;
    }

    setCoverFile(file);
  };

  const resizeImageFile = async (file: File, maxWidth = 1200, maxHeight = 800): Promise<File> => {
    return new Promise((resolve, reject) => {
      const image = new Image();
      const objectUrl = URL.createObjectURL(file);

      image.onload = async () => {
        URL.revokeObjectURL(objectUrl);
        const ratio = Math.min(maxWidth / image.width, maxHeight / image.height, 1);
        const width = Math.round(image.width * ratio);
        const height = Math.round(image.height * ratio);

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          reject(new Error('Canvas context unavailable'));
          return;
        }
        ctx.drawImage(image, 0, 0, width, height);

        canvas.toBlob((blob) => {
          if (!blob) {
            reject(new Error('Image resize failed'));
            return;
          }

          resolve(new File([blob], file.name, { type: file.type }));
        }, file.type || 'image/png');
      };

      image.onerror = (e) => {
        URL.revokeObjectURL(objectUrl);
        reject(new Error('Failed to load image for resizing'));
      };

      image.src = objectUrl;
    });
  };

  const handleUploadCover = async () => {
    if (!job || !coverFile) return;

    setUploadError(null);
    setUploadSuccess(null);
    setUploading(true);

    try {
      const resizedFile = await resizeImageFile(coverFile, 1200, 800);
      const formData = new FormData();
      formData.append('image', resizedFile);
      const response = await jobsApi.uploadPreview(job.id, formData);
      setJob(response.data);
      setCoverFile(null);
      setUploadSuccess('Обложка успешно загружена.');
    } catch (err: any) {
      console.error(err);
      setUploadError(err?.response?.data?.detail || err?.message || 'Не удалось загрузить обложку.');
    } finally {
      setUploading(false);
    }
  };

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

      {/* ── Обложка задания ── */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="font-medium text-gray-900 mb-3">Обложка</h3>

        {job.preview_image ? (
          <div className="space-y-3">
            <img
              src={job.preview_image}
              alt="Job cover"
              className="w-full rounded-lg object-contain max-h-80"
              style={{ maxWidth: '100%', maxHeight: '320px' }}
            />
            <p className="text-sm text-gray-600">Эта обложка отображается в галерее и карточках задания.</p>
          </div>
        ) : (
          <div className="text-sm text-gray-500">
            <p>Пока что обложка не загружена.</p>
            <p className="mt-1">Загрузите изображение после завершения расчёта, чтобы оно появилось в галерее.</p>
          </div>
        )}

        {canUploadCover && (
          <div className="mt-4 space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Выберите файл обложки
              </label>
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={(e: ChangeEvent<HTMLInputElement>) => handleCoverChange(e)}
                className="w-full text-sm text-gray-700"
              />
            </div>
            {uploadError && <p className="text-sm text-red-600">{uploadError}</p>}
            {uploadSuccess && <p className="text-sm text-green-600">{uploadSuccess}</p>}
            <button
              type="button"
              onClick={handleUploadCover}
              disabled={!coverFile || uploading}
              className="btn btn-primary w-full"
            >
              {uploading ? 'Загружаем...' : 'Загрузить обложку'}
            </button>
          </div>
        )}
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
