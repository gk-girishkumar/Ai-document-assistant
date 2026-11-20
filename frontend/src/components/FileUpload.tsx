import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, File, AlertCircle, CheckCircle } from 'lucide-react';
import { uploadDocument } from '../services/documents';
import toast from 'react-hot-toast';

interface FileUploadProps {
  onUploadSuccess: () => void;
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;
      const file = acceptedFiles[0];

      // Validate size (< 50MB)
      if (file.size > 50 * 1024 * 1024) {
        toast.error('File size exceeds the 50MB limit.');
        return;
      }

      setUploading(true);
      setProgress(0);

      try {
        await uploadDocument(file, (p) => setProgress(p));
        toast.success(`'${file.name}' uploaded successfully!`);
        onUploadSuccess();
      } catch (err: any) {
        const msg = err.response?.data?.detail || 'Failed to upload document.';
        toast.error(msg);
      } finally {
        setUploading(false);
        setProgress(0);
      }
    },
    [onUploadSuccess]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
    },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
        isDragActive
          ? 'border-indigo-500 bg-indigo-50/50 scale-[1.01]'
          : 'border-slate-300 hover:border-indigo-400 bg-white hover:bg-slate-50/50'
      } ${uploading ? 'pointer-events-none opacity-80' : ''}`}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center justify-center space-y-3">
        <div className="p-3 bg-indigo-50 rounded-full text-indigo-600">
          <UploadCloud className="h-8 w-8" />
        </div>
        <div>
          <p className="text-base font-semibold text-slate-800">
            {isDragActive ? 'Drop your document here...' : 'Upload PDF or Text Document'}
          </p>
          <p className="text-sm text-slate-500 mt-1">
            Drag & drop or click to select (PDF, TXT, MD up to 50MB)
          </p>
        </div>

        {uploading && (
          <div className="w-full max-w-xs mt-4">
            <div className="flex justify-between text-xs text-slate-600 mb-1">
              <span>Uploading...</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-indigo-600 h-2 transition-all duration-200"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
