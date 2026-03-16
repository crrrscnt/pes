import { Link, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { LogOut, History, Settings, Home, Grid } from 'lucide-react';

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Не удалось выйти', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                to={user ? "/scan" : "/"}
                className="flex items-center gap-2"
              >
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">PES</span>
                </div>
                <span className="text-xl font-bold text-gray-900">PES Scan</span>
              </Link>
            </div>

            <nav className="flex items-center gap-4">
              {user && (
                <Link
                  to="/scan"
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition ${location.pathname === '/scan'
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100'
                    }`}
                >
                  <Home className="w-4 h-4" />
                  Главная
                </Link>
              )}

              <Link
                to="/gallery"
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition ${location.pathname.startsWith('/gallery')
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
                  }`}
              >
                <Grid className="w-4 h-4" />
                Галерея
              </Link>

              {user && (
                <Link
                  to="/history"
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition ${location.pathname === '/history'
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100'
                    }`}
                >
                  <History className="w-4 h-4" />
                  История
                </Link>
              )}

              {user?.role === 'admin' && (
                <Link
                  to="/admin"
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition ${location.pathname === '/admin'
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100'
                    }`}
                >
                  <Settings className="w-4 h-4" />
                  Админ
                </Link>
              )}

              <div className="flex items-center gap-2">
                {user ? (
                  <>
                    {/* ===== FIX? ===== */}
                    <span className="text-sm text-gray-600">
                      {user.email}
                      {user.role === 'admin' && (
                        <span className="ml-2 px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full">
                          Админ
                        </span>
                      )}
                      {user.role === 'expert' && (
                        <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                          Эксперт
                        </span>
                      )}
                    </span>
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition"
                    >
                      <LogOut className="w-4 h-4" />
                      Выйти
                    </button>
                  </>
                ) : (
                  <div className="flex items-center gap-2">
                    <Link
                      to="/login"
                      className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition"
                    >
                      Войти
                    </Link>
                    <Link
                      to="/register"
                      className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition"
                    >
                      Зарегистрироваться
                    </Link>
                  </div>
                )}
              </div>
            </nav>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="container mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
