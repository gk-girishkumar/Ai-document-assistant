import React, { useEffect, useState, useMemo } from 'react';
import { listDocuments, deleteDocument, processDocument } from '../services/documents';
import type { Document } from '../types';
import DocumentCard from '../components/DocumentCard';
import FileUpload from '../components/FileUpload';
import { Search, FileQuestion, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const loadDocuments = async () => {
    try {
      const data = await listDocuments();
      setDocuments(data);
    } catch (err: any) {
      toast.error('Failed to load documents.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
    // Poll documents every 5 seconds to update indexing status
    const interval = setInterval(loadDocuments, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document and its citations?')) return;
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      toast.success('Document deleted.');
    } catch (err: any) {
      toast.error('Failed to delete document.');
    }
  };

  const handleProcess = async (id: string) => {
    try {
      await processDocument(id);
      toast.success('Processing started in background.');
      loadDocuments();
    } catch (err: any) {
      toast.error('Failed to start processing.');
    }
  };

  const filteredDocs = useMemo(() => {
    return documents.filter((d) =>
      d.filename.toLowerCase().includes(search.toLowerCase())
    );
  }, [documents, search]);

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Documents Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            Upload, index, and organize files for retrieval-augmented question answering.
          </p>
        </div>
        <button
          onClick={loadDocuments}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition self-start sm:self-auto"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Upload Dropzone */}
      <FileUpload onUploadSuccess={loadDocuments} />

      {/* Search & Filter Bar */}
      <div className="flex items-center justify-between gap-4 pt-4 border-t border-slate-200">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search documents by name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-sm border border-slate-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <span className="text-xs text-slate-500 font-medium">
          {filteredDocs.length} {filteredDocs.length === 1 ? 'document' : 'documents'}
        </span>
      </div>

      {/* Documents Grid / Empty State */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((n) => (
            <div key={n} className="bg-white rounded-xl border border-slate-200 p-6 animate-pulse space-y-4">
              <div className="h-5 bg-slate-200 rounded w-3/4"></div>
              <div className="h-4 bg-slate-100 rounded w-1/2"></div>
              <div className="h-8 bg-slate-100 rounded w-full"></div>
            </div>
          ))}
        </div>
      ) : filteredDocs.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredDocs.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              onDelete={handleDelete}
              onProcess={handleProcess}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-16 bg-white border border-dashed border-slate-200 rounded-2xl">
          <FileQuestion className="h-12 w-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">No documents found</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto mt-1">
            {search ? 'Try clearing your search query.' : 'Upload your first PDF, TXT or MD document above.'}
          </p>
        </div>
      )}
    </div>
  );
}
