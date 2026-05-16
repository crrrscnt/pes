import { useState, useEffect, useRef, useCallback } from 'react';
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

  // Стабилизация params-объекта
  const paramsRef = useRef(params);
  paramsRef.current = params;

  const doFetch = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await jobsApi.list({
        page: paramsRef.current.page || 1,
        per_page: paramsRef.current.perPage || 10,
        status_filter: paramsRef.current.statusFilter,
      });

      setJobs(response.data.jobs ?? []);
      setTotal(response.data.total);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch jobs';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let stale = false;

    const fetch = async () => {
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

    fetch();
    return () => { stale = true; };
  }, [params.page, params.perPage, params.statusFilter]);

  // Авто-обновление каждые 5 секунд если есть running-задания
  useEffect(() => {
    const hasRunning = jobs.some(j => j.status === 'running');
    if (!hasRunning) return;

    const interval = setInterval(() => {
      doFetch();
    }, 5000);

    return () => clearInterval(interval);
  }, [jobs, doFetch]);

  return {
    jobs,
    total,
    loading,
    error,
    refetch: doFetch,
  };
}
