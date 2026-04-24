import { api } from './api';
import type {
  CommunityInviteAcceptPayload,
  CommunityInviteAcceptResponse,
  PlayIdentifyPayload,
  PlayIdentifyResponse,
  PlayMatchDetailResponse,
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


export async function acceptCommunityInvite(inviteToken: string, payload: CommunityInviteAcceptPayload, tenantSlug?: string | null) {
  const response = await api.post<CommunityInviteAcceptResponse>(`/public/community-invites/${inviteToken}/accept`, payload, {
    params: withTenantParams(tenantSlug),
  });
  return response.data;
}