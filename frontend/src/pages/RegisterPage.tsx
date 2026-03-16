import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '../hooks/useAuth';

const registerSchema = z.object({
  email: z.string().email('Неправильный формат адреса электронной почты'),
  password: z.string().min(6, 'Пароль должен содержать не менее 6 символов'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Пароли не совпадают",
  path: ["confirmPassword"],
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterForm) => {
    setLoading(true);
    setError(null);

    try {
      await registerUser(data.email, data.password);
      navigate('/login');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка регистрации');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6 text-center">
          Создать аккаунт
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

          <div className="form-group">
            <label htmlFor="confirmPassword" className="form-label">
              Подтвердите пароль
            </label>
            <input
              {...register('confirmPassword')}
              type="password"
              id="confirmPassword"
              className="form-input"
              placeholder="Подтвердите ваш пароль"
            />
            {errors.confirmPassword && (
              <p className="mt-1 text-sm text-red-600">{errors.confirmPassword.message}</p>
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
                Создаем аккаунт...
              </>
            ) : (
              'Создать аккаунт'
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-gray-600">
            Уже есть аккаунт?{' '}
            <Link to="/login" className="text-blue-600 hover:text-blue-700">
              Войти
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
