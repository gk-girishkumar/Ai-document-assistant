import api from './api';
import type { Document, Chunk, DocumentUploadResponse } from '../types';

export async function listDocuments(): Promise<Document[]> {
  const { data } = await api.get<Document[]>('/documents');
  return data;
}

export async function getDocument(id: string): Promise<Document> {
  const { data } = await api.get<Document>(`/documents/${id}`);
  return data;
}

export async function uploadDocument(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await api.post<DocumentUploadResponse>('/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (event.total && onProgress) {
        onProgress(Math.round((event.loaded * 100) / event.total));
      }
    },
  });
  return data;
}

export async function deleteDocument(id: string): Promise<void> {
  await api.delete(`/documents/${id}`);
}

export async function processDocument(id: string): Promise<{ document_id: string; status: string; message: string }> {
  const { data } = await api.post(`/documents/${id}/process`);
  return data;
}

export async function getChunks(documentId: string): Promise<Chunk[]> {
  const { data } = await api.get<Chunk[]>(`/documents/${documentId}/chunks`);
  return data;
}
