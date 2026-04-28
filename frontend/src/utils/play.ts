import type { PlayLevel } from '../types';

export const DEFAULT_PLAY_ALIAS_SLUG = 'default-club';

export const PLAY_LEVEL_LABELS: Record<PlayLevel, string> = {
  NO_PREFERENCE: 'Nessuna preferenza',
  BEGINNER: 'Principiante',
  INTERMEDIATE_LOW: 'Intermedio basso',
  INTERMEDIATE_MEDIUM: 'Intermedio medio',
  INTERMEDIATE_HIGH: 'Intermedio alto',
  ADVANCED: 'Avanzato',
};

export const PLAY_LEVEL_OPTIONS = Object.entries(PLAY_LEVEL_LABELS).map(([value, label]) => ({
  value: value as PlayLevel,
  label,
}));


export function formatPlayLevel(level: PlayLevel | null | undefined): string {
  return PLAY_LEVEL_LABELS[level || 'NO_PREFERENCE'];
}


export function buildClubPlayPath(tenantSlug: string, suffix = ''): string {
  const normalizedTenantSlug = String(tenantSlug).trim().toLowerCase();
  const normalizedSuffix = suffix ? (suffix.startsWith('/') ? suffix : `/${suffix}`) : '';
  return `/c/${encodeURIComponent(normalizedTenantSlug)}/play${normalizedSuffix}`;
}


export function buildPlayMatchPath(tenantSlug: string, matchId: string): string {
  return buildClubPlayPath(tenantSlug, `/matches/${encodeURIComponent(matchId)}`);
}


export function buildInviteAcceptPath(tenantSlug: string, inviteToken: string): string {
  return buildClubPlayPath(tenantSlug, `/invite/${encodeURIComponent(inviteToken)}`);
}


export function formatClubDisplayName(tenantSlug: string): string {
  return String(tenantSlug)
    .split('-')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}