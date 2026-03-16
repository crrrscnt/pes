import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Settings } from 'lucide-react';
import { jobsApi, authApi } from '../api/endpoints';
import { MOLECULE_PARAMS, OPTIMIZERS, MAPPERS } from '../types';
import type { User, MoleculeType, OptimizerType, MapperType } from '../types';

const VALID_MOLECULES = Object.keys(MOLECULE_PARAMS) as MoleculeType[];

const formSchema = z.object({
  molecule: z.string().refine(
    (v) => VALID_MOLECULES.includes(v as MoleculeType),
    { message: `Допустимые молекулы: ${VALID_MOLECULES.join(', ')}` }
  ),
  atom_name:            z.string().min(1),
  optimizer:            z.string().min(1),
  mapper:               z.string().min(1),
  precision_multiplier: z.number().int().min(1).max(2),
  use_linucb:           z.boolean(),
});

type FormData = z.infer<typeof formSchema>;

interface MoleculeFormProps {
  user: User | null;
  onJobCreated: (jobId: string) => void;
  onOptimizerChange?: (optimizer: OptimizerType) => void;
  onMapperChange?: (mapper: MapperType) => void;
}

export default function MoleculeForm({
  user,
  onJobCreated,
  onOptimizerChange,
  onMapperChange,
}: MoleculeFormProps) {
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const isExpertOrAdmin = user && (user.role === 'expert' || user.role === 'admin');

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      molecule:             'H2',
      atom_name:            'H',
      optimizer:            'SLSQP',
      mapper:               'Parity',
      precision_multiplier: 1,
      use_linucb:           true,
    },
  });

  const precisionMultiplier = watch('precision_multiplier');
  const useLinUCB           = watch('use_linucb');
  const moleculeValue       = watch('molecule');

  const handleMoleculeInput = (raw: string) => {
    setValue('molecule', raw.trim());
    const params = MOLECULE_PARAMS[raw.trim() as MoleculeType];
    if (params) setValue('atom_name', params.atom);
  };

  const onSubmit = async (data: FormData) => {
    if (!user) { setError('Войдите, чтобы запустить расчёты'); return; }
    setLoading(true);
    setError(null);
    try {
      const response = await jobsApi.create({
        molecule:             data.molecule,
        atom_name:            data.atom_name,
        optimizer:            data.optimizer,
        mapper:               data.mapper,
        precision_multiplier: data.precision_multiplier,
        use_linucb:           data.use_linucb,
      });
      onJobCreated(response.data.id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка при создании задания');
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800 text-center">
          <strong>Расчёты доступны только зарегистрированным пользователям.</strong>
        </p>
        <p className="text-sm text-blue-700 text-center mt-2">
          Войдите или зарегистрируйтесь, чтобы выполнить расчёт.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* ── Молекула: текстовый ввод с datalist ── */}
      <div className="form-group">
        <label htmlFor="molecule" className="form-label">Молекула</label>
        <datalist id="molecule-list">
          {VALID_MOLECULES.map((m) => (
            <option key={m} value={m} />
          ))}
        </datalist>
        <input
          {...register('molecule')}
          id="molecule"
          list="molecule-list"
          placeholder="H2, LiH, BH, BeH, CH, NH, OH, FH"
          className="form-input w-full"
          autoComplete="off"
          onChange={(e) => handleMoleculeInput(e.target.value)}
        />
        {errors.molecule && (
          <p className="mt-1 text-xs text-red-600">{errors.molecule.message}</p>
        )}
      </div>

      {/* ── LinUCB статус ── */}
      <div className="rounded-lg border border-violet-200 bg-violet-50 p-3">
        <div className="flex items-start gap-3">
          <div>
            <p className="text-sm font-semibold text-violet-900">
              {useLinUCB ? 'Умный выбор метода включён' : 'Ручной выбор метода'}
            </p>
            <p className="text-xs text-violet-700 mt-0.5">
              {useLinUCB
                ? 'LinUCB выбирает маппер/оптимизатор и повторяет расчёт до достижения качества.'
                : 'Вы сами выбираете маппер и оптимизатор.'}
            </p>
          </div>
        </div>
      </div>

      {/* ── Расширенные настройки — только для эксперта/админа ── */}
      {isExpertOrAdmin && (
        <>
          <div className="flex items-center justify-between border-t pt-3">
            <span className="text-sm font-medium text-gray-700">Расширенные настройки</span>
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="p-2 rounded-lg transition hover:bg-gray-100 text-gray-700"
              style={{ border: 'none' }}
            >
              <Settings className="w-5 h-5" />
            </button>
          </div>

          {showAdvanced && (
            <div className="space-y-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
              {/* Тогл LinUCB */}
              <div className="form-group">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    {...register('use_linucb')}
                    className="w-4 h-4 text-violet-600 rounded"
                  />
                  <span className="text-sm text-gray-700">Авто-выбор метода (LinUCB)</span>
                </label>
                <p className="mt-1 text-xs text-gray-500">
                  Снимите, чтобы указать маппер и оптимизатор вручную.
                </p>
              </div>

              {/* Ручные настройки */}
              {!useLinUCB && (
                <>
                  <div className="form-group">
                    <label htmlFor="optimizer" className="form-label">Оптимизатор</label>
                    <select
                      {...register('optimizer', {
                        onChange: (e) => onOptimizerChange?.(e.target.value as OptimizerType),
                      })}
                      id="optimizer"
                      className="form-select"
                    >
                      {OPTIMIZERS.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="mapper" className="form-label">Мэппер</label>
                    <select
                      {...register('mapper', {
                        onChange: (e) => onMapperChange?.(e.target.value as MapperType),
                      })}
                      id="mapper"
                      className="form-select"
                    >
                      {MAPPERS.map((m) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {/* 2x точность */}
              <div className="form-group">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={precisionMultiplier === 2}
                    onChange={(e) => setValue('precision_multiplier', e.target.checked ? 2 : 1)}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-sm text-gray-700">
                    2x точность (двойное количество точек)
                  </span>
                </label>
                <p className="mt-1 text-xs text-gray-500">
                  Уменьшает шаг вдвое. Время расчёта примерно удваивается.
                </p>
              </div>
            </div>
          )}
        </>
      )}

      <button type="submit" disabled={loading} className="btn btn-primary w-full">
        {loading ? (
          <><div className="spinner" /> Запуск сканирования...</>
        ) : (
          useLinUCB ? 'Умный PES-скан' : 'PES сканирование'
        )}
      </button>

      {user.role === 'user' && user.expert_request_status === 'none' && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800 mb-2">
            Хотите расширенные настройки и 2x точность?
          </p>
          <button
            type="button"
            onClick={async () => {
              try { await authApi.requestExpert(); alert('Запрос отправлен!'); window.location.reload(); }
              catch { alert('Ошибка при отправке запроса'); }
            }}
            className="btn btn-secondary text-sm"
          >
            Запрос статуса эксперта
          </button>
        </div>
      )}

      {user.expert_request_status === 'pending' && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-700">
            ⏳ Запрос на статус эксперта ожидает одобрения.
          </p>
        </div>
      )}
    </form>
  );
}
