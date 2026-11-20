import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import {
  FileText,
  MessageSquare,
  LogOut,
  User as UserIcon,
  Menu,
  X,
  Bot,
} from 'lucide-react';

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navigation = [
    { name: 'Documents', href: '/documents', icon: FileText },
    { name: 'AI Chat', href: '/chat', icon: MessageSquare },
  ];

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex md:w-64 md:flex-col md:inset-y-0 bg-slate-900 text-white">
        <div className="flex flex-col flex-grow pt-5 pb-4 overflow-y-auto">
          <div className="flex items-center flex-shrink-0 px-4 gap-3">
            <div className="p-2 bg-indigo-600 rounded-lg text-white">
              <Bot className="h-6 w-6" />
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight text-white">DocAssistant</span>
              <span className="block text-xs text-indigo-400 font-medium">Enterprise RAG</span>
            </div>
          </div>

          <nav className="mt-8 flex-1 px-3 space-y-1">
            {navigation.map((item) => {
              const active = location.pathname.startsWith(item.href);
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                    active
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <item.icon className="mr-3 h-5 w-5 flex-shrink-0" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* User profile & logout */}
          <div className="p-4 border-t border-slate-800">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-full bg-slate-700 flex items-center justify-center text-slate-300">
                <UserIcon className="h-5 w-5" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">
                  {user?.email || 'User'}
                </p>
                <p className="text-xs text-slate-400 capitalize">{user?.role || 'User'}</p>
              </div>
              <button
                onClick={logout}
                title="Log out"
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Mobile Header */}
        <header className="md:hidden flex items-center justify-between bg-slate-900 text-white px-4 py-3">
          <div className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-indigo-400" />
            <span className="font-bold">DocAssistant</span>
          </div>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-1 rounded-md text-slate-300 hover:text-white"
          >
            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-slate-900 text-white px-4 pt-2 pb-4 space-y-1 border-b border-slate-800">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center px-3 py-2 rounded-md text-base font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                <item.icon className="mr-3 h-5 w-5" />
                {item.name}
              </Link>
            ))}
            <button
              onClick={() => {
                logout();
                setMobileMenuOpen(false);
              }}
              className="flex w-full items-center px-3 py-2 rounded-md text-base font-medium text-rose-400 hover:bg-slate-800"
            >
              <LogOut className="mr-3 h-5 w-5" />
              Sign Out
            </button>
          </div>
        )}

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
