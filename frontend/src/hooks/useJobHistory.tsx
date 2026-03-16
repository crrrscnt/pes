import { useState, useEffect } from 'react';
import { jobsApi } from '../api/endpoints';
import type { Job, JobListResponse } from '../types';

interface UseJobHistoryParams {
  page?: number;
  perPage?: number;
  statusFilter?: string;
  moleculeFilter?: string;
}

export function useJobHistory(params: UseJobHistoryParams = {}) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await jobsApi.list({
        page: params.page || 1,
        per_page: params.perPage || 10,
        status_filter: params.statusFilter,
        molecule_filter: params.moleculeFilter,
      });
      
      setJobs(response.data.jobs);
      setTotal(response.data.total);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [params.page, params.perPage, params.statusFilter, params.moleculeFilter]);

  return {
    jobs,
    total,
    loading,
    error,
    refetch: fetchJobs,
  };
}
