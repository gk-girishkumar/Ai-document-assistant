import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Bot, User as UserIcon, BookOpen, ChevronDown, ChevronUp } from 'lucide-react';
import type { Message } from '../types';
import CitationCard from './CitationCard';

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isAssistant = message.role === 'assistant';
  const hasCitations = message.citations && message.citations.length > 0;
  const [citationsOpen, setCitationsOpen] = useState(true);

  return (
    <div className={`flex gap-4 p-4 rounded-xl ${isAssistant ? 'bg-white border border-slate-200' : 'bg-indigo-50/60'}`}>
      <div
        className={`h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          isAssistant ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-white'
        }`}
      >
        {isAssistant ? <Bot className="h-5 w-5" /> : <UserIcon className="h-5 w-5" />}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="font-semibold text-sm text-slate-800">
            {isAssistant ? 'DocAssistant AI' : 'You'}
          </span>
          {message.created_at && (
            <span className="text-xs text-slate-400">
              {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>

        <div className="prose prose-sm prose-slate max-w-none text-slate-800 leading-relaxed">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Source Citations */}
        {hasCitations && (
          <div className="mt-4 pt-3 border-t border-slate-100">
            <button
              onClick={() => setCitationsOpen(!citationsOpen)}
              className="flex items-center gap-1.5 text-xs font-semibold text-indigo-700 hover:text-indigo-800 mb-2"
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>Grounded Citations ({message.citations!.length})</span>
              {citationsOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>

            {citationsOpen && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                {message.citations!.map((cit, idx) => (
                  <CitationCard key={idx} citation={cit} index={idx} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
