import api from './api';
import type { Conversation, ChatResponse } from '../types';

export async function createConversation(
  title: string = 'New Conversation',
  documentId?: string,
): Promise<Conversation> {
  const { data } = await api.post<Conversation>('/conversations', {
    title,
    document_id: documentId || null,
  });
  return data;
}

export async function listConversations(): Promise<Conversation[]> {
  const { data } = await api.get<Conversation[]>('/conversations');
  return data;
}

export async function getConversation(id: string): Promise<Conversation> {
  const { data } = await api.get<Conversation>(`/conversations/${id}`);
  return data;
}

export async function sendMessage(
  conversationId: string,
  content: string,
): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>(
    `/conversations/${conversationId}/messages`,
    { content, role: 'user' },
  );
  return data;
}

export async function deleteConversation(id: string): Promise<void> {
  await api.delete(`/conversations/${id}`);
}
