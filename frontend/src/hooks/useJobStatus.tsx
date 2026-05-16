import { useState, useEffect, useRef, useCallback } from 'react';
import { jobsApi, publicApi } from '../api/endpoints';
import type { Job, PartialResult } from '../types';

interface UseJobStatusOptions {
  isPublic?: boolean;
}

type JobStatus = Job['status'];

const FINAL_STATUSES: JobStatus[] = ['completed', 'failed'];

export function useJobStatus(jobId: string | null, options: UseJobStatusOptions = {}) {
  const { isPublic = false } = options;
  const [job, setJob] = useState<Job | null>(null);
  const [partialResults, setPartialResults] = useState<PartialResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const staleRef = useRef(false);

  // Cleanup SSE on unmount or jobId change
  const closeEventSource = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setPartialResults([]);
      setError(null);
      closeEventSource();
      return;
    }

    staleRef.current = false;
    setPartialResults([]);
    setError(null);
    setLoading(true);

    // Initial fetch
    const fetchJob = async () => {
      try {
        const api = isPublic ? publicApi.getJob(jobId) : jobsApi.get(jobId);
        const response = await api;
        if (!staleRef.current) {
          setJob(response.data);
        }
      } catch (err: any) {
        if (!staleRef.current) {
          setError(err.message || 'Failed to fetch job');
        }
      } finally {
        if (!staleRef.current) {
          setLoading(false);
        }
      }
    };

    fetchJob();

    // SSE only for private jobs
    if (!isPublic) {
      try {
        const es = jobsApi.stream(jobId);
        eventSourceRef.current = es;

        es.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            setJob((prev) => {
              if (!prev) return prev;

              // ИСПРАВЛЕНИЕ: явно обновляем optimizer/mapper из SSE
              // Если пришли реальные значения (не linucb_pending) — применяем
              const newOptimizer = data.optimizer !== undefined && data.optimizer !== 'linucb_pending' 
                ? data.optimizer 
                : prev.optimizer;
              const newMapper = data.mapper !== undefined && data.mapper !== 'linucb_pending'
                ? data.mapper
                : prev.mapper;

              return {
                ...prev,
                ...data,
                id: data.id || prev.id,
                user_id: prev.user_id,
                molecule: data.molecule || prev.molecule,
                optimizer: newOptimizer,
                mapper: newMapper,
                status: data.status || prev.status,
                progress: data.progress ?? prev.progress,
                results: data.results || prev.results,
                job_metadata: data.job_metadata || prev.job_metadata,
                preview_image: data.preview_image || prev.preview_image,
                use_linucb: data.use_linucb ?? prev.use_linucb,
                error_message: data.error_message ?? prev.error_message,
              };
            });

            if (data.partial_results?.length) {
              setPartialResults((prev) => [...prev, ...data.partial_results]);
            }

            // ИСПРАВЛЕНИЕ: после завершения делаем force-refresh для гарантии
            if (FINAL_STATUSES.includes(data.status)) {
              closeEventSource();
              // Небольшая задержка для гарантии записи в БД, затем HTTP-запрос
              setTimeout(() => {
                if (!staleRef.current) {
                  jobsApi.get(jobId).then(resp => {
                    if (!staleRef.current) {
                      setJob(prev => prev ? { ...prev, ...resp.data } : resp.data);
                    }
                  }).catch(() => {});
                }
              }, 500);
            }
          } catch (err) {
            console.error('SSE parse error:', err);
          }
        };

        es.onerror = async () => {
          closeEventSource();
          if (staleRef.current) return;

          try {
            const resp = await jobsApi.get(jobId);
            if (!staleRef.current) setJob(resp.data);
          } catch (e) {
            if (!staleRef.current) setError('Connection lost');
          }
        };
      } catch (e) {
        console.error('SSE init failed:', e);
        setError('Connection failed');
      }
    }

    return () => {
      staleRef.current = true;
      closeEventSource();
    };
  }, [jobId, isPublic, closeEventSource]);

  return { job, partialResults, loading, error, setJob };
}
