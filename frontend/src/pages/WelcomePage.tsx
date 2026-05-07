import { Link } from 'react-router-dom';
import { Grid } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export default function WelcomePage() {
  const { user } = useAuth();
  if (!user){
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Simple Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">PES</span>
              </div>
              <span className="text-xl font-bold text-gray-900">Главная</span>
            </div>

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
                Регистрация
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content with its own header and interactive cards */}
      <main className="flex-1 flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-3xl">
          <div className="bg-white rounded-2xl shadow-xl p-8 md:p-12 text-center w-full">
            <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6 leading-tight">
              РАСЧЁТ ПОТЕНЦИАЛЬНОЙ
              <br />ЭНЕРГЕТИЧЕСКОЙ ПОВЕРХНОСТИ
              <br />МОЛЕКУЛЫ
            </h1>
            <p className="text-gray-600 mb-10">
              Добро пожаловать в систему расчета ПЭП!</p><p className="text-gray-600 mb-10">Запускайте квантовые расчёты и исследуйте
              потенциал энергетической поверхности ваших молекул.
            </p>
          </div>

          {/* Interactive Features */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6 w-full">
            <Link to="/scan" className="bg-white rounded-lg p-6 text-center shadow card hover:no-underline">
              <div className="text-3xl mb-3">🔬</div>
              <h3 className="font-semibold text-gray-900 mb-1">Квантовые расчёты</h3>
              <p className="text-sm text-gray-600">Перейти к запуску ПЭП-скана</p>
            </Link>

            <Link to="/gallery" className="bg-white rounded-lg p-6 text-center shadow card hover:no-underline">
              <div className="text-3xl mb-3">📊</div>
              <h3 className="font-semibold text-gray-900 mb-1">Визуализация</h3>
              <p className="text-sm text-gray-600">Просмотр галереи ПЭП-сканов</p>
            </Link>

            <div className="bg-white rounded-lg p-6 text-center shadow card">
              <div className="text-3xl mb-3">💾</div>
              <h3 className="font-semibold text-gray-900 mb-1">Экспорт данных</h3>
              <p className="text-sm text-gray-600">JSON и PNG форматы</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

return (
      <main className="flex-1 flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-3xl">
          <div className="bg-white rounded-2xl shadow-xl p-8 md:p-12 text-center w-full">
            <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6 leading-tight">
              РАСЧЁТ ПОТЕНЦИАЛЬНОЙ
              <br />ЭНЕРГЕТИЧЕСКОЙ ПОВЕРХНОСТИ
              <br />МОЛЕКУЛЫ
            </h1>

            {/* Removed the register prompt after login; keep header actions visible */}
          </div>

          {/* Interactive Features */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6 w-full">
            <Link to="/scan" className="bg-white rounded-lg p-6 text-center shadow card hover:no-underline">
              <div className="text-3xl mb-3">🔬</div>
              <h3 className="font-semibold text-gray-900 mb-1">Квантовые расчёты</h3>
              <p className="text-sm text-gray-600">Перейти к запуску ПЭП-скана</p>
            </Link>

            <Link to="/gallery" className="bg-white rounded-lg p-6 text-center shadow card hover:no-underline">
              <div className="text-3xl mb-3">📊</div>
              <h3 className="font-semibold text-gray-900 mb-1">Визуализация</h3>
              <p className="text-sm text-gray-600">Просмотр галереи ПЭП-сканов</p>
            </Link>

            <div className="bg-white rounded-lg p-6 text-center shadow card">
              <div className="text-3xl mb-3">💾</div>
              <h3 className="font-semibold text-gray-900 mb-1">Экспорт данных</h3>
              <p className="text-sm text-gray-600">JSON и PNG форматы</p>
            </div>
          </div>
        </div>
      </main>
  );
}
