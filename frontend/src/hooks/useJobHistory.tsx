import { useState, useEffect, useRef } from 'react';
import { jobsApi } from '../api/endpoints';
import type { Job } from '../types';

interface UseJobHistoryParams {
  page?: number;
  perPage?: number;
  statusFilter?: string;
}

export function useJobHistory(params: UseJobHistoryParams = {}) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Стабилизация params-объекта: избегаем лишних запросов если родитель
  // пересоздаёт объект при каждом рендере
  const paramsRef = useRef(params);
  paramsRef.current = params;

  useEffect(() => {
    let stale = false;

    const doFetch = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await jobsApi.list({
          page: paramsRef.current.page || 1,
          per_page: paramsRef.current.perPage || 10,
          status_filter: paramsRef.current.statusFilter,
        });

        if (!stale) {
          setJobs(response.data.jobs ?? []);
          setTotal(response.data.total);
        }
      } catch (err: unknown) {
        if (!stale) {
          const message = err instanceof Error ? err.message : 'Failed to fetch jobs';
          setError(message);
        }
      } finally {
        if (!stale) {
          setLoading(false);
        }
      }
    };

    doFetch();
    return () => { stale = true; };
  }, [params.page, params.perPage, params.statusFilter]);

  return {
    jobs,
    total,
    loading,
    error,
    refetch: () => {
      // Принудительный refetch через изменение внутреннего счётчика
      // (в данной реализации достаточно вызвать ререндер, но для простоты
      // можно добавить версию в deps — здесь оставляем явный перезапрос)
      setLoading(true);
      jobsApi.list({
        page: params.page || 1,
        per_page: params.perPage || 10,
        status_filter: params.statusFilter,
      }).then(res => {
        setJobs(res.data.jobs ?? []);
        setTotal(res.data.total);
      }).catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to fetch jobs');
      }).finally(() => setLoading(false));
    },
  };
}
