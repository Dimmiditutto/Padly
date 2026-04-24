export type BookingStatus = 'PENDING_PAYMENT' | 'CONFIRMED' | 'CANCELLED' | 'COMPLETED' | 'NO_SHOW' | 'EXPIRED';
export type PaymentProvider = 'STRIPE' | 'PAYPAL' | 'NONE';
export type PaymentStatus = 'UNPAID' | 'INITIATED' | 'PAID' | 'FAILED' | 'CANCELLED' | 'EXPIRED';
export type RefundStatus = 'NOT_REQUIRED' | 'PENDING' | 'SUCCEEDED' | 'FAILED';
export type BookingSource = 'PUBLIC' | 'ADMIN_MANUAL' | 'ADMIN_RECURRING';

export interface ApiMessage {
  message: string;
}

export interface TimeSlot {
  slot_id: string;
  court_id?: string | null;
  court_name?: string | null;
  court_badge_label?: string | null;
  start_time: string;
  end_time: string;
  display_start_time: string;
  display_end_time: string;
  available: boolean;
  reason?: string | null;
}

export interface CourtSummary {
  id: string;
  name: string;
  badge_label?: string | null;
  sort_order: number;
  is_active: boolean;
}

export interface CourtAvailability {
  court_id: string;
  court_name: string;
  badge_label?: string | null;
  slots: TimeSlot[];
}

export interface CourtUpsertPayload {
  name: string;
  badge_label?: string | null;
}

export interface BookingSummary {
  id: string;
  public_reference: string;
  court_id?: string | null;
  court_name?: string | null;
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
  source: BookingSource;
  recurring_series_id?: string | null;
  recurring_series_label?: string | null;
  recurring_series_start_date?: string | null;
  recurring_series_end_date?: string | null;
  recurring_series_weekday?: number | null;
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
  court_id?: string | null;
  court_name?: string | null;
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
  tenant_id: string;
  tenant_slug: string;
  public_name: string;
  timezone: string;
  currency: string;
  contact_email?: string | null;
  support_email?: string | null;
  support_phone?: string | null;
  booking_hold_minutes: number;
  cancellation_window_hours: number;
  member_hourly_rate: number;
  non_member_hourly_rate: number;
  member_ninety_minute_rate: number;
  non_member_ninety_minute_rate: number;
  stripe_enabled: boolean;
  paypal_enabled: boolean;
}

export interface AvailabilityResponse {
  date: string;
  duration_minutes: number;
  deposit_amount: number;
  slots: TimeSlot[];
  courts?: CourtAvailability[];
}

export interface PublicBookingPayload {
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  note: string;
  booking_date: string;
  court_id?: string | null;
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

export interface PublicCancellationResponse {
  booking: PublicBookingSummary;
  cancellable: boolean;
  cancellation_reason?: string | null;
  refund_required: boolean;
  refund_status: RefundStatus;
  refund_amount?: number | null;
  refund_message: string;
  message?: string | null;
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
  booking_date?: string;
  start_date?: string;
  end_date?: string;
  status: string;
  payment_provider: string;
  customer?: string;
  query?: string;
}

export interface AdminBookingStatusPayload {
  status: 'CONFIRMED' | 'CANCELLED' | 'COMPLETED' | 'NO_SHOW';
}

export interface AdminBookingUpdatePayload {
  booking_date: string;
  court_id?: string | null;
  start_time: string;
  slot_id?: string | null;
  duration_minutes: number;
  note: string;
}

export interface AdminManualBookingPayload {
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  note: string;
  booking_date: string;
  court_id?: string | null;
  start_time: string;
  slot_id?: string | null;
  duration_minutes: number;
  payment_provider: PaymentProvider;
}

export interface BlackoutPayload {
  court_id?: string | null;
  title: string;
  reason: string;
  start_at: string;
  end_at: string;
}

export interface BlackoutItem {
  id: string;
  court_id?: string | null;
  court_name?: string | null;
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
  court_id?: string | null;
  weekday: number;
  start_date: string;
  end_date: string;
  start_time: string;
  slot_id?: string | null;
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

export interface RecurringCancelResponse {
  message: string;
  cancelled_count: number;
  skipped_count: number;
  series_id?: string | null;
  booking_ids: string[];
}

export interface CourtListResponse {
  items: CourtSummary[];
}

export interface AdminSession {
  email: string;
  full_name: string;
  role: string;
  club_id: string;
  club_slug: string;
  club_public_name: string;
  timezone: string;
}

export interface AdminSettings {
  club_id: string;
  club_slug: string;
  public_name: string;
  timezone: string;
  currency: string;
  notification_email: string;
  support_email?: string | null;
  support_phone?: string | null;
  booking_hold_minutes: number;
  cancellation_window_hours: number;
  reminder_window_hours: number;
  member_hourly_rate: number;
  non_member_hourly_rate: number;
  member_ninety_minute_rate: number;
  non_member_ninety_minute_rate: number;
  stripe_enabled: boolean;
  paypal_enabled: boolean;
}

export interface AdminSettingsUpdatePayload {
  public_name?: string | null;
  notification_email?: string | null;
  support_email?: string | null;
  support_phone?: string | null;
  booking_hold_minutes: number;
  cancellation_window_hours: number;
  reminder_window_hours: number;
  member_hourly_rate: number;
  non_member_hourly_rate: number;
  member_ninety_minute_rate: number;
  non_member_ninety_minute_rate: number;
}

export interface AdminDashboardData {
  bookings: BookingSummary[];
  report: ReportResponse;
  events: AdminEvent[];
}

export type SubscriptionStatus = 'TRIALING' | 'ACTIVE' | 'PAST_DUE' | 'SUSPENDED' | 'CANCELLED';

export interface SubscriptionStatusBanner {
  status: SubscriptionStatus;
  plan_code: string;
  plan_name: string;
  trial_ends_at?: string | null;
  current_period_end?: string | null;
  is_access_blocked: boolean;
}
