import type { PlayLevel } from '../types';
import { formatTimeValue } from './format';

export const DEFAULT_PLAY_ALIAS_SLUG = 'default-club';
const CLUB_PUBLIC_NAME_CACHE_PREFIX = 'play-club-name:';

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


export function buildPlayAccessPath(tenantSlug: string, groupToken?: string | null): string {
  if (!groupToken) {
    return buildClubPlayPath(tenantSlug, '/access');
  }
  return buildClubPlayPath(tenantSlug, `/access/${encodeURIComponent(groupToken)}`);
}


export function buildPlayMatchPath(tenantSlug: string, matchId: string): string {
  return buildClubPlayPath(tenantSlug, `/matches/${encodeURIComponent(matchId)}`);
}


export function buildAbsoluteAppUrl(path: string): string {
  return typeof window !== 'undefined' ? `${window.location.origin}${path}` : path;
}


export function buildAbsolutePlayMatchUrl(tenantSlug: string, shareToken: string): string {
  return buildAbsoluteAppUrl(buildPlayMatchPath(tenantSlug, shareToken));
}


function formatShareWeekdayDate(dateValue: string, timeZone?: string | null): string {
  const label = new Intl.DateTimeFormat('it-IT', {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
    ...(timeZone ? { timeZone } : {}),
  }).format(new Date(dateValue));
  return label.charAt(0).toUpperCase() + label.slice(1);
}


function shouldUseMobileWhatsAppLink(): boolean {
  if (typeof navigator === 'undefined') {
    return false;
  }
  return /Android|iPhone|iPad|iPod|Windows Phone|IEMobile|Opera Mini/i.test(navigator.userAgent || '');
}


export function buildPlayMatchShareText({
  startAt,
  endAt,
  levelRequested,
  shareUrl,
  clubName,
  participantNames = [],
  timeZone,
}: {
  startAt: string;
  endAt?: string | null;
  levelRequested: PlayLevel;
  shareUrl: string;
  clubName?: string | null;
  participantNames?: string[];
  timeZone?: string | null;
}): string {
  const normalizedParticipantNames = participantNames
    .map((name) => String(name).trim())
    .filter(Boolean);

  const participantLines = normalizedParticipantNames.map((name) => `🎾 ${name}`);

  const formattedStartTime = formatTimeValue(startAt, timeZone);
  const formattedEndTime = endAt ? formatTimeValue(endAt, timeZone) : null;
  const timeRangeLabel = formattedEndTime
    ? `🕒 *Ore ${formattedStartTime}/${formattedEndTime}*`
    : `🕒 *Ore ${formattedStartTime}*`;

  const lines = [
    '🎾 Match aperto',
    `📅 *${formatShareWeekdayDate(startAt, timeZone)}*`,
    timeRangeLabel,
    '',
    `📈 Livello ${formatPlayLevel(levelRequested)}`,
  ];

  if (clubName) {
    lines.push(`📍 ${clubName}`);
  }

  if (participantLines.length > 0) {
    lines.push('', ...participantLines);
  }

  lines.push('', 'Chi gioca?', shareUrl);

  return lines.join('\n');
}


export function buildPlayMatchWhatsAppUrl(options: {
  startAt: string;
  endAt?: string | null;
  levelRequested: PlayLevel;
  shareUrl: string;
  clubName?: string | null;
  participantNames?: string[];
  timeZone?: string | null;
}): string {
  const whatsAppBaseUrl = shouldUseMobileWhatsAppLink()
    ? 'https://wa.me/?text='
    : 'https://web.whatsapp.com/send?text=';
  return `${whatsAppBaseUrl}${encodeURIComponent(buildPlayMatchShareText(options))}`;
}


export function buildInviteAcceptPath(tenantSlug: string, inviteToken: string): string {
  return buildClubPlayPath(tenantSlug, `/invite/${encodeURIComponent(inviteToken)}`);
}


export function formatClubDisplayName(tenantSlug: string): string {
  if (String(tenantSlug).trim().toLowerCase() === DEFAULT_PLAY_ALIAS_SLUG) {
    return 'il tuo club';
  }

  return String(tenantSlug)
    .split('-')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}


export function rememberClubPublicName(tenantSlug: string, publicName: string | null | undefined): void {
  const normalizedTenantSlug = String(tenantSlug).trim().toLowerCase();
  const normalizedPublicName = String(publicName || '').trim();
  if (!normalizedTenantSlug || !normalizedPublicName || typeof window === 'undefined') {
    return;
  }

  try {
    window.localStorage.setItem(`${CLUB_PUBLIC_NAME_CACHE_PREFIX}${normalizedTenantSlug}`, normalizedPublicName);
  } catch {
    // Ignore storage failures: the UI can still fall back to runtime data.
  }
}


export function getRememberedClubPublicName(tenantSlug: string): string | null {
  const normalizedTenantSlug = String(tenantSlug).trim().toLowerCase();
  if (!normalizedTenantSlug || typeof window === 'undefined') {
    return null;
  }

  try {
    const cachedPublicName = window.localStorage.getItem(`${CLUB_PUBLIC_NAME_CACHE_PREFIX}${normalizedTenantSlug}`);
    return cachedPublicName?.trim() || null;
  } catch {
    return null;
  }
}


export function resolveClubDisplayName(tenantSlug: string, publicName?: string | null): string | null {
  const normalizedPublicName = String(publicName || '').trim();
  if (normalizedPublicName) {
    return normalizedPublicName;
  }

  const rememberedPublicName = getRememberedClubPublicName(tenantSlug);
  if (rememberedPublicName) {
    return rememberedPublicName;
  }

  if (String(tenantSlug).trim().toLowerCase() === DEFAULT_PLAY_ALIAS_SLUG) {
    return null;
  }

  return formatClubDisplayName(tenantSlug);
}