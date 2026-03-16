import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '../hooks/useAuth';

const loginSchema = z.object({
  email: z.string().email('Неправильный формат адреса электронной почты'),
  password: z.string().min(6, 'Пароль должен содержать не менее 6 символов'),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    setLoading(true);
    setError(null);

    try {
      await login(data.email, data.password);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка входа');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6 text-center">
          Логин
        </h1>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="form-group">
            <label htmlFor="email" className="form-label">
              Email
            </label>
            <input
              {...register('email')}
              type="email"
              id="email"
              className="form-input"
              placeholder="Введите ваш email"
            />
            {errors.email && (
              <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="password" className="form-label">
              Пароль
            </label>
            <input
              {...register('password')}
              type="password"
              id="password"
              className="form-input"
              placeholder="Введите ваш пароль"
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary w-full"
          >
            {loading ? (
              <>
                <div className="spinner"></div>
                Входим в систему...
              </>
            ) : (
              'Войти'
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-gray-600">
            Нет аккаунта?{' '}
            <Link to="/register" className="text-blue-600 hover:text-blue-700">
              Создать аккаунт
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
