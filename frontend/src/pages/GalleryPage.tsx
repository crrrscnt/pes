import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { publicApi } from '../api/endpoints';
import type { JobListResponse } from '../types';
import JobCard from '../components/JobCard';
import { Search, Grid } from 'lucide-react';

export default function GalleryPage() {
    const [page, setPage] = useState(1);
    const [searchInput, setSearchInput] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    const { data, isLoading, isFetching, error } = useQuery<JobListResponse, Error>({
        queryKey: ['public-jobs', page, searchQuery],
        queryFn: async () => {
            const response = await publicApi.listJobs({
                page,
                per_page: 12,
                molecule_filter: searchQuery || undefined,
                sort_by: 'date',
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
                    Просмотр завершенных сканирований ПЭП от сообщества
                </p>
            </div>

            <div className="bg-white rounded-lg shadow p-4 mb-6">
                <div className="flex items-center gap-2 text-gray-700 font-medium mb-4">
                    <Search className="w-5 h-5" />
                    Поиск по галерее
                </div>

                <div className="grid gap-3">
                    <input
                        type="text"
                        id="search-query"
                        value={searchInput}
                        onChange={(e) => setSearchInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                setSearchQuery(searchInput.trim());
                                setPage(1);
                            }
                        }}
                        className="form-input w-full"
                        placeholder="Введите молекулу, ID задания или часть названия"
                    />

                    <div className="flex flex-col gap-2 sm:flex-row sm:justify-between">
                        <button
                            onClick={() => {
                                setSearchQuery(searchInput.trim());
                                setPage(1);
                            }}
                            className="btn btn-primary w-full sm:w-auto"
                            type="button"
                        >
                            Найти
                        </button>
                        <button
                            onClick={() => {
                                setSearchInput('');
                                setSearchQuery('');
                                setPage(1);
                            }}
                            className="btn btn-secondary w-full sm:w-auto"
                            type="button"
                        >
                            Очистить поиск
                        </button>
                    </div>
                </div>
            </div>

            {isFetching && !isLoading && (
                <div className="flex items-center gap-2 text-gray-600 mb-4">
                    <div className="spinner"></div>
                    <span>Обновляем результаты...</span>
                </div>
            )}

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
                    <p className="text-gray-600">Попробуйте другое ключевое слово или очистите поиск</p>
                </div>
            )}
        </div>
    );
}