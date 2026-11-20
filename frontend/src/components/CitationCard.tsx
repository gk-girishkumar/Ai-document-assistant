import React from 'react';
import { FileText, Bookmark } from 'lucide-react';
import type { Citation } from '../types';

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export default function CitationCard({ citation, index }: CitationCardProps) {
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs text-slate-700 hover:bg-indigo-50/40 hover:border-indigo-200 transition">
      <div className="flex items-center justify-between font-semibold text-slate-800 mb-1.5">
        <span className="flex items-center gap-1.5 truncate">
          <FileText className="h-3.5 w-3.5 text-indigo-600 flex-shrink-0" />
          <span className="truncate" title={citation.filename}>
            {citation.filename}
          </span>
        </span>
        {citation.page_number && (
          <span className="bg-white border border-slate-200 px-1.5 py-0.5 rounded text-[11px] font-medium text-slate-600">
            Page {citation.page_number}
          </span>
        )}
      </div>
      <p className="text-slate-600 leading-relaxed line-clamp-3 italic">
        "{citation.chunk_text}"
      </p>
    </div>
  );
}
