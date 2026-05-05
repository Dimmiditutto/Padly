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
  public_booking_deposit_enabled?: boolean;
  public_booking_base_amount?: number;
  public_booking_included_minutes?: number;
  public_booking_extra_amount?: number;
  public_booking_extra_step_minutes?: number;
  public_booking_extras?: string[];
  stripe_enabled: boolean;
  paypal_enabled: boolean;
}

export interface PublicClubSummary {
  club_id: string;
  club_slug: string;
  public_name: string;
  public_address?: string | null;
  public_postal_code?: string | null;
  public_city?: string | null;
  public_province?: string | null;
  public_latitude?: number | null;
  public_longitude?: number | null;
  has_coordinates: boolean;
  distance_km?: number | null;
  courts_count: number;
  contact_email?: string | null;
  support_phone?: string | null;
  is_community_open: boolean;
  public_activity_score: number;
  recent_open_matches_count: number;
  public_activity_label: string;
  open_matches_three_of_four_count: number;
  open_matches_two_of_four_count: number;
  open_matches_one_of_four_count: number;
}

export interface PublicClubDirectoryResponse {
  query?: string | null;
  items: PublicClubSummary[];
}

export interface PublicClubOpenMatchSummary {
  id: string;
  court_name?: string | null;
  court_badge_label?: string | null;
  start_at: string;
  end_at: string;
  level_requested: PlayLevel;
  participant_count: number;
  available_spots: number;
  occupancy_label: string;
  missing_players_message: string;
}

export interface PublicClubDetailResponse {
  club: PublicClubSummary;
  timezone: string;
  support_email?: string | null;
  support_phone?: string | null;
  public_match_window_days: number;
  open_matches: PublicClubOpenMatchSummary[];
}

export interface MatchinnHomeCommunitiesResponse {
  items: PublicClubSummary[];
}

export interface MatchinnHomeOpenMatchItem {
  club: PublicClubSummary;
  match: PublicClubOpenMatchSummary;
}

export interface MatchinnHomeOpenMatchesResponse {
  items: MatchinnHomeOpenMatchItem[];
  location_source: 'query' | 'discovery' | 'none' | string;
  preferred_level?: PlayLevel | null;
}

export type PublicDiscoveryTimeSlot = 'morning' | 'lunch_break' | 'early_afternoon' | 'late_afternoon' | 'evening';
export type PublicDiscoveryNotificationKind = 'WATCHLIST_MATCH_THREE_OF_FOUR' | 'WATCHLIST_MATCH_TWO_OF_FOUR' | 'NEARBY_DIGEST';
export type NotificationChannel = 'IN_APP' | 'WEB_PUSH';
export type NotificationDeliveryStatus = 'SENT' | 'SKIPPED' | 'FAILED';

export interface PublicDiscoveryIdentifyPayload {
  preferred_level: PlayLevel;
  preferred_time_slots: PublicDiscoveryTimeSlot[];
  latitude?: number | null;
  longitude?: number | null;
  nearby_radius_km: number;
  nearby_digest_enabled: boolean;
  privacy_accepted: boolean;
}

export interface PublicDiscoveryPreferencesPayload {
  preferred_level: PlayLevel;
  preferred_time_slots: PublicDiscoveryTimeSlot[];
  latitude?: number | null;
  longitude?: number | null;
  nearby_radius_km: number;
  nearby_digest_enabled: boolean;
}

export interface PublicDiscoverySession {
  subscriber_id: string;
  preferred_level: PlayLevel;
  preferred_time_slots: PublicDiscoveryTimeSlot[];
  latitude?: number | null;
  longitude?: number | null;
  has_coordinates: boolean;
  nearby_radius_km: number;
  nearby_digest_enabled: boolean;
  last_identified_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PublicDiscoveryNotificationSummary {
  id: string;
  kind: PublicDiscoveryNotificationKind;
  channel: NotificationChannel;
  status: NotificationDeliveryStatus;
  title: string;
  message: string;
  payload?: Record<string, unknown> | null;
  sent_at?: string | null;
  read_at?: string | null;
  created_at: string;
}

export interface PublicDiscoveryMeResponse {
  subscriber?: PublicDiscoverySession | null;
  recent_notifications: PublicDiscoveryNotificationSummary[];
  unread_notifications_count: number;
}

export interface PublicClubWatchSummary {
  watch_id: string;
  club: PublicClubSummary;
  alert_match_three_of_four: boolean;
  alert_match_two_of_four: boolean;
  matching_open_match_count: number;
  created_at: string;
}

export interface PublicClubWatchResponse {
  item: PublicClubWatchSummary;
}

export interface PublicClubWatchlistResponse {
  items: PublicClubWatchSummary[];
}

export interface PublicClubContactRequestPayload {
  name: string;
  email?: string | null;
  phone?: string | null;
  preferred_level: PlayLevel;
  note?: string | null;
  privacy_accepted: boolean;
}

export interface PublicClubContactRequestResponse {
  request_id: string;
  message: string;
}

export interface AvailabilityResponse {
  date: string;
  duration_minutes: number;
  deposit_amount: number;
  deposit_required?: boolean;
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
  public_address?: string | null;
  public_postal_code?: string | null;
  public_city?: string | null;
  public_province?: string | null;
  public_latitude?: number | null;
  public_longitude?: number | null;
  is_community_open: boolean;
  booking_hold_minutes: number;
  cancellation_window_hours: number;
  reminder_window_hours: number;
  member_hourly_rate: number;
  non_member_hourly_rate: number;
  member_ninety_minute_rate: number;
  non_member_ninety_minute_rate: number;
  public_booking_deposit_enabled?: boolean;
  public_booking_base_amount?: number;
  public_booking_included_minutes?: number;
  public_booking_extra_amount?: number;
  public_booking_extra_step_minutes?: number;
  public_booking_extras?: string[];
  play_community_deposit_enabled: boolean;
  play_community_deposit_amount: number;
  play_community_payment_timeout_minutes: number;
  play_community_use_public_deposit?: boolean;
  stripe_enabled: boolean;
  paypal_enabled: boolean;
}

export interface AdminSettingsUpdatePayload {
  public_name?: string | null;
  notification_email?: string | null;
  support_email?: string | null;
  support_phone?: string | null;
  public_address?: string | null;
  public_postal_code?: string | null;
  public_city?: string | null;
  public_province?: string | null;
  public_latitude?: number | null;
  public_longitude?: number | null;
  is_community_open: boolean;
  booking_hold_minutes: number;
  cancellation_window_hours: number;
  reminder_window_hours: number;
  member_hourly_rate: number;
  non_member_hourly_rate: number;
  member_ninety_minute_rate: number;
  non_member_ninety_minute_rate: number;
  public_booking_deposit_enabled: boolean;
  public_booking_base_amount: number;
  public_booking_included_minutes: number;
  public_booking_extra_amount: number;
  public_booking_extra_step_minutes: number;
  public_booking_extras: string[];
  play_community_deposit_enabled: boolean;
  play_community_deposit_amount: number;
  play_community_payment_timeout_minutes: number;
  play_community_use_public_deposit: boolean;
}

export interface AdminCommunityInvitePayload {
  profile_name: string;
  phone: string;
  invited_level: PlayLevel;
}

export interface AdminCommunityInviteResponse {
  message: string;
  invite_id: string;
  invite_token: string;
  invite_path: string;
  profile_name: string;
  phone: string;
  invited_level: PlayLevel;
  expires_at: string;
}

export type AdminCommunityInviteStatus = 'ACTIVE' | 'USED' | 'EXPIRED' | 'REVOKED';

export interface AdminCommunityInviteSummary {
  id: string;
  profile_name: string;
  phone: string;
  invited_level: PlayLevel;
  created_at: string;
  expires_at: string;
  used_at?: string | null;
  revoked_at?: string | null;
  accepted_player_name?: string | null;
  status: AdminCommunityInviteStatus;
  can_revoke: boolean;
}

export interface AdminCommunityInviteListResponse {
  items: AdminCommunityInviteSummary[];
}

export interface AdminCommunityInviteRevokeResponse {
  message: string;
  item: AdminCommunityInviteSummary;
}

export interface AdminCommunityAccessLinkPayload {
  label?: string | null;
  max_uses?: number | null;
  expires_at?: string | null;
}

export interface AdminCommunityAccessLinkResponse {
  message: string;
  link_id: string;
  access_token: string;
  access_path: string;
  label?: string | null;
  max_uses?: number | null;
  used_count: number;
  expires_at?: string | null;
}

export type AdminCommunityAccessLinkStatus = 'ACTIVE' | 'SATURATED' | 'EXPIRED' | 'REVOKED';

export interface AdminCommunityAccessLinkSummary {
  id: string;
  label?: string | null;
  max_uses?: number | null;
  used_count: number;
  created_at: string;
  expires_at?: string | null;
  revoked_at?: string | null;
  status: AdminCommunityAccessLinkStatus;
  can_revoke: boolean;
}

export interface AdminCommunityAccessLinkListResponse {
  items: AdminCommunityAccessLinkSummary[];
}

export interface AdminCommunityAccessLinkRevokeResponse {
  message: string;
  item: AdminCommunityAccessLinkSummary;
}

export interface AdminPlayShareableMatchSummary {
  id: string;
  share_token: string;
  share_path: string;
  court_name?: string | null;
  start_at: string;
  end_at: string;
  status: PlayMatchStatus;
  level_requested: PlayLevel;
  participant_count: number;
  participant_names: string[];
}

export interface AdminPlayShareableMatchListResponse {
  items: AdminPlayShareableMatchSummary[];
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

export type PlayLevel = 'NO_PREFERENCE' | 'BEGINNER' | 'INTERMEDIATE_LOW' | 'INTERMEDIATE_MEDIUM' | 'INTERMEDIATE_HIGH' | 'ADVANCED';
export type PlayMatchStatus = 'OPEN' | 'FULL' | 'CANCELLED';
export type PlayAccessPurpose = 'INVITE' | 'GROUP' | 'DIRECT' | 'RECOVERY';

export interface PlayPlayerSummary {
  id: string;
  profile_name: string;
  phone: string;
  email?: string | null;
  email_verified_at?: string | null;
  declared_level: PlayLevel;
  privacy_accepted_at: string;
  created_at: string;
}

export interface MatchParticipantSummary {
  player_id: string;
  profile_name: string;
  declared_level: PlayLevel;
}

export type PlayNotificationChannel = 'IN_APP' | 'WEB_PUSH';
export type PlayNotificationKind = 'MATCH_THREE_OF_FOUR' | 'MATCH_TWO_OF_FOUR' | 'MATCH_ONE_OF_FOUR' | 'MATCH_COMPLETED' | 'MATCH_CANCELLED';

export interface PlayNotificationPreferenceSummary {
  in_app_enabled: boolean;
  web_push_enabled: boolean;
  notify_match_three_of_four: boolean;
  notify_match_two_of_four: boolean;
  notify_match_one_of_four: boolean;
  level_compatibility_only: boolean;
}

export interface PlayPushState {
  push_supported: boolean;
  public_vapid_key?: string | null;
  service_worker_path: string;
  has_active_subscription: boolean;
  active_subscription_count: number;
}

export interface PlayNotificationItem {
  id: string;
  match_id?: string | null;
  channel: PlayNotificationChannel;
  kind: PlayNotificationKind;
  title: string;
  message: string;
  payload?: Record<string, unknown> | null;
  sent_at?: string | null;
  read_at?: string | null;
  created_at: string;
}

export interface PlayNotificationSettings {
  preferences: PlayNotificationPreferenceSummary;
  push: PlayPushState;
  recent_notifications: PlayNotificationItem[];
  unread_notifications_count: number;
}

export interface PlayMatchSummary {
  id: string;
  share_token?: string | null;
  court_id: string;
  court_name?: string | null;
  court_badge_label?: string | null;
  created_by_player_id: string;
  creator_profile_name?: string | null;
  start_at: string;
  end_at: string;
  duration_minutes: number;
  status: PlayMatchStatus;
  level_requested: PlayLevel;
  note?: string | null;
  participant_count: number;
  available_spots: number;
  joined_by_current_player: boolean;
  created_at: string;
  participants: MatchParticipantSummary[];
}

export interface PlaySessionResponse {
  player?: PlayPlayerSummary | null;
  notification_settings?: PlayNotificationSettings | null;
}

export interface PlayIdentifyPayload {
  profile_name: string;
  phone: string;
  declared_level: PlayLevel;
  privacy_accepted: boolean;
}

export interface PlayIdentifyResponse {
  message: string;
  player: PlayPlayerSummary;
}

export interface CommunityInviteAcceptPayload {
  declared_level: PlayLevel;
  privacy_accepted: boolean;
}

export interface CommunityInviteAcceptResponse {
  message: string;
  player: PlayPlayerSummary;
}

export interface PlayAccessStartPayload {
  purpose: PlayAccessPurpose;
  email: string;
  profile_name?: string | null;
  phone?: string | null;
  declared_level: PlayLevel;
  privacy_accepted: boolean;
  invite_token?: string | null;
  group_token?: string | null;
}

export interface PlayAccessStartResponse {
  message: string;
  challenge_id: string;
  email_hint: string;
  expires_at: string;
  resend_available_at: string;
}

export interface PlayAccessVerifyPayload {
  challenge_id: string;
  otp_code: string;
}

export interface PlayAccessVerifyResponse {
  message: string;
  player: PlayPlayerSummary;
}

export interface PlayAccessResendResponse {
  message: string;
  challenge_id: string;
  email_hint: string;
  expires_at: string;
  resend_available_at: string;
}

export interface PlayMatchesResponse {
  player?: PlayPlayerSummary | null;
  open_matches: PlayMatchSummary[];
  my_matches: PlayMatchSummary[];
  pending_payment?: PlayPendingPaymentSummary | null;
}

export interface PlayMatchDetailResponse {
  player?: PlayPlayerSummary | null;
  match: PlayMatchSummary;
}

export interface PlayCreateMatchPayload {
  booking_date: string;
  court_id: string;
  start_time: string;
  slot_id?: string | null;
  duration_minutes: number;
  level_requested: PlayLevel;
  note?: string | null;
  force_create?: boolean;
}

export interface PlayCreateMatchResponse {
  created: boolean;
  message: string;
  match?: PlayMatchSummary | null;
  suggested_matches: PlayMatchSummary[];
}

export interface PlayBookingSummary {
  id: string;
  public_reference: string;
  court_id: string;
  start_at: string;
  end_at: string;
  status: BookingStatus;
  deposit_amount: number;
  payment_provider: PaymentProvider;
  payment_status: PaymentStatus;
  expires_at?: string | null;
  source: BookingSource;
}

export interface PlayBookingPaymentAction {
  required: boolean;
  payer_player_id: string;
  deposit_amount: number;
  payment_timeout_minutes: number;
  expires_at?: string | null;
  available_providers: PaymentProvider[];
  selected_provider?: PaymentProvider | null;
}

export interface PlayPendingPaymentSummary {
  booking: PlayBookingSummary;
  payment_action: PlayBookingPaymentAction;
}

export interface PlayMatchJoinResponse {
  action: string;
  message: string;
  match: PlayMatchSummary;
  booking?: PlayBookingSummary | null;
  payment_action?: PlayBookingPaymentAction | null;
}

export interface PlayBookingCheckoutPayload {
  provider?: PaymentProvider | null;
}

export interface PlayMatchLeaveResponse {
  action: string;
  message: string;
  match: PlayMatchSummary;
}

export interface PlayMatchUpdatePayload {
  level_requested?: PlayLevel;
  note?: string | null;
}

export interface PlayMatchUpdateResponse {
  action: string;
  message: string;
  match: PlayMatchSummary;
}

export interface PlayMatchSearchPlayersResponse {
  message: string;
  // Counts unique recipients notified by the manual search trigger, not raw channel/log fan-out.
  notifications_created: number;
  cooldown_remaining_seconds: number;
  match: PlayMatchSummary;
}

export interface PlayNotificationPreferenceUpdatePayload {
  in_app_enabled: boolean;
  web_push_enabled: boolean;
  notify_match_three_of_four: boolean;
  notify_match_two_of_four: boolean;
  notify_match_one_of_four: boolean;
  level_compatibility_only: boolean;
}

export interface PlayNotificationPreferenceUpdateResponse {
  message: string;
  settings: PlayNotificationSettings;
}

export interface PlayNotificationReadResponse {
  message: string;
  settings: PlayNotificationSettings;
}

export interface PlayPushSubscriptionPayload {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
  user_agent?: string | null;
}

export interface PlayPushSubscriptionRevokePayload {
  endpoint?: string | null;
}

export interface PlayPushSubscriptionResponse {
  message: string;
  settings: PlayNotificationSettings;
}
