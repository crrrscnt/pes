import { useState, useEffect } from 'react';
import { jobsApi, publicApi } from '../api/endpoints';
import type { Job, PartialResult } from '../types';

interface UseJobStatusOptions {
  isPublic?: boolean; // Флаг для использования публичного API
}

export function useJobStatus(jobId: string | null, options: UseJobStatusOptions = {}) {
  const { isPublic = false } = options;
  const [job, setJob] = useState<Job | null>(null);
  const [partialResults, setPartialResults] = useState<PartialResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setPartialResults([]);
      return;
    }

    setPartialResults([]);  // Очистить старые результаты
    setLoading(true);
    setError(null);

    // Get initial job status
    const fetchJob = isPublic
      ? publicApi.getJob(jobId)
      : jobsApi.get(jobId);

    fetchJob
      .then(response => {
        setJob(response.data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });

    // Set up SSE stream только для приватного режима
    // В публичном режиме SSE не поддерживается, используются только финальные результаты
    if (!isPublic) {
      let eventSource: EventSource | null = null;
      try {
        eventSource = jobsApi.stream(jobId);

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            // Обновить job status
            setJob(prevJob => ({
              ...prevJob,
              ...data,
              id: data.id || prevJob?.id,
              user_id: prevJob?.user_id,
              molecule: prevJob?.molecule,
              atom_name: prevJob?.atom_name,
              optimizer: prevJob?.optimizer,
              mapper: prevJob?.mapper,
              is_public: prevJob?.is_public,
              precision_multiplier: prevJob?.precision_multiplier,
              results: data.results || prevJob?.results,
              job_metadata: data.job_metadata || prevJob?.job_metadata,
              preview_image: prevJob?.preview_image,
            } as Job));

            if (data.partial_results && Array.isArray(data.partial_results)) {
              setPartialResults(prev => [...prev, ...data.partial_results]);
            }

            if (data.status === 'completed' || data.status === 'failed') {
              try {
                eventSource?.close();
              } catch (e) {
                /* ignore */
              }
            }
          } catch (err) {
            console.error('Error parsing SSE data:', err);
          }
        };

        eventSource.onerror = async (err) => {
          console.error('SSE error:', err);
          // Try a single GET to obtain final job state before declaring connection lost.
          try {
            const resp = await jobsApi.get(jobId);
            setJob(resp.data);
          } catch (e) {
            console.error('Failed to fetch job after SSE error:', e);
            setError('Connection lost');
          } finally {
            // Close the connection to prevent the browser from continuously reconnecting
            try {
              eventSource?.close();
            } catch (e) {
              /* ignore */
            }
          }
        };

        return () => {
          try {
            eventSource?.close();
          } catch (e) {
            /* ignore */
          }
        };
      } catch (e) {
        console.error('Failed to create EventSource:', e);
        setError('Connection failed');
      }
    }
  }, [jobId, isPublic]);

  return { job, partialResults, loading, error, setJob };
}
