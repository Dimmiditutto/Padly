import { api } from './api';
import type {
  ApiMessage,
  AvailabilityResponse,
  BookingStatusResponse,
  PaymentInitResponse,
  PublicClubContactRequestPayload,
  PublicClubContactRequestResponse,
  PublicClubDetailResponse,
  PublicClubDirectoryResponse,
  PublicClubWatchResponse,
  PublicClubWatchlistResponse,
  PublicCancellationResponse,
  PublicBookingCreateResponse,
  PublicBookingPayload,
  PublicConfig,
  PublicDiscoveryIdentifyPayload,
  PublicDiscoveryMeResponse,
  PublicDiscoveryPreferencesPayload,
  PublicDiscoverySession,
} from '../types';

const AVAILABILITY_CACHE_TTL_MS = 20_000;
const AVAILABILITY_CACHE_MAX_ENTRIES = 64;

const availabilityCache = new Map<string, { data: AvailabilityResponse; expiresAt: number }>();
const availabilityInFlight = new Map<string, Promise<AvailabilityResponse>>();

function withTenantParams(tenantSlug?: string | null) {
  return tenantSlug ? { tenant: tenantSlug } : undefined;
}

function buildAvailabilityCacheKey(date: string, durationMinutes: number, tenantSlug?: string | null) {
  return `${tenantSlug || 'default'}::${date}::${durationMinutes}`;
}

function addDaysToDateInput(dateValue: string, daysToAdd: number) {
  const [year, month, day] = dateValue.split('-').map(Number);
  if (!year || !month || !day) {
    return dateValue;
  }

  const normalizedDate = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
  normalizedDate.setUTCDate(normalizedDate.getUTCDate() + daysToAdd);
  return normalizedDate.toISOString().slice(0, 10);
}

function getCachedAvailability(cacheKey: string) {
  const cached = availabilityCache.get(cacheKey);
  if (!cached) {
    return null;
  }

  if (cached.expiresAt <= Date.now()) {
    availabilityCache.delete(cacheKey);
    return null;
  }

  availabilityCache.delete(cacheKey);
  availabilityCache.set(cacheKey, cached);
  return cached.data;
}

function setCachedAvailability(cacheKey: string, data: AvailabilityResponse) {
  availabilityCache.set(cacheKey, {
    data,
    expiresAt: Date.now() + AVAILABILITY_CACHE_TTL_MS,
  });

  while (availabilityCache.size > AVAILABILITY_CACHE_MAX_ENTRIES) {
    const oldestKey = availabilityCache.keys().next().value;
    if (!oldestKey) {
      break;
    }
    availabilityCache.delete(oldestKey);
  }
}


export async function getPublicConfig(tenantSlug?: string | null) {
  const response = await api.get<PublicConfig>('/public/config', { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function listPublicClubs(query?: string | null) {
  const response = await api.get<PublicClubDirectoryResponse>('/public/clubs', { params: query ? { query } : undefined });
  return response.data;
}


export async function listPublicClubsNearby(latitude: number, longitude: number, query?: string | null) {
  const response = await api.get<PublicClubDirectoryResponse>('/public/clubs/nearby', {
    params: {
      latitude,
      longitude,
      ...(query ? { query } : {}),
    },
  });
  return response.data;
}


export async function getPublicClubDetail(clubSlug: string, level?: string | null) {
  const response = await api.get<PublicClubDetailResponse>(`/public/clubs/${clubSlug}`, {
    params: level ? { level } : undefined,
  });
  return response.data;
}

export async function getPublicDiscoveryMe() {
  const response = await api.get<PublicDiscoveryMeResponse>('/public/discovery/me');
  return response.data;
}

export async function identifyPublicDiscovery(payload: PublicDiscoveryIdentifyPayload) {
  const response = await api.post<PublicDiscoveryMeResponse>('/public/discovery/identify', payload);
  return response.data;
}

export async function markPublicDiscoveryNotificationRead(notificationId: string) {
  const response = await api.post<PublicDiscoveryMeResponse>(`/public/discovery/notifications/${notificationId}/read`);
  return response.data;
}

export async function updatePublicDiscoveryPreferences(payload: PublicDiscoveryPreferencesPayload) {
  const response = await api.put<PublicDiscoverySession>('/public/discovery/preferences', payload);
  return response.data;
}

export async function listPublicWatchlist() {
  const response = await api.get<PublicClubWatchlistResponse>('/public/discovery/watchlist');
  return response.data;
}

export async function followPublicClub(clubSlug: string) {
  const response = await api.post<PublicClubWatchResponse>(`/public/discovery/watchlist/${clubSlug}`);
  return response.data;
}

export async function unfollowPublicClub(clubSlug: string) {
  const response = await api.delete<ApiMessage>(`/public/discovery/watchlist/${clubSlug}`);
  return response.data;
}

export async function createPublicClubContactRequest(clubSlug: string, payload: PublicClubContactRequestPayload) {
  const response = await api.post<PublicClubContactRequestResponse>(`/public/clubs/${clubSlug}/contact-request`, payload);
  return response.data;
}

export async function getAvailability(date: string, durationMinutes: number, tenantSlug?: string | null) {
  const cacheKey = buildAvailabilityCacheKey(date, durationMinutes, tenantSlug);
  const cached = getCachedAvailability(cacheKey);
  if (cached) {
    return cached;
  }

  const inFlight = availabilityInFlight.get(cacheKey);
  if (inFlight) {
    return inFlight;
  }

  const request = api.get<AvailabilityResponse>('/public/availability', {
    params: { date, duration_minutes: durationMinutes, ...withTenantParams(tenantSlug) },
  }).then((response) => {
    setCachedAvailability(cacheKey, response.data);
    return response.data;
  }).finally(() => {
    availabilityInFlight.delete(cacheKey);
  });

  availabilityInFlight.set(cacheKey, request);
  return request;
}

export async function prefetchAvailabilityWindow(startDate: string, durationMinutes: number, tenantSlug?: string | null, dayCount = 7) {
  const dates = Array.from({ length: Math.max(0, dayCount) }, (_, index) => addDaysToDateInput(startDate, index));
  await Promise.all(dates.map((date) => getAvailability(date, durationMinutes, tenantSlug).catch(() => null)));
}

export async function createPublicBooking(payload: PublicBookingPayload, tenantSlug?: string | null) {
  const response = await api.post<PublicBookingCreateResponse>('/public/bookings', payload, { params: withTenantParams(tenantSlug) });
  return response.data;
}

export async function createPublicCheckout(bookingId: string, tenantSlug?: string | null) {
  const response = await api.post<PaymentInitResponse>(`/public/bookings/${bookingId}/checkout`, undefined, { params: withTenantParams(tenantSlug) });
  return response.data;
}

export async function getPublicBookingStatus(publicReference: string, tenantSlug?: string | null) {
  const response = await api.get<BookingStatusResponse>(`/public/bookings/${publicReference}/status`, { params: withTenantParams(tenantSlug) });
  return response.data;
}

export async function getPublicCancellation(token: string, tenantSlug?: string | null) {
  const response = await api.get<PublicCancellationResponse>(`/public/bookings/cancel/${token}`, { params: withTenantParams(tenantSlug) });
  return response.data;
}

export async function cancelPublicBooking(token: string, tenantSlug?: string | null) {
  const response = await api.post<PublicCancellationResponse>(`/public/bookings/cancel/${token}`, undefined, { params: withTenantParams(tenantSlug) });
  return response.data;
}