import React from 'react';
import { AlertPriority } from '../types';

interface ReportCardProps {
  title: string;
  description: string;
  type: string;
  borough: string;
  status: string;
  priority: AlertPriority;
  author: string;
  createdAt: string;
  driveLink?: string;
 // onViewDetails: () => void;
}

const ReportCard: React.FC<ReportCardProps> = ({
  title,
  description,
  type,
  borough,
  status,
  priority,
  author,
  createdAt,
  driveLink,
 // onViewDetails,
}) => {
  return (
    <div className="card bg-zinc-800 card-hover cursor-pointer flex flex-col h-full">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-start gap-4 mb-4">
        <div>
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            {title}
          </h3>
          <p className="text-sm text-text-muted">
            {type} • {borough}
          </p>
        </div>
        <div className="flex gap-2">
          <span className={`priority-badge priority-${priority}`}>{priority}</span>
          <span className={`status-badge status-${status}`}>{status.replace('_', ' ')}</span>
        </div>
      </div>
      <p className="text-text-secondary text-sm leading-relaxed mb-4 flex-1">
        {description}
      </p>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pt-4 border-t border-border min-w-0">
        <div>
          <p className="text-sm text-text-muted m-0">{author}</p>
          <p className="text-xs text-text-muted mt-1">{new Date(createdAt).toLocaleDateString()}</p>
        </div>
        <div className="flex gap-2 w-full sm:w-auto min-w-0">
          {driveLink && (
            <button
              className="btn btn-secondary flex-1 sm:flex-none text-sm whitespace-nowrap overflow-hidden text-ellipsis w-full sm:w-auto"
              onClick={e => {
                e.stopPropagation();
                window.open(driveLink, '_blank');
              }}
              type="button"
            >
              📄 View Slides
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReportCard; 