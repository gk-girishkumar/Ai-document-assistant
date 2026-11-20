import api from './api';
import type { User } from '../types';

const TOKEN_KEY = 'access_token';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getStoredToken();
}

export async function login(email: string, password: string): Promise<User> {
  const { data } = await api.post<{ access_token: string }>('/auth/login', {
    email,
    password,
  });

  storeToken(data.access_token);
  return getMe();
}

export async function register(email: string, password: string): Promise<User> {
  const { data } = await api.post<{ access_token: string }>('/auth/register', {
    email,
    password,
  });

  storeToken(data.access_token);
  return getMe();
}

export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout');
  } finally {
    clearToken();
  }
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/users/me');
  return data;
}
