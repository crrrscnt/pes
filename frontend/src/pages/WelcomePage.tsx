import { Link } from 'react-router-dom';
import { Grid } from 'lucide-react';

export default function WelcomePage() {
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
              <span className="text-xl font-bold text-gray-900">PES Scan</span>
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

      {/* Main Content */}
      {/* СДЕЛАНО: flex-col чтобы дети располагались вертикально */}
      <main className="flex-1 flex flex-col items-center justify-center p-4">
        {/* Центрирующий контейнер с ограниченной шириной */}
        <div className="w-full max-w-2xl">
          {/* Hero Card */}
          <div className="bg-white rounded-2xl shadow-xl p-8 md:p-12 text-center w-full">
            {/* Title */}
            <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-8 leading-tight">
              РАСЧЁТ ПОТЕНЦИАЛЬНОЙ<br />
              ЭНЕРГЕТИЧЕСКОЙ ПОВЕРХНОСТИ<br />
              МОЛЕКУЛЫ
            </h1>

            {/* Gallery Button */}
            <Link
              to="/gallery"
              className="inline-flex items-center justify-center gap-3 px-8 py-4 bg-gray-700 text-gray-600 text-lg font-semibold rounded-xl hover:bg-blue-700 transition-all transform hover:scale-105 shadow-lg hover:shadow-xl"
            >
              <Grid className="w-6 h-6" />
              Галерея расчётов
            </Link>

            {/* Info Text */}
            <p className="mt-8 text-gray-600 text-sm md:text-base">
              Просматривайте расчёты других пользователей в галерее или{' '}
              <Link to="/register" className="text-blue-600 hover:text-blue-700 underline">
                зарегистрируйтесь
              </Link>
              {' '}для выполнения собственных квантово-химических расчётов
            </p>
          </div>

          {/* Features */}
          {/* Здесь важно: mt-8 и w-full — будет под карточкой */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4 w-full">
            <div className="bg-white rounded-lg p-4 text-center shadow">
              <div className="text-3xl mb-2">🔬</div>
              <h3 className="font-semibold text-gray-900 mb-1">Квантовые расчёты</h3>
              <p className="text-sm text-gray-600">VQE алгоритмы для молекул</p>
            </div>

            <div className="bg-white rounded-lg p-4 text-center shadow">
              <div className="text-3xl mb-2">📊</div>
              <h3 className="font-semibold text-gray-900 mb-1">Визуализация</h3>
              <p className="text-sm text-gray-600">Интерактивные графики PES</p>
            </div>

            <div className="bg-white rounded-lg p-4 text-center shadow">
              <div className="text-3xl mb-2">💾</div>
              <h3 className="font-semibold text-gray-900 mb-1">Экспорт данных</h3>
              <p className="text-sm text-gray-600">JSON и PNG форматы</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
