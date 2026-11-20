import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getDocument, getChunks, processDocument, deleteDocument } from '../services/documents';
import type { Document, Chunk } from '../types';
import ProcessingStatus from '../components/ProcessingStatus';
import {
  ArrowLeft,
  FileText,
  PlayCircle,
  MessageSquare,
  Trash2,
  Calendar,
  Layers,
  Database,
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [document, setDocument] = useState<Document | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    if (!id) return;
    try {
      const doc = await getDocument(id);
      setDocument(doc);
      if (doc.status === 'completed') {
        const chunkList = await getChunks(id);
        setChunks(chunkList);
      }
    } catch (err: any) {
      toast.error('Document not found or inaccessible.');
      navigate('/documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const handleProcess = async () => {
    if (!id) return;
    try {
      await processDocument(id);
      toast.success('Document indexing started.');
      loadData();
    } catch {
      toast.error('Failed to trigger processing.');
    }
  };

  const handleDelete = async () => {
    if (!id || !confirm('Permanently delete this document and its chunk vectors?')) return;
    try {
      await deleteDocument(id);
      toast.success('Document deleted.');
      navigate('/documents');
    } catch {
      toast.error('Failed to delete document.');
    }
  };

  if (loading || !document) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-slate-500">
        Loading document details...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Back button */}
      <Link
        to="/documents"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-indigo-600 transition"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Documents
      </Link>

      {/* Main Metadata Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl flex-shrink-0">
              <FileText className="h-8 w-8" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 break-all">{document.filename}</h1>
              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 mt-2">
                <span className="flex items-center gap-1">
                  <Database className="h-3.5 w-3.5" />
                  {(document.file_size / (1024 * 1024)).toFixed(2)} MB
                </span>
                <span className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" />
                  {new Date(document.created_at).toLocaleString()}
                </span>
                <span className="flex items-center gap-1">
                  <Layers className="h-3.5 w-3.5" />
                  {chunks.length} chunks indexed
                </span>
              </div>
            </div>
          </div>
          <ProcessingStatus status={document.status} />
        </div>

        {/* Action Buttons */}
        <div className="mt-6 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {document.status === 'pending' && (
              <button
                onClick={handleProcess}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
              >
                <PlayCircle className="h-4 w-4" />
                Process Document
              </button>
            )}

            {document.status === 'completed' && (
              <Link
                to={`/chat?doc=${document.id}`}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
              >
                <MessageSquare className="h-4 w-4" />
                Chat With Document
              </Link>
            )}
          </div>

          <button
            onClick={handleDelete}
            className="inline-flex items-center gap-1 px-3 py-2 text-rose-600 hover:bg-rose-50 rounded-lg text-sm font-medium transition"
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </button>
        </div>
      </div>

      {/* Chunks & Vector Store Section */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center justify-between">
          <span>Extracted Chunks ({chunks.length})</span>
          <span className="text-xs font-normal text-slate-500">Vector dimension: 384 (pgvector)</span>
        </h2>

        {chunks.length === 0 ? (
          <p className="text-sm text-slate-500 italic py-4 text-center">
            {document.status === 'completed'
              ? 'No text chunks extracted from this file.'
              : 'Process this document to extract and index chunks.'}
          </p>
        ) : (
          <div className="space-y-3">
            {chunks.map((chunk) => (
              <div
                key={chunk.id}
                className="p-3.5 rounded-lg border border-slate-200 bg-slate-50 text-xs text-slate-700 hover:bg-white transition"
              >
                <div className="flex justify-between font-semibold text-slate-600 mb-1.5">
                  <span>Chunk #{chunk.chunk_index}</span>
                  {chunk.page_number && (
                    <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded text-[11px]">
                      Page {chunk.page_number}
                    </span>
                  )}
                </div>
                <p className="leading-relaxed text-slate-800">{chunk.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
