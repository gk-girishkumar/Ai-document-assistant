import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import type { ApiError } from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor — attach auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response interceptor — normalize errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      // Only redirect if not already on auth pages
      const path = window.location.pathname;
      if (path !== '/login' && path !== '/register') {
        window.location.href = '/login';
      }
    }

    const apiError: ApiError = {
      detail:
        error.response?.data?.detail ||
        error.message ||
        'An unexpected error occurred',
      status_code: error.response?.status,
      errors: error.response?.data?.errors,
    };

    return Promise.reject(apiError);
  },
);

export default api;
