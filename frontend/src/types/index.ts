export interface User {
  id: string;
  email: string;
  role: 'user' | 'expert' | 'admin';
  created_at: string;
  is_active: boolean;
  expert_request_status: 'none' | 'pending' | 'approved' | 'rejected';
  expert_request_date?: string;
}

export interface JobRoundResponse {
  id: string;
  arm_id: string;
  round_number: number;
  reward?: number | null;
  avg_error_ha?: number | null;
  context_vector?: number[] | null;
  created_at: string;
}

export interface Job {
  id: string;
  user_id?: string;
  molecule: string;
  optimizer: string;
  mapper: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress: number;
  error_message?: string;
  results?: Record<string, any>;
  job_metadata?: Record<string, any>;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  is_public: boolean;
  precision_multiplier: number;
  preview_image?: string;
  use_linucb?: boolean;
  rounds?: JobRoundResponse[];
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  per_page: number;
}

export interface UserListResponse {
  users: User[];
  total: number;
  page: number;
  per_page: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface JobCreate {
  molecule: string;
  optimizer: string;
  mapper: string;
  precision_multiplier?: number;
  use_linucb?: boolean;
}

export interface PESResult {
  distance: number;
  vqe: number;
  numpy: number;
  num_spatial_orbitals: number;
  num_particles: number;
}

export interface PESResults {
  [distance: string]: PESResult | { error: string };
}

export interface ScanResults {
  molecule_name: string;
  results: PESResults;
  min_distance?: number;
  peaks?: number[];
  elapsed_time: number;
  status: 'completed' | 'failed';
}

export interface PartialResult {
  distance: number;
  vqe: number;
  numpy: number;
  total_points: number;
  calculated_points: number;
}

export interface ExpertRequest {
  user_id: string;
  email: string;
  request_date: string;
  status: string;
}

export const OPTIMIZER_TOOLTIPS = {
  SLSQP: 'SLSQP - градиентный оптимизатор, быстро сходится для гладких задач; хорош при строгих ограничениях, даёт малое время и точную локальную оптимизацию.',
  COBYLA: 'COBYLA - безградиентный оптимизатор, устойчив к неточным оценкам градиента; медленнее, но полезен при шумных функциях.',
  SPSA: 'SPSA - стохастический оптимизатор, требует меньше измерений градиента на итерацию, подходит для шумных/квантовых измерений; даёт более высокие ошибки и требует больше времени.',
} as const;

export const MAPPER_TOOLTIPS = {
  JordanWigner: 'JordanWigner мэппер: простой, может требовать больше операций для дальних связей; хорошо для малых систем.',
  BravyiKitaev: 'BravyiKitaev мэппер: компромисс, уменьшает глубину и локализует операции.',
  Parity: 'Parity мэппер: полезен при парных взаимодействиях; может давать выигрыш в некоторых схемах.',
} as const;

export const OPTIMIZERS = ['SLSQP', 'COBYLA', 'SPSA'] as const;

export const MAPPERS = ['JordanWigner', 'BravyiKitaev', 'Parity'] as const;

export type MoleculeType = string; // Теперь любая строка, не ограничена
export type OptimizerType = typeof OPTIMIZERS[number];
export type MapperType = typeof MAPPERS[number];

export interface LinUCBArmStats {
  arm_id: string;
  mapper: string;
  optimizer: string;
  n_pulls: number;
  avg_reward: number | null;
  total_reward: number;
}
