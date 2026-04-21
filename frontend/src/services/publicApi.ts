import { api } from './api';
import type {
  AvailabilityResponse,
  BookingStatusResponse,
  PaymentInitResponse,
  PublicCancellationResponse,
  PublicBookingCreateResponse,
  PublicBookingPayload,
  PublicConfig,
} from '../types';

function withTenantParams(tenantSlug?: string | null) {
  return tenantSlug ? { tenant: tenantSlug } : undefined;
}


export async function getPublicConfig(tenantSlug?: string | null) {
  const response = await api.get<PublicConfig>('/public/config', { params: withTenantParams(tenantSlug) });
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