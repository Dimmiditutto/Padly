import { api } from './api';
import type {
  AdminBookingStatusPayload,
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
  RecurringCreateResponse,
  RecurringPreviewResponse,
  RecurringSeriesPayload,
  ReportResponse,
} from '../types';

export async function loginAdmin(email: string, password: string) {
  const response = await api.post<AdminSession>('/admin/auth/login', { email, password });
  return response.data;
}

export async function logoutAdmin() {
  const response = await api.post<ApiMessage>('/admin/auth/logout');
  return response.data;
}

export async function getAdminSession() {
  const response = await api.get<AdminSession>('/admin/auth/me');
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

export async function markAdminBalancePaid(bookingId: string) {
  const response = await api.post<BookingSummary>(`/admin/bookings/${bookingId}/balance-paid`);
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

export async function getAdminSettings() {
  const response = await api.get<AdminSettings>('/admin/settings');
  return response.data;
}

export async function updateAdminSettings(payload: AdminSettingsUpdatePayload) {
  const response = await api.put<AdminSettings>('/admin/settings', payload);
  return response.data;
}import { api } from './api';
import type {
  AdminDashboardData,
  AdminDashboardFilters,
  AdminManualBookingPayload,
  AdminSession,
  AdminSettings,
  ApiMessage,
  BlackoutPayload,
  BookingListResponse,
  BookingSummary,
  RecurringCreateResponse,
  RecurringPreviewResponse,
  RecurringSeriesPayload,
  ReportResponse,
} from '../types';

export async function loginAdmin(email: string, password: string) {
  const response = await api.post<AdminSession>('/admin/auth/login', { email, password });
  return response.data;
}

export async function logoutAdmin() {
  const response = await api.post<ApiMessage>('/admin/auth/logout');
  return response.data;
}

export async function fetchAdminSession() {
  const response = await api.get<AdminSession>('/admin/auth/me');
  return response.data;
}

export async function fetchAdminBookings(filters: Partial<AdminDashboardFilters>) {
  const response = await api.get<BookingListResponse>('/admin/bookings', { params: filters });
  return response.data;
}

export async function fetchBookingDetail(bookingId: string) {
  const response = await api.get<BookingSummary>(`/admin/bookings/${bookingId}`);
  return response.data;
}

export async function fetchAdminReport() {
  const response = await api.get<ReportResponse>('/admin/reports/summary');
  return response.data;
}

export async function fetchAdminEvents() {
  const response = await api.get<AdminDashboardData['events']>('/admin/events');
  return response.data;
}

export async function fetchDashboardData(filters: Partial<AdminDashboardFilters>) {
  const [bookings, report, events] = await Promise.all([
    fetchAdminBookings(filters),
    fetchAdminReport(),
    fetchAdminEvents(),
  ]);

  return {
    bookings: bookings.items,
    report,
    events,
  } satisfies AdminDashboardData;
}

export async function createManualBooking(payload: AdminManualBookingPayload) {
  const response = await api.post<BookingSummary>('/admin/bookings', payload);
  return response.data;
}

export async function cancelAdminBooking(bookingId: string) {
  const response = await api.post<ApiMessage>(`/admin/bookings/${bookingId}/cancel`);
  return response.data;
}

export async function updateBookingStatus(bookingId: string, status: 'CONFIRMED' | 'CANCELLED' | 'COMPLETED' | 'NO_SHOW') {
  const response = await api.post<BookingSummary>(`/admin/bookings/${bookingId}/status`, { status });
  return response.data;
}

export async function markBalancePaid(bookingId: string) {
  const response = await api.post<BookingSummary>(`/admin/bookings/${bookingId}/balance-paid`);
  return response.data;
}

export async function createBlackout(payload: BlackoutPayload) {
  const response = await api.post<{ id: string; message: string }>('/admin/blackouts', payload);
  return response.data;
}

export async function previewRecurringSeries(payload: RecurringSeriesPayload) {
  const response = await api.post<RecurringPreviewResponse>('/admin/recurring/preview', payload);
  return response.data;
}

export async function createRecurringSeries(payload: RecurringSeriesPayload) {
  const response = await api.post<RecurringCreateResponse>('/admin/recurring', payload);
  return response.data;
}

export async function fetchAdminSettings() {
  const response = await api.get<AdminSettings>('/admin/settings');
  return response.data;
}