import { useState, useEffect } from 'react';
import { Menu, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import MoleculeForm from '../components/MoleculeForm';
import PESChart from '../components/PESChart';
import JobDetails from '../components/JobDetails';
import { useJobHistory } from '../hooks/useJobHistory';
import { OPTIMIZER_TOOLTIPS, MAPPER_TOOLTIPS } from '../types';
import type { OptimizerType, MapperType } from '../types';

export default function HomePage() {
  const { user } = useAuth();
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [quickTipText, setQuickTipText] = useState<string>('');

  // Get recent jobs for sidebar
  const { jobs: recentJobs = [] } = useJobHistory({ perPage: 5 });
  const safeRecentJobs = recentJobs ?? [];

  const isExpertOrAdmin = user && (user.role === 'expert' || user.role === 'admin');

  // Устанавливаем начальный текст для Quick Tip
  useEffect(() => {
    if (!user) {
      setQuickTipText('Зарегистрируйтесь, чтобы получить доступ ко всем молекулам');
    } else {
      setQuickTipText('Настройте параметры сканирования квантовой химии ниже');
    }
  }, [user]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const jobIdFromUrl = params.get('job');
    if (jobIdFromUrl) {
      setCurrentJobId(jobIdFromUrl);
    }
  }, []);

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 1024;
      setIsMobile(mobile);

      // На мобильных - закрываем сайдбар
      if (mobile) {
        setSidebarOpen(false);
      }
      // На desktop - открываем сайдбар
      else {
        setSidebarOpen(true);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleOptimizerChange = (optimizer: OptimizerType) => {
    if (isExpertOrAdmin) {
      setQuickTipText(OPTIMIZER_TOOLTIPS[optimizer]);
    }
  };

  const handleMapperChange = (mapper: MapperType) => {
    if (isExpertOrAdmin) {
      setQuickTipText(MAPPER_TOOLTIPS[mapper]);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return '✓';
      case 'running':
        return '⟳';
      case 'failed':
        return '✗';
      default:
        return '○';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600';
      case 'running':
        return 'text-blue-600';
      case 'failed':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="flex h-[calc(100vh-80px)] bg-gray-50 relative">
      {/* Single Sidebar Toggle Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className={`sidebar-toggle ${sidebarOpen ? 'sidebar-toggle-open' : 'sidebar-toggle-closed'}`}
        aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        {sidebarOpen ? (
          isMobile ? <X className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />
        ) : (
          isMobile ? <Menu className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />
        )}
      </button>

      {/* Overlay for mobile */}
      {isMobile && sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        ></div>
      )}

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        <div className="p-6">
          <div className="mb-6">
            <h2 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-blue-800 bg-clip-text text-transparent">
              PES параметры
            </h2>
          </div>

          {/* Quick Tip Card */}
          <div className="sidebar-info-card">
            <p className="text-xs text-blue-900 font-medium mb-1">Подсказка</p>
            <p className="text-sm text-blue-700">
              {quickTipText}
            </p>
          </div>

          <MoleculeForm
            user={user}
            onJobCreated={setCurrentJobId}
            onOptimizerChange={handleOptimizerChange}
            onMapperChange={handleMapperChange}
          />

          {user && safeRecentJobs.length > 0 && (
            <div className="sidebar-recent-scans">
              <h3 className="text-sm font-medium text-gray-900 mb-2">Последние сканы</h3>
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
                    <span className="text-sm text-gray-700">
                      {job.molecule} - {job.optimizer}
                    </span>
                    <span className={`text-xs ${getStatusColor(job.status)}`}>
                      {getStatusIcon(job.status)}
                    </span>
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
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Потенциальная энергетическая поверхность
            </h1>
            <p className="text-gray-600">
              Визуализация результатов сканирования PES для выбранной молекулы в реальном времени
            </p>
          </div>

          {/* Content Grid */}
          <div className="content-grid">
            {/* Chart - Takes 2 columns on xl screens */}
            <div className="chart-section">
              <div className="card">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Кривая диссоциации
                </h2>
                <PESChart jobId={currentJobId} />
              </div>
            </div>

            {/* Job Details */}
            <div className="job-details-section">
              <div className="card sticky top-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Статус задания
                </h2>
                <JobDetails jobId={currentJobId} />
              </div>
            </div>
          </div>

          {/* Additional Info Cards */}
          {user && (
            <div className="stats-grid">
              <div className="stat-card stat-card-blue">
                <div className="text-3xl font-bold mb-2">{safeRecentJobs.length}</div>
                <div className="text-blue-100">Недавние сканы</div>
              </div>
              <div className="stat-card stat-card-green">
                <div className="text-3xl font-bold mb-2">
                  {safeRecentJobs.filter(j => j.status === 'completed').length}
                </div>
                <div className="text-green-100">Завершено</div>
              </div>
              <div className="stat-card stat-card-purple">
                <div className="text-3xl font-bold mb-2">
                  {safeRecentJobs.filter(j => j.status === 'running').length}
                </div>
                <div className="text-purple-100">В процессе</div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}