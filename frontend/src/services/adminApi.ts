import { api } from './api';
import type {
  AdminBookingStatusPayload,
  AdminBookingUpdatePayload,
  AdminCommunityInvitePayload,
  AdminCommunityInviteResponse,
  AdminDashboardFilters,
  AdminEvent,
  AdminManualBookingPayload,
  AdminSession,
  AdminSettings,
  AdminSettingsUpdatePayload,
  ApiMessage,
  BlackoutItem,
  BlackoutPayload,
  BookingDetail,
  BookingListResponse,
  BookingSummary,
  CourtListResponse,
  CourtSummary,
  CourtUpsertPayload,
  RecurringCancelResponse,
  RecurringCreateResponse,
  RecurringPreviewResponse,
  RecurringSeriesPayload,
  ReportResponse,
  SubscriptionStatusBanner,
} from '../types';

function withTenantParams(tenantSlug?: string | null) {
  return tenantSlug ? { tenant: tenantSlug } : undefined;
}


export async function loginAdmin(email: string, password: string, tenantSlug?: string | null) {
  const response = await api.post<AdminSession>('/admin/auth/login', { email, password }, { params: withTenantParams(tenantSlug) });
  return response.data;
}

export async function requestAdminPasswordReset(email: string, tenantSlug?: string | null) {
  const response = await api.post<ApiMessage>('/admin/auth/password-reset/request', { email }, { params: withTenantParams(tenantSlug) });
  return response.data;
}

export async function confirmAdminPasswordReset(token: string, newPassword: string, tenantSlug?: string | null) {
  const response = await api.post<ApiMessage>('/admin/auth/password-reset/confirm', { token, new_password: newPassword }, { params: withTenantParams(tenantSlug) });
  return response.data;
}

export async function logoutAdmin(tenantSlug?: string | null) {
  const response = await api.post<ApiMessage>('/admin/auth/logout', undefined, { params: withTenantParams(tenantSlug) });
  return response.data;
}

export async function getAdminSession(tenantSlug?: string | null) {
  const response = await api.get<AdminSession>('/admin/auth/me', { params: withTenantParams(tenantSlug) });
  return response.data;
}

export async function listAdminBookings(filters: AdminDashboardFilters) {
  const response = await api.get<BookingListResponse>('/admin/bookings', { params: filters });
  return response.data;
}

export async function getAdminBooking(bookingId: string) {
  const response = await api.get<BookingDetail>(`/admin/bookings/${bookingId}`);
  return response.data;
}

export async function createAdminBooking(payload: AdminManualBookingPayload) {
  const response = await api.post<BookingSummary>('/admin/bookings', payload);
  return response.data;
}

export async function cancelAdminBooking(bookingId: string) {
  const response = await api.post<ApiMessage>(`/admin/bookings/${bookingId}/cancel`);
  return response.data;
}

export async function updateAdminBookingStatus(bookingId: string, payload: AdminBookingStatusPayload) {
  const response = await api.post<BookingSummary>(`/admin/bookings/${bookingId}/status`, payload);
  return response.data;
}

export async function updateAdminBooking(bookingId: string, payload: AdminBookingUpdatePayload) {
  const response = await api.put<BookingDetail>(`/admin/bookings/${bookingId}`, payload);
  return response.data;
}

export async function markAdminBalancePaid(bookingId: string) {
  const response = await api.post<BookingSummary>(`/admin/bookings/${bookingId}/balance-paid`);
  return response.data;
}

export async function deleteAdminBooking(bookingId: string) {
  const response = await api.post<ApiMessage>(`/admin/bookings/${bookingId}/delete`);
  return response.data;
}

export async function getAdminReport() {
  const response = await api.get<ReportResponse>('/admin/reports/summary');
  return response.data;
}

export async function listAdminEvents() {
  const response = await api.get<AdminEvent[]>('/admin/events');
  return response.data;
}

export async function listBlackouts() {
  const response = await api.get<BlackoutItem[]>('/admin/blackouts');
  return response.data;
}

export async function createBlackout(payload: BlackoutPayload) {
  const response = await api.post<{ id: string; message: string }>('/admin/blackouts', payload);
  return response.data;
}

export async function previewRecurring(payload: RecurringSeriesPayload) {
  const response = await api.post<RecurringPreviewResponse>('/admin/recurring/preview', payload);
  return response.data;
}

export async function createRecurring(payload: RecurringSeriesPayload) {
  const response = await api.post<RecurringCreateResponse>('/admin/recurring', payload);
  return response.data;
}

export async function updateRecurringSeries(seriesId: string, payload: RecurringSeriesPayload) {
  const response = await api.put<RecurringCreateResponse>(`/admin/recurring/${seriesId}`, payload);
  return response.data;
}

export async function cancelRecurringOccurrences(bookingIds: string[]) {
  const response = await api.post<RecurringCancelResponse>('/admin/recurring/cancel-occurrences', { booking_ids: bookingIds });
  return response.data;
}

export async function cancelRecurringSeries(seriesId: string) {
  const response = await api.post<RecurringCancelResponse>(`/admin/recurring/${seriesId}/cancel`);
  return response.data;
}

export async function deleteRecurringSeries(seriesId: string) {
  const response = await api.post<ApiMessage>(`/admin/recurring/${seriesId}/delete`);
  return response.data;
}

export async function listAdminCourts() {
  const response = await api.get<CourtListResponse>('/admin/courts');
  return response.data;
}

export async function createAdminCourt(payload: CourtUpsertPayload) {
  const response = await api.post<CourtSummary>('/admin/courts', payload);
  return response.data;
}

export async function updateAdminCourt(courtId: string, payload: CourtUpsertPayload) {
  const response = await api.put<CourtSummary>(`/admin/courts/${courtId}`, payload);
  return response.data;
}

export async function getAdminSettings() {
  const response = await api.get<AdminSettings>('/admin/settings');
  return response.data;
}

export async function updateAdminSettings(payload: AdminSettingsUpdatePayload) {
  const response = await api.put<AdminSettings>('/admin/settings', payload);
  return response.data;
}

export async function createAdminCommunityInvite(payload: AdminCommunityInvitePayload) {
  const response = await api.post<AdminCommunityInviteResponse>('/admin/settings/community-invites', payload);
  return response.data;
}

export async function getSubscriptionStatus(tenantSlug?: string | null) {
  const response = await api.get<SubscriptionStatusBanner>('/admin/billing/status', { params: withTenantParams(tenantSlug) });
  return response.data;
}