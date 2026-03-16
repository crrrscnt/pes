import { apiClient } from './client';
import type {
  User,
  Job,
  JobListResponse,
  UserListResponse,
  LoginRequest,
  RegisterRequest,
  JobCreate,
  ExpertRequest
} from '../types';

// Auth endpoints
export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<{ user: User; message: string }>('/api/auth/login', data),

  register: (data: RegisterRequest) =>
    apiClient.post<{ message: string }>('/api/auth/register', data),

  logout: () =>
    apiClient.post<{ message: string }>('/api/auth/logout'),

  me: () =>
    apiClient.get<User>('/api/auth/me'),

  requestExpert: () =>
    apiClient.post<{ message: string }>('/api/auth/request-expert'),
};

// Job endpoints
export const jobsApi = {
  create: (data: JobCreate) =>
    apiClient.post<Job>('/api/jobs', data),

  get: (jobId: string) =>
    apiClient.get<Job>(`/api/jobs/${jobId}`),

  list: (params?: {
    page?: number;
    per_page?: number;
    status_filter?: string;
    molecule_filter?: string;
  }) =>
    apiClient.get<JobListResponse>('/api/jobs', { params }),

  stream: (jobId: string) =>
    // Include credentials so the browser sends cookies (session_id) with the SSE request.
    // EventSource supports an init dict with `withCredentials` in modern browsers/TS dom lib.
    new EventSource(`${apiClient.defaults.baseURL}/api/jobs/${jobId}/stream`, { withCredentials: true }),
};

// Public endpoints
export const publicApi = {
  listJobs: (params?: {
    page?: number;
    per_page?: number;
    molecule_filter?: string;
    status_filter?: string;
    sort_by?: string;
  }) =>
    apiClient.get<JobListResponse>('/api/public/jobs', { params }),

  getJob: (jobId: string) =>
    apiClient.get<Job>(`/api/public/jobs/${jobId}`),
};

// Admin endpoints
export const adminApi = {
  listUsers: (params?: {
    page?: number;
    per_page?: number;
    role_filter?: string;
    active_filter?: boolean;
  }) =>
    apiClient.get<UserListResponse>('/api/admin/users', { params }),

  getUserJobs: (userId: string, params?: {
    page?: number;
    per_page?: number;
    status_filter?: string;
  }) =>
    apiClient.get<JobListResponse>(`/api/admin/users/${userId}/jobs`, { params }),

  updateUser: (userId: string, data: Partial<User>) =>
    apiClient.patch<User>(`/api/admin/users/${userId}`, data),

  listAllJobs: (params?: {
    page?: number;
    per_page?: number;
    status_filter?: string;
    molecule_filter?: string;
    user_filter?: string;
  }) =>
    apiClient.get<JobListResponse>('/api/admin/jobs', { params }),

  deleteJob: (jobId: string) =>
    apiClient.delete<{ message: string }>(`/api/admin/jobs/${jobId}`),

  listExpertRequests: () =>
    apiClient.get<ExpertRequest[]>('/api/admin/expert-requests'),

  handleExpertRequest: (userId: string, action: 'approve' | 'reject') =>
    apiClient.post<{ message: string }>(`/api/admin/expert-requests/${userId}`, { action }),
};

// LinUCB bandit state (admin only)
export const linucbApi = {
  getArmStats: () => apiClient.get('/api/linucb/arms'),
  reset: () => apiClient.post('/api/linucb/reset', {}),
};
