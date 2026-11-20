import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams, useParams, useNavigate } from 'react-router-dom';
import {
  listConversations,
  getConversation,
  createConversation,
  sendMessage,
  deleteConversation,
} from '../services/chat';
import { listDocuments } from '../services/documents';
import type { Conversation, Message, Document } from '../types';
import ChatMessage from '../components/ChatMessage';
import {
  Send,
  Plus,
  Trash2,
  FileText,
  MessageSquare,
  Loader2,
  Bot,
  Sparkles,
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function ChatPage() {
  const [searchParams] = useSearchParams();
  const { conversationId: paramConvoId } = useParams<{ conversationId?: string }>();
  const navigate = useNavigate();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>(searchParams.get('doc') || '');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [fetchingConvo, setFetchingConvo] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [activeConversation?.messages, loading]);

  // Load conversations and documents
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [convos, docs] = await Promise.all([listConversations(), listDocuments()]);
      setConversations(convos);
      setDocuments(docs.filter((d) => d.status === 'completed'));

      // If URL has paramConvoId, load it; else load first convo or create one
      if (paramConvoId) {
        loadConversation(paramConvoId);
      } else if (convos.length > 0) {
        loadConversation(convos[0].id);
      } else {
        handleNewConversation();
      }
    } catch {
      toast.error('Failed to load chat data.');
    }
  };

  const loadConversation = async (id: string) => {
    setFetchingConvo(true);
    try {
      const convo = await getConversation(id);
      setActiveConversation(convo);
      if (convo.document_id) {
        setSelectedDocId(convo.document_id);
      }
    } catch {
      toast.error('Failed to load conversation.');
    } finally {
      setFetchingConvo(false);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConvo = await createConversation('New Conversation', selectedDocId || undefined);
      setConversations((prev) => [newConvo, ...prev]);
      setActiveConversation(newConvo);
      navigate(`/chat/${newConvo.id}`);
    } catch {
      toast.error('Failed to start new conversation.');
    }
  };

  const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation?')) return;
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversation?.id === id) {
        setActiveConversation(null);
        navigate('/chat');
      }
      toast.success('Conversation deleted.');
    } catch {
      toast.error('Failed to delete conversation.');
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading || !activeConversation) return;

    const userText = input.trim();
    setInput('');

    // Optimistically append user message
    const tempUserMsg: Message = {
      role: 'user',
      content: userText,
      created_at: new Date().toISOString(),
    };

    setActiveConversation((prev) =>
      prev ? { ...prev, messages: [...(prev.messages || []), tempUserMsg] } : null
    );

    setLoading(true);
    try {
      const chatResponse = await sendMessage(activeConversation.id, userText);
      const assistantMsg: Message = {
        role: 'assistant',
        content: chatResponse.content,
        citations: chatResponse.citations,
        created_at: new Date().toISOString(),
      };

      setActiveConversation((prev) =>
        prev ? { ...prev, messages: [...(prev.messages || []), assistantMsg] } : null
      );

      // Refresh conversations list to update title and timestamps
      const updatedList = await listConversations();
      setConversations(updatedList);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to generate answer.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-6rem)] bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
      {/* Sidebar: Conversations List */}
      <div className="w-72 bg-slate-50 border-r border-slate-200 flex flex-col flex-shrink-0">
        <div className="p-4 border-b border-slate-200">
          <button
            onClick={handleNewConversation}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition shadow-sm"
          >
            <Plus className="h-4 w-4" />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.map((convo) => {
            const active = activeConversation?.id === convo.id;
            return (
              <div
                key={convo.id}
                onClick={() => {
                  loadConversation(convo.id);
                  navigate(`/chat/${convo.id}`);
                }}
                className={`group flex items-center justify-between p-2.5 rounded-lg text-xs font-medium cursor-pointer transition ${
                  active
                    ? 'bg-indigo-100/70 text-indigo-900 font-semibold'
                    : 'text-slate-700 hover:bg-slate-200/60'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <MessageSquare className="h-4 w-4 text-slate-400 group-hover:text-indigo-600 flex-shrink-0" />
                  <span className="truncate">{convo.title}</span>
                </div>
                <button
                  onClick={(e) => handleDeleteConversation(e, convo.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-600 rounded transition"
                  title="Delete chat"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Chat Header / Document Selector */}
        <div className="p-4 border-b border-slate-200 bg-white flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-indigo-600" />
            <h2 className="font-bold text-slate-800 text-sm">
              {activeConversation?.title || 'Document Assistant'}
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-medium hidden sm:inline">Scope:</span>
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
            >
              <option value="">All Uploaded Documents</option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  📄 {doc.filename}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-slate-50/40">
          {fetchingConvo ? (
            <div className="flex justify-center items-center h-full text-slate-400">
              <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
            </div>
          ) : !activeConversation?.messages || activeConversation.messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center max-w-sm mx-auto p-6">
              <div className="p-4 bg-indigo-50 rounded-2xl text-indigo-600 mb-4">
                <Sparkles className="h-8 w-8" />
              </div>
              <h3 className="font-bold text-slate-900 text-base">Grounded Document Search</h3>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Ask any question about your indexed files. Answers are verified and cited with page-level sources.
              </p>
            </div>
          ) : (
            activeConversation.messages.map((msg, i) => <ChatMessage key={i} message={msg} />)
          )}

          {loading && (
            <div className="flex items-center gap-2 text-xs text-slate-500 p-3 bg-white border border-slate-200 rounded-xl max-w-xs animate-pulse">
              <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
              <span>Retrieving relevant chunks & formulating grounded answer...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Chat Input Bar */}
        <div className="p-4 bg-white border-t border-slate-200">
          <form onSubmit={handleSend} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your documents..."
              disabled={loading || !activeConversation}
              className="flex-1 px-4 py-2.5 text-sm border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={loading || !input.trim() || !activeConversation}
              className="inline-flex items-center justify-center px-4 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
