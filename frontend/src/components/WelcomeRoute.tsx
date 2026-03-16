import { useAuth } from '../hooks/useAuth';
import { Navigate } from 'react-router-dom';

interface WelcomeRouteProps {
  children: React.ReactNode;
}

export default function WelcomeRoute({ children }: WelcomeRouteProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="spinner"></div>
        <span className="ml-2 text-gray-600">Загрузка...</span>
      </div>
    );
  }

  // If user is logged in, redirect to /scan
  if (user) {
    return <Navigate to="/scan" replace />;
  }

  // Otherwise show welcome page
  return <>{children}</>;
}
