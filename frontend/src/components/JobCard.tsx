import { Link } from 'react-router-dom';
import { Calendar, User as UserIcon, FlaskConical } from 'lucide-react';
import type { Job } from '../types';

interface JobCardProps {
    job: Job;
}

export default function JobCard({ job }: JobCardProps) {
    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    // Use static molecule images instead of preview_image
    const moleculeImage = `/molecules/${job.molecule}.png`;

    return (
        <Link
            to={`/gallery/${job.id}`}
            className="block bg-white rounded-lg shadow hover:shadow-lg transition-shadow overflow-hidden"
        >
            {/* Molecule Image */}
            <div className="w-full h-48 bg-gray-100 flex items-center justify-center p-4">
                <img
                    src={moleculeImage}
                    alt={`${job.molecule} molecule`}
                    className="w-full h-full object-contain"
                    style={{ display: 'block', margin: 'auto' }}
                    onError={(e) => {
                        // Fallback to icon if image fails to load
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                        target.parentElement!.innerHTML = `
                            <div class="flex flex-col items-center justify-center text-gray-400">
                                <svg class="w-16 h-16 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                                </svg>
                                <span class="text-sm font-medium">${job.molecule}</span>
                            </div>
                        `;
                    }}
                />
            </div>

            {/* Card Content */}
            <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">{job.molecule}</h3>
                    {job.precision_multiplier === 2 && (
                        <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs font-medium rounded">
                            2x точность
                        </span>
                    )}
                </div>

                <div className="space-y-1 text-sm text-gray-600">
                    <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        <span>{formatDate(job.completed_at || job.created_at)}</span>
                    </div>

                    <div className="flex items-center gap-2">
                        <UserIcon className="w-4 h-4" />
                        <span className="capitalize">
                            {job.user_id ? 'Registered User' : 'Anonymous'}
                        </span>
                    </div>
                </div>

                {/* Metadata */}
                {job.job_metadata && (
                    <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500">
                        <div className="flex justify-between">
                            <span>Min расстояние:</span>
                            <span className="font-medium">
                                {job.job_metadata.min_distance?.toFixed(4)} Å
                            </span>
                        </div>
                        <div className="flex justify-between">
                            <span>Точки:</span>
                            <span className="font-medium">{job.job_metadata.total_points}</span>
                        </div>
                    </div>
                )}
            </div>
        </Link>
    );
}
