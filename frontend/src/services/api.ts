import axios, { AxiosError, AxiosResponse } from 'axios';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';

const rawBase = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '/api';
const API_BASE_URL = rawBase.replace(/\/+$/, '');

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  withCredentials: true,
});


function getWindowTenantSlug(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  return getTenantSlugFromSearchParams(new URLSearchParams(window.location.search));
}


api.interceptors.request.use((config) => {
  const tenantSlug = getWindowTenantSlug();
  if (!tenantSlug) {
    return config;
  }

  if (config.params instanceof URLSearchParams) {
    if (!config.params.get('tenant')) {
      config.params.set('tenant', tenantSlug);
    }
  } else {
    const currentParams = (config.params ?? {}) as Record<string, unknown>;
    if (!currentParams.tenant) {
      config.params = { ...currentParams, tenant: tenantSlug };
    }
  }

  const requestHeaders = new axios.AxiosHeaders(config.headers);
  if (!requestHeaders.get('x-tenant-slug')) {
    requestHeaders.set('x-tenant-slug', tenantSlug);
  }
  config.headers = requestHeaders;

  return config;
});

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    const requestUrl = String(error.config?.url || '');
    const isAdminRequest = requestUrl.includes('/admin');
    const isLoginRequest = requestUrl.includes('/admin/auth/login');

    if (error.response?.status === 401 && isAdminRequest && !isLoginRequest && window.location.pathname !== '/admin/login') {
      window.location.href = withTenantPath('/admin/login', getWindowTenantSlug());
    }

    return Promise.reject(error);
  }
);
