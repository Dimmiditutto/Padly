import { api } from './api';
import type {
  CommunityInviteAcceptPayload,
  CommunityInviteAcceptResponse,
  PaymentInitResponse,
  PlayAccessResendResponse,
  PlayAccessStartPayload,
  PlayAccessStartResponse,
  PlayAccessVerifyPayload,
  PlayAccessVerifyResponse,
  PlayBookingCheckoutPayload,
  PlayCreateMatchPayload,
  PlayCreateMatchResponse,
  PlayIdentifyPayload,
  PlayIdentifyResponse,
  PlayNotificationPreferenceUpdatePayload,
  PlayNotificationPreferenceUpdateResponse,
  PlayNotificationReadResponse,
  PlayMatchDetailResponse,
  PlayMatchJoinResponse,
  PlayMatchLeaveResponse,
  PlayMatchUpdatePayload,
  PlayMatchUpdateResponse,
  PlayMatchesResponse,
  PlayPushSubscriptionPayload,
  PlayPushSubscriptionResponse,
  PlayPushSubscriptionRevokePayload,
  PlaySessionResponse,
} from '../types';

function withTenantParams(tenantSlug?: string | null) {
  return tenantSlug ? { tenant: tenantSlug } : undefined;
}


export async function getPlaySession(tenantSlug?: string | null) {
  const response = await api.get<PlaySessionResponse>('/play/me', { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function identifyPlayPlayer(payload: PlayIdentifyPayload, tenantSlug?: string | null) {
  const response = await api.post<PlayIdentifyResponse>('/play/identify', payload, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function getPlayMatches(tenantSlug?: string | null) {
  const response = await api.get<PlayMatchesResponse>('/play/matches', { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function getPlayMatchDetail(matchId: string, tenantSlug?: string | null) {
  const response = await api.get<PlayMatchDetailResponse>(`/play/matches/${matchId}`, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function getPlaySharedMatch(shareToken: string, tenantSlug?: string | null) {
  const response = await api.get<PlayMatchDetailResponse>(`/play/shared/${shareToken}`, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function createPlayMatch(payload: PlayCreateMatchPayload, tenantSlug?: string | null) {
  const response = await api.post<PlayCreateMatchResponse>('/play/matches', payload, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function joinPlayMatch(matchId: string, tenantSlug?: string | null) {
  const response = await api.post<PlayMatchJoinResponse>(`/play/matches/${matchId}/join`, undefined, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function startPlayBookingCheckout(bookingId: string, payload: PlayBookingCheckoutPayload, tenantSlug?: string | null) {
  const response = await api.post<PaymentInitResponse>(`/play/bookings/${bookingId}/checkout`, payload, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function leavePlayMatch(matchId: string, tenantSlug?: string | null) {
  const response = await api.post<PlayMatchLeaveResponse>(`/play/matches/${matchId}/leave`, undefined, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function updatePlayMatch(matchId: string, payload: PlayMatchUpdatePayload, tenantSlug?: string | null) {
  const response = await api.patch<PlayMatchUpdateResponse>(`/play/matches/${matchId}`, payload, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function cancelPlayMatch(matchId: string, tenantSlug?: string | null) {
  const response = await api.post<PlayMatchLeaveResponse>(`/play/matches/${matchId}/cancel`, undefined, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function updatePlayNotificationPreferences(payload: PlayNotificationPreferenceUpdatePayload, tenantSlug?: string | null) {
  const response = await api.put<PlayNotificationPreferenceUpdateResponse>('/play/notifications/preferences', payload, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function markPlayNotificationRead(notificationId: string, tenantSlug?: string | null) {
  const response = await api.post<PlayNotificationReadResponse>(`/play/notifications/${notificationId}/read`, undefined, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function registerPlayPushSubscription(payload: PlayPushSubscriptionPayload, tenantSlug?: string | null) {
  const response = await api.post<PlayPushSubscriptionResponse>('/play/push-subscriptions', payload, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function revokePlayPushSubscription(payload: PlayPushSubscriptionRevokePayload, tenantSlug?: string | null) {
  const response = await api.post<PlayPushSubscriptionResponse>('/play/push-subscriptions/revoke', payload, { params: withTenantParams(tenantSlug) });
  return response.data;
}


export async function acceptCommunityInvite(inviteToken: string, payload: CommunityInviteAcceptPayload, tenantSlug?: string | null) {
  const response = await api.post<CommunityInviteAcceptResponse>(`/public/community-invites/${inviteToken}/accept`, payload, {
    params: withTenantParams(tenantSlug),
  });
  return response.data;
}


export async function startPlayAccessOtp(payload: PlayAccessStartPayload, tenantSlug?: string | null) {
  const response = await api.post<PlayAccessStartResponse>('/public/play-access/start', payload, {
    params: withTenantParams(tenantSlug),
  });
  return response.data;
}


export async function verifyPlayAccessOtp(payload: PlayAccessVerifyPayload, tenantSlug?: string | null) {
  const response = await api.post<PlayAccessVerifyResponse>('/public/play-access/verify', payload, {
    params: withTenantParams(tenantSlug),
  });
  return response.data;
}


export async function resendPlayAccessOtp(challengeId: string, tenantSlug?: string | null) {
  const response = await api.post<PlayAccessResendResponse>(`/public/play-access/${challengeId}/resend`, undefined, {
    params: withTenantParams(tenantSlug),
  });
  return response.data;
}