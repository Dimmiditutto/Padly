import axios, { AxiosError, AxiosResponse } from 'axios';

const rawBase = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '/api';
const API_BASE_URL = rawBase.replace(/\/+$/, '');

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  withCredentials: true,
});

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    const requestUrl = String(error.config?.url || '');
    const isAdminRequest = requestUrl.includes('/admin');
    const isLoginRequest = requestUrl.includes('/admin/auth/login');

    if (error.response?.status === 401 && isAdminRequest && !isLoginRequest && window.location.pathname !== '/admin/login') {
      window.location.href = '/admin/login';
    }

    return Promise.reject(error);
  }
);
