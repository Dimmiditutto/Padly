import { api } from './api';
import type {
  CommunityInviteAcceptPayload,
  CommunityInviteAcceptResponse,
  PlayCreateMatchPayload,
  PlayCreateMatchResponse,
  PlayIdentifyPayload,
  PlayIdentifyResponse,
  PlayMatchDetailResponse,
  PlayMatchJoinResponse,
  PlayMatchLeaveResponse,
  PlayMatchUpdatePayload,
  PlayMatchUpdateResponse,
  PlayMatchesResponse,
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


export async function acceptCommunityInvite(inviteToken: string, payload: CommunityInviteAcceptPayload, tenantSlug?: string | null) {
  const response = await api.post<CommunityInviteAcceptResponse>(`/public/community-invites/${inviteToken}/accept`, payload, {
    params: withTenantParams(tenantSlug),
  });
  return response.data;
}