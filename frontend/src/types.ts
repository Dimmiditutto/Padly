export type BookingStatus = 'PENDING_PAYMENT' | 'CONFIRMED' | 'CANCELLED' | 'COMPLETED' | 'NO_SHOW' | 'EXPIRED';
export type PaymentProvider = 'STRIPE' | 'PAYPAL' | 'NONE';
export type PaymentStatus = 'UNPAID' | 'INITIATED' | 'PAID' | 'FAILED' | 'CANCELLED' | 'EXPIRED';

export interface ApiMessage {
  message: string;
}

export interface TimeSlot {
  slot_id: string;
  start_time: string;
  end_time: string;
  display_start_time: string;
  display_end_time: string;
  available: boolean;
  reason?: string | null;
}

export interface BookingSummary {
  id: string;
  public_reference: string;
  start_at: string;
  end_at: string;
  duration_minutes: number;
  booking_date_local: string;
  status: BookingStatus;
  deposit_amount: number;
  payment_provider: PaymentProvider;
  payment_status: PaymentStatus;
  customer_name?: string | null;
  customer_email?: string | null;
  customer_phone?: string | null;
  note?: string | null;
  created_by: string;
  source: string;
  created_at: string;
  cancelled_at?: string | null;
  completed_at?: string | null;
  no_show_at?: string | null;
  balance_paid_at?: string | null;
}

export interface BookingDetail extends BookingSummary {
  customer_email?: string | null;
  payment_reference?: string | null;
}

export interface PublicBookingSummary {
  id: string;
  public_reference: string;
  start_at: string;
  end_at: string;
  duration_minutes: number;
  booking_date_local: string;
  status: BookingStatus;
  deposit_amount: number;
  payment_provider: PaymentProvider;
  payment_status: PaymentStatus;
  created_at: string;
  cancelled_at?: string | null;
  completed_at?: string | null;
  no_show_at?: string | null;
  balance_paid_at?: string | null;
}

export interface PublicConfig {
  app_name: string;
  timezone: string;
  currency: string;
  booking_hold_minutes: number;
  cancellation_window_hours: number;
  stripe_enabled: boolean;
  paypal_enabled: boolean;
}

export interface AvailabilityResponse {
  date: string;
  duration_minutes: number;
  deposit_amount: number;
  slots: TimeSlot[];
}

export interface PublicBookingPayload {
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  note: string;
  booking_date: string;
  start_time: string;
  slot_id?: string | null;
  duration_minutes: number;
  payment_provider: PaymentProvider;
  privacy_accepted: boolean;
}

export interface PublicBookingCreateResponse {
  booking: PublicBookingSummary;
  checkout_ready: boolean;
  next_action_url?: string | null;
}

export interface PaymentInitResponse {
  booking_id: string;
  public_reference: string;
  provider: PaymentProvider;
  checkout_url: string;
  payment_status: PaymentStatus;
}

export interface BookingStatusResponse {
  booking: PublicBookingSummary;
}

export interface AdminEvent {
  id: string;
  event_type: string;
  actor: string;
  message: string;
  created_at: string;
}

export interface BookingListResponse {
  items: BookingSummary[];
  total: number;
}

export interface ReportResponse {
  total_bookings: number;
  confirmed_bookings: number;
  pending_bookings: number;
  cancelled_bookings: number;
  collected_deposits: number;
}

export interface AdminDashboardFilters {
  booking_date: string;
  status: string;
  payment_provider: string;
  customer: string;
}

export interface AdminBookingStatusPayload {
  status: 'CONFIRMED' | 'CANCELLED' | 'COMPLETED' | 'NO_SHOW';
}

export interface AdminManualBookingPayload {
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  note: string;
  booking_date: string;
  start_time: string;
  duration_minutes: number;
  payment_provider: PaymentProvider;
}

export interface BlackoutPayload {
  title: string;
  reason: string;
  start_at: string;
  end_at: string;
}

export interface BlackoutItem {
  id: string;
  title: string;
  reason?: string | null;
  start_at: string;
  end_at: string;
  is_active: boolean;
}

export interface RecurringOccurrence {
  booking_date: string;
  start_time: string;
  end_time: string;
  display_start_time: string;
  display_end_time: string;
  available: boolean;
  reason?: string | null;
}

export interface RecurringSeriesPayload {
  label: string;
  weekday: number;
  start_date: string;
  weeks_count: number;
  start_time: string;
  duration_minutes: number;
}

export interface RecurringPreviewResponse {
  occurrences: RecurringOccurrence[];
}

export interface RecurringCreateResponse {
  series_id: string;
  created_count: number;
  skipped_count: number;
  skipped: RecurringOccurrence[];
}

export interface AdminSession {
  email: string;
  full_name: string;
}

export interface AdminSettings {
  timezone: string;
  currency: string;
  booking_hold_minutes: number;
  cancellation_window_hours: number;
  reminder_window_hours: number;
  stripe_enabled: boolean;
  paypal_enabled: boolean;
}

export interface AdminSettingsUpdatePayload {
  booking_hold_minutes: number;
  cancellation_window_hours: number;
  reminder_window_hours: number;
}

export interface AdminDashboardData {
  bookings: BookingSummary[];
  report: ReportResponse;
  events: AdminEvent[];
}
