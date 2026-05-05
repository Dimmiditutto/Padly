import { describe, expect, it } from 'vitest';

import { buildPlayMatchShareText, resolveClubDisplayName } from './play';

describe('play utilities', () => {
  it('keeps the club section in the shared WhatsApp text', () => {
    const shareText = buildPlayMatchShareText({
      startAt: '2026-05-05T18:00:00Z',
      endAt: '2026-05-05T19:30:00Z',
      levelRequested: 'INTERMEDIATE_MEDIUM',
      shareUrl: 'https://padly.test/c/roma-club/play/matches/share-1',
      clubName: 'Roma Club',
      participantNames: ['Luca Smash'],
      timeZone: 'Europe/Rome',
    });

    expect(shareText).toContain('📣 MATCH APERTO');
    expect(shareText).toContain('📈 Livello Intermedio medio\n📍 Roma Club');
  });

  it('normalizes URL-like public names before sharing them', () => {
    const shareText = buildPlayMatchShareText({
      startAt: '2026-05-05T18:00:00Z',
      endAt: '2026-05-05T19:30:00Z',
      levelRequested: 'INTERMEDIATE_MEDIUM',
      shareUrl: 'https://padly.test/c/roma-club/play/matches/share-1',
      clubName: 'https://www.roma-club.it/',
      participantNames: ['Luca Smash'],
      timeZone: 'Europe/Rome',
    });

    expect(shareText).toContain('📍 roma-club.it');
    expect(shareText).not.toContain('📍 https://');
    expect(shareText).not.toContain('📍 www.');
  });

  it('normalizes URL-like public names when resolving the club display name', () => {
    expect(resolveClubDisplayName('roma-club', 'https://www.roma-club.it/')).toBe('roma-club.it');
  });
});