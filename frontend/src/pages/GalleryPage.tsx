import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { publicApi } from '../api/endpoints';
import JobCard from '../components/JobCard';
import { Filter, Grid } from 'lucide-react';

export default function GalleryPage() {
    const [page, setPage] = useState(1);
    const [moleculeFilter, setMoleculeFilter] = useState('');
    const [sortBy, setSortBy] = useState<'date' | 'oldest'>('date');

    const { data, isLoading, error } = useQuery({
        queryKey: ['public-jobs', page, moleculeFilter, sortBy],
        queryFn: async () => {
            const response = await publicApi.listJobs({
                page,
                per_page: 12,
                molecule_filter: moleculeFilter || undefined,
                sort_by: sortBy,
            });
            return response.data;
        },
    });

    const totalPages = data ? Math.ceil(data.total / 12) : 0;

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-64">
                <div className="spinner"></div>
                <span className="ml-2 text-gray-600">Загружаем галерею...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center py-12">
                <h1 className="text-2xl font-bold text-gray-900 mb-4">Ошибка</h1>
                <p className="text-gray-600">Не удалось загрузить галерею</p>
            </div>
        );
    }

    return (
        <div>
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900 mb-4">Галерея</h1>
                <p className="text-gray-600">
                    Просмотр завершенных сканирований PES от сообщества
                </p>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-lg shadow p-4 mb-6">
                <div className="flex items-center gap-2 mb-3">
                    <Filter className="w-5 h-5 text-gray-600" />
                    <span className="font-medium text-gray-700">Фильтры</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Molecule Filter */}
                    <div>
                        <label htmlFor="molecule-filter" className="form-label">
                            Молекула
                        </label>
                        <select
                            id="molecule-filter"
                            value={moleculeFilter}
                            onChange={(e) => {
                                setMoleculeFilter(e.target.value);
                                setPage(1);
                            }}
                            className="form-select"
                        >
                            <option value="">Все молекулы</option>
                            <option value="H2">H₂</option>
                            <option value="LiH">LiH</option>
                            <option value="BH">BH</option>
                            <option value="BeH">BeH</option>
                            <option value="CH">CH</option>
                            <option value="NH">NH</option>
                            <option value="OH">OH</option>
                            <option value="FH">FH</option>
                        </select>
                    </div>

                    {/* Sort By */}
                    <div>
                        <label htmlFor="sort-by" className="form-label">
                            Сортировка
                        </label>
                        <select
                            id="sort-by"
                            value={sortBy}
                            onChange={(e) => {
                                setSortBy(e.target.value as 'date' | 'oldest');
                                setPage(1);
                            }}
                            className="form-select"
                        >
                            <option value="date">Сначала новые</option>
                            <option value="oldest">Сначала старые</option>
                        </select>
                    </div>

                    {/* Clear Filters */}
                    <div className="flex items-end">
                        <button
                            onClick={() => {
                                setMoleculeFilter('');
                                setSortBy('date');
                                setPage(1);
                            }}
                            className="btn btn-secondary w-full"
                        >
                            Сбросить
                        </button>
                    </div>
                </div>
            </div>

            {/* Grid of Cards */}
            {data && data.jobs.length > 0 ? (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-6">
                        {data.jobs.map((job) => (
                            <JobCard key={job.id} job={job} />
                        ))}
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="flex items-center justify-center gap-2">
                            <button
                                onClick={() => setPage(Math.max(1, page - 1))}
                                disabled={page === 1}
                                className="btn btn-secondary"
                            >
                                Предыдущая
                            </button>

                            <div className="flex items-center gap-1">
                                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                    const pageNum = i + 1;
                                    return (
                                        <button
                                            key={pageNum}
                                            onClick={() => setPage(pageNum)}
                                            className={`px-3 py-1 rounded ${page === pageNum
                                                ? 'bg-blue-600 text-white'
                                                : 'bg-white text-gray-700 hover:bg-gray-100'
                                                }`}
                                        >
                                            {pageNum}
                                        </button>
                                    );
                                })}
                                {totalPages > 5 && <span className="px-2">...</span>}
                            </div>

                            <button
                                onClick={() => setPage(Math.min(totalPages, page + 1))}
                                disabled={page === totalPages}
                                className="btn btn-secondary"
                            >
                                Следующая
                            </button>
                        </div>
                    )}
                </>
            ) : (
                <div className="text-center py-12">
                    <Grid className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Результаты не найдены</h3>
                    <p className="text-gray-600">Попробуйте изменить фильтры</p>
                </div>
            )}
        </div>
    );
}