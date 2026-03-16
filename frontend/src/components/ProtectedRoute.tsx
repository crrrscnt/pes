import { useAuth } from '../hooks/useAuth';
import { Navigate } from 'react-router-dom';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export default function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="spinner"></div>
        <span className="ml-2 text-gray-600">Загрузка...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requireAdmin && user.role !== 'admin') {
    return (
      <div className="text-center py-12">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Доступ запрещен</h1>
        <p className="text-gray-600">У вас нет прав администратора для доступа к этой странице.</p>
      </div>
    );
  }

  return <>{children}</>;
}
