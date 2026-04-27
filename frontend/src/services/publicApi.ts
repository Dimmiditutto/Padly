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

function withTenantParams(tenantSlug?: string | null) {
  return tenantSlug ? { tenant: tenantSlug } : undefined;
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
  const response = await api.get<AvailabilityResponse>('/public/availability', {
    params: { date, duration_minutes: durationMinutes, ...withTenantParams(tenantSlug) },
  });
  return response.data;
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