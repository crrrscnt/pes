import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Menu, X, ChevronLeft, ChevronRight, FlaskConical } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import MoleculeForm from '../components/MoleculeForm';
import PESChart from '../components/PESChart';
import JobDetails from '../components/JobDetails';
import { useJobHistory } from '../hooks/useJobHistory';
import { OPTIMIZER_TOOLTIPS, MAPPER_TOOLTIPS } from '../types';
import type { OptimizerType, MapperType } from '../types';

export default function HomePage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const [currentJobId, setCurrentJobId] = useState<string | null>(searchParams.get('job'));
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [quickTipText, setQuickTipText] = useState('');

  const { jobs: recentJobs } = useJobHistory({ page: 1, perPage: 5 });

  const isExpertOrAdmin = useMemo(
    () => user?.role === 'expert' || user?.role === 'admin',
    [user?.role]
  );

  // Подсказка показывается ТОЛЬКО экспертам и админам — обычным пользователям не нужна,
  // т.к. они не могут менять гиперпараметры (LinUCB выбирает за них)
  useEffect(() => {
    if (!isExpertOrAdmin) {
      setQuickTipText('');
      return;
    }
    setQuickTipText('Настройте параметры сканирования квантовой химии ниже');
  }, [isExpertOrAdmin]);

  // Синхронизация с URL (?job=...)
  useEffect(() => {
    const jobFromUrl = searchParams.get('job');
    if (jobFromUrl && jobFromUrl !== currentJobId) {
      setCurrentJobId(jobFromUrl);
    }
  }, [searchParams, currentJobId]);

  // Адаптив сайдбара
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 1024;
      setIsMobile(mobile);
      setSidebarOpen(!mobile);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleOptimizerChange = useCallback((optimizer: OptimizerType) => {
    if (isExpertOrAdmin) {
      setQuickTipText(OPTIMIZER_TOOLTIPS[optimizer]);
    }
  }, [isExpertOrAdmin]);

  const handleMapperChange = useCallback((mapper: MapperType) => {
    if (isExpertOrAdmin) {
      setQuickTipText(MAPPER_TOOLTIPS[mapper]);
    }
  }, [isExpertOrAdmin]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <span className="status-badge status-completed">✓</span>;
      case 'running':   return <span className="status-badge status-running">⟳</span>;
      case 'failed':    return <span className="status-badge status-failed">✗</span>;
      default:          return <span className="status-badge status-queued">○</span>;
    }
  };

  // ── Гость: явная заглушка вместо формы ──
  if (!user) {
    return (
      <div className="theme-glass min-h-screen flex items-center justify-center p-6">
        <div className="card text-center max-w-md">
          <FlaskConical className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--gray-400)' }} />
          <h2 className="text-xl font-bold mb-2">Требуется авторизация</h2>
          <p className="mb-6" style={{ color: 'var(--text-muted)' }}>
            Для запуска квантовых расчётов необходимо войти в систему или зарегистрироваться.
            <br />
            Анонимные пользователи могут просматривать только галерею публичных расчётов.
          </p>
          <div className="flex flex-col gap-3">
            <a href="/login" className="btn btn-primary">Войти</a>
            <a href="/register" className="btn btn-secondary">Зарегистрироваться</a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="theme-glass min-h-screen">
      {/* Toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className={`sidebar-toggle ${sidebarOpen ? 'sidebar-toggle-open' : 'sidebar-toggle-closed'}`}
        aria-label={sidebarOpen ? 'Закрыть сайдбар' : 'Открыть сайдбар'}
      >
        {sidebarOpen
          ? (isMobile ? <X className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />)
          : (isMobile ? <Menu className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />)}
      </button>

      {/* Mobile overlay */}
      {isMobile && sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        <div className="p-6">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-blue-800">
              ПЭП параметры
            </h2>
          </div>

          {/* Quick Tip — только для экспертов и админов */}
          {isExpertOrAdmin && quickTipText && (
            <div className="sidebar-info-card">
              <p className="font-medium mb-1">Подсказка</p>
              <p className="text-sm">{quickTipText}</p>
            </div>
          )}

          <MoleculeForm
            user={user}
            onJobCreated={setCurrentJobId}
            onOptimizerChange={handleOptimizerChange}
            onMapperChange={handleMapperChange}
          />

          {recentJobs.length > 0 && (
            <div className="sidebar-recent-scans">
              <h3 className="text-sm font-medium mb-2">Последние сканы</h3>
              <div className="space-y-2">
                {recentJobs.map((job) => (
                  <div
                    key={job.id}
                    className="recent-scan-item"
                    onClick={() => {
                      setCurrentJobId(job.id);
                      if (isMobile) setSidebarOpen(false);
                    }}
                  >
                    <span className="text-sm font-medium">{job.molecule} — {job.optimizer}</span>
                    {getStatusIcon(job.status)}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className={`main-content ${!isMobile && !sidebarOpen ? 'main-content-expanded' : ''}`}>
        <div className="p-6 max-w-7xl mx-auto">
          <div className="mb-6">
            <h1>Потенциальная энергетическая поверхность</h1>
            <p className="mt-1" style={{ color: 'var(--text-muted)' }}>
              Визуализация результатов сканирования ПЭП для выбранной молекулы в реальном времени
            </p>
          </div>

          <div className="content-grid">
            <div className="chart-section">
              <div className="card">
                <PESChart jobId={currentJobId} />
              </div>
            </div>

            <div className="job-details-section">
              <div className="card sticky top-6">
                <h2 className="mb-4">Статус задания</h2>
                <JobDetails jobId={currentJobId} />
              </div>
            </div>
          </div>

          <div className="stats-grid">
            <div className="stat-card stat-card-blue">
              <div className="text-3xl font-bold mb-2">{recentJobs.length}</div>
              <div className="text-blue-100">Недавние сканы</div>
            </div>
            <div className="stat-card stat-card-green">
              <div className="text-3xl font-bold mb-2">
                {recentJobs.filter(j => j.status === 'completed').length}
              </div>
              <div className="text-green-100">Завершено</div>
            </div>
            <div className="stat-card stat-card-purple">
              <div className="text-3xl font-bold mb-2">
                {recentJobs.filter(j => j.status === 'running').length}
              </div>
              <div className="text-purple-100">В процессе</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
