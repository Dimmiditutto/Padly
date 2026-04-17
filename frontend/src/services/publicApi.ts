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

export async function getPublicConfig() {
  const response = await api.get<PublicConfig>('/public/config');
  return response.data;
}

export async function getAvailability(date: string, durationMinutes: number) {
  const response = await api.get<AvailabilityResponse>('/public/availability', {
    params: { date, duration_minutes: durationMinutes },
  });
  return response.data;
}

export async function createPublicBooking(payload: PublicBookingPayload) {
  const response = await api.post<PublicBookingCreateResponse>('/public/bookings', payload);
  return response.data;
}

export async function createPublicCheckout(bookingId: string) {
  const response = await api.post<PaymentInitResponse>(`/public/bookings/${bookingId}/checkout`);
  return response.data;
}

export async function getPublicBookingStatus(publicReference: string) {
  const response = await api.get<BookingStatusResponse>(`/public/bookings/${publicReference}/status`);
  return response.data;
}

export async function getPublicCancellation(token: string) {
  const response = await api.get<PublicCancellationResponse>(`/public/bookings/cancel/${token}`);
  return response.data;
}

export async function cancelPublicBooking(token: string) {
  const response = await api.post<PublicCancellationResponse>(`/public/bookings/cancel/${token}`);
  return response.data;
}