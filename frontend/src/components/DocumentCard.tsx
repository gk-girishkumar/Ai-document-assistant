import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, Trash2, PlayCircle, MessageSquare } from 'lucide-react';
import type { Document } from '../types';
import ProcessingStatus from './ProcessingStatus';

interface DocumentCardProps {
  document: Document;
  onDelete: (id: string) => void;
  onProcess: (id: string) => void;
}

function formatBytes(bytes: number, decimals = 1) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export default function DocumentCard({
  document,
  onDelete,
  onProcess,
}: DocumentCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition p-5 flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-lg">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <Link
                to={`/documents/${document.id}`}
                className="font-semibold text-slate-800 hover:text-indigo-600 line-clamp-1 text-base transition"
                title={document.filename}
              >
                {document.filename}
              </Link>
              <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                <span>{formatBytes(document.file_size)}</span>
                <span>•</span>
                <span>{new Date(document.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
          <ProcessingStatus status={document.status} />
        </div>

        {document.error_message && (
          <p className="text-xs text-rose-600 bg-rose-50 p-2 rounded mt-3 line-clamp-2">
            Error: {document.error_message}
          </p>
        )}
      </div>

      <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          {document.status === 'pending' && (
            <button
              onClick={() => onProcess(document.id)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 font-medium text-xs transition"
            >
              <PlayCircle className="h-4 w-4" />
              Process
            </button>
          )}

          {document.status === 'completed' && (
            <Link
              to={`/chat?doc=${document.id}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 font-medium text-xs transition"
            >
              <MessageSquare className="h-4 w-4" />
              Ask AI
            </Link>
          )}
        </div>

        <button
          onClick={() => onDelete(document.id)}
          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
          title="Delete document"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
