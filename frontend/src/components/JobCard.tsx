import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, User as UserIcon, FlaskConical } from 'lucide-react';
import type { Job } from '../types';

interface JobCardProps {
    job: Job;
}

export default function JobCard({ job }: JobCardProps) {
    const [imageError, setImageError] = useState(false);

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    const imageUrl = !imageError && job.preview_image ? job.preview_image : `/molecules/${job.molecule}.png`;

    return (
        <Link
            to={`/gallery/${job.id}`}
            className="block bg-white rounded-lg shadow hover:shadow-lg transition-shadow overflow-hidden"
        >
            {/* Molecule Image */}
            <div className="w-full bg-gray-100 flex items-start justify-center overflow-hidden rounded-t-lg" style={{ aspectRatio: '16 / 9' }}>
                {imageUrl ? (
                  <img
                    src={imageUrl}
                    alt={`${job.molecule} molecule`}
                    style={{ width: '100%', maxWidth: '90%', height: '100%', objectFit: 'cover', objectPosition: 'center', display: 'block', margin: '15px auto' }}
                    loading="lazy"
                    onError={() => setImageError(true)}
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center text-gray-400">
                    <div className="w-16 h-16 mb-2 rounded-full bg-white shadow flex items-center justify-center">
                      <FlaskConical className="w-8 h-8" />
                    </div>
                    <span className="text-sm font-medium">{job.molecule}</span>
                  </div>
                )}
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
