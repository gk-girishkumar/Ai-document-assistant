export interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Chunk {
  id: string;
  document_id: string;
  text: string;
  page_number?: number;
  chunk_index: number;
  created_at: string;
}

export interface Document {
  id: string;
  owner_id: string;
  filename: string;
  mime_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  created_at: string;
  updated_at: string;
  chunks?: Chunk[];
}

export interface Citation {
  document_id: string;
  filename: string;
  page_number?: number;
  chunk_text: string;
}

export interface Message {
  id?: string;
  conversation_id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  created_at?: string;
}

export interface Conversation {
  id: string;
  owner_id: string;
  document_id?: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

export interface ChatResponse {
  content: string;
  citations: Citation[];
  confidence?: number;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  status: string;
  message: string;
}

export interface ApiError {
  detail: string;
  status_code?: number;
  errors?: Record<string, string[]>;
}
