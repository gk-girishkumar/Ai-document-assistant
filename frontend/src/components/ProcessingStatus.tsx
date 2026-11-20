import React from 'react';
import { Loader2, CheckCircle, AlertCircle, Clock } from 'lucide-react';

interface ProcessingStatusProps {
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

export default function ProcessingStatus({ status }: ProcessingStatusProps) {
  switch (status) {
    case 'completed':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
          <CheckCircle className="h-3.5 w-3.5 text-emerald-600" />
          Ready
        </span>
      );
    case 'processing':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200 animate-pulse">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-600" />
          Indexing
        </span>
      );
    case 'failed':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
          <AlertCircle className="h-3.5 w-3.5 text-rose-600" />
          Failed
        </span>
      );
    case 'pending':
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
          <Clock className="h-3.5 w-3.5 text-slate-500" />
          Pending
        </span>
      );
  }
}
