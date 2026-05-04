import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { resolveTenantSlugFromLocation, withTenantPath } from '../utils/tenantContext';

const rawBase = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '/api';
const API_BASE_URL = rawBase.replace(/\/+$/, '');

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  withCredentials: true,
});

type TrackedRequestConfig = InternalAxiosRequestConfig & { __loaderTracked?: boolean };

const apiActivityListeners = new Set<(hasPendingRequests: boolean) => void>();
let pendingApiRequestCount = 0;

function notifyApiActivity() {
  const hasPendingRequests = pendingApiRequestCount > 0;
  for (const listener of apiActivityListeners) {
    listener(hasPendingRequests);
  }
}

function startTrackedRequest(config: TrackedRequestConfig) {
  if (config.__loaderTracked) {
    return;
  }

  config.__loaderTracked = true;
  pendingApiRequestCount += 1;
  notifyApiActivity();
}

function finishTrackedRequest(config?: TrackedRequestConfig) {
  if (!config?.__loaderTracked) {
    return;
  }

  config.__loaderTracked = false;
  pendingApiRequestCount = Math.max(0, pendingApiRequestCount - 1);
  notifyApiActivity();
}

export function subscribeToApiActivity(listener: (hasPendingRequests: boolean) => void) {
  apiActivityListeners.add(listener);
  return () => {
    apiActivityListeners.delete(listener);
  };
}

export function getHasPendingApiRequests() {
  return pendingApiRequestCount > 0;
}


function getWindowTenantSlug(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  return resolveTenantSlugFromLocation(window.location);
}


api.interceptors.request.use((config) => {
  startTrackedRequest(config as TrackedRequestConfig);
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
}, (error: AxiosError) => {
  finishTrackedRequest(error.config as TrackedRequestConfig | undefined);
  return Promise.reject(error);
});

api.interceptors.response.use(
  (response: AxiosResponse) => {
    finishTrackedRequest(response.config as TrackedRequestConfig);
    return response;
  },
  (error: AxiosError) => {
    finishTrackedRequest(error.config as TrackedRequestConfig | undefined);
    const requestUrl = String(error.config?.url || '');
    const isAdminRequest = requestUrl.includes('/admin');
    const isLoginRequest = requestUrl.includes('/admin/auth/login');

    if (error.response?.status === 401 && isAdminRequest && !isLoginRequest && window.location.pathname !== '/admin/login') {
      window.location.href = withTenantPath('/admin/login', getWindowTenantSlug());
    }

    return Promise.reject(error);
  }
);
