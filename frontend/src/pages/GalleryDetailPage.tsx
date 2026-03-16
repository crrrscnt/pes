import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { publicApi } from '../api/endpoints';
import PESChart from '../components/PESChart';
import JobDetails from '../components/JobDetails';

export default function GalleryDetailPage() {
    const { jobId } = useParams<{ jobId: string }>();

    const { data: job, isLoading, error } = useQuery({
        queryKey: ['public-job', jobId],
        queryFn: async () => {
            const response = await publicApi.getJob(jobId!);
            return response.data;
        },
        enabled: !!jobId,
    });

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-64">
                <div className="spinner"></div>
                <span className="ml-2 text-gray-600">Загрузка...</span>
            </div>
        );
    }

    if (error || !job) {
        return (
            <div className="text-center py-12">
                <h1 className="text-2xl font-bold text-gray-900 mb-4">Job Not Found</h1>
                <Link to="/gallery" className="text-blue-600 hover:text-blue-700">
                    ← Назад к галерее
                </Link>
            </div>
        );
    }

    return (
        <div>
            <div className="mb-6">
                <Link
                    to="/gallery"
                    className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 mb-4"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Назад к галерее
                </Link>
                <h1 className="text-2xl font-bold text-gray-900">
                    {job.molecule} PES Scan
                </h1>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Chart */}
                <div className="lg:col-span-2">
                    <div className="bg-white rounded-lg shadow p-6">
                        <h2 className="text-xl font-bold text-gray-900 mb-4">
                            Потенциальная энергетическая поверхность
                        </h2>
                        {/* ИСПРАВЛЕНО: добавлен флаг isPublic={true} */}
                        <PESChart jobId={job.id} isPublic={true} />
                    </div>
                </div>

                {/* Details */}
                <div className="lg:col-span-1">
                    <div className="bg-white rounded-lg shadow p-6">
                        <h2 className="text-xl font-bold text-gray-900 mb-4">
                            Детали задания
                        </h2>
                        {/* ИСПРАВЛЕНО: добавлен флаг isPublic={true} */}
                        <JobDetails jobId={job.id} isPublic={true} />
                    </div>
                </div>
            </div>
        </div>
    );
}
