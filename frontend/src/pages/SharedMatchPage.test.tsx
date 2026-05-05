import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SharedMatchPage } from './SharedMatchPage';
import type { PlayMatchSummary, PlayPlayerSummary } from '../types';

vi.mock('../services/playApi', () => ({
  getPlaySession: vi.fn(),
  getPlaySharedMatch: vi.fn(),
  joinPlayMatch: vi.fn(),
}));

vi.mock('../services/publicApi', () => ({
  getPublicConfig: vi.fn(),
}));

vi.mock('../components/play/JoinConfirmModal', () => ({
  JoinConfirmModal: () => null,
}));

import { getPublicConfig } from '../services/publicApi';
import { getPlaySession, getPlaySharedMatch } from '../services/playApi';

const clipboardWriteText = vi.fn();
const windowOpenMock = vi.fn();

const basePlayer: PlayPlayerSummary = {
  id: 'player-1',
  profile_name: 'Luca Smash',
  phone: '+393331112233',
  declared_level: 'INTERMEDIATE_MEDIUM',
  privacy_accepted_at: '2026-04-24T10:00:00Z',
  created_at: '2026-04-24T10:00:00Z',
};

function buildSharedMatch(overrides: Partial<PlayMatchSummary> = {}): PlayMatchSummary {
  return {
    id: 'match-1',
    share_token: 'share-match-1',
    court_id: 'court-1',
    court_name: 'Campo Centrale',
    court_badge_label: 'Indoor',
    created_by_player_id: 'creator-1',
    creator_profile_name: 'Club Captain',
    start_at: '2026-05-10T18:00:00Z',
    end_at: '2026-05-10T19:30:00Z',
    duration_minutes: 90,
    status: 'OPEN',
    level_requested: 'INTERMEDIATE_MEDIUM',
    note: 'Porta palline nuove',
    participant_count: 2,
    available_spots: 2,
    joined_by_current_player: false,
    created_at: '2026-05-01T10:00:00Z',
    participants: [
      { player_id: 'p-1', profile_name: 'Luca Smash', declared_level: 'INTERMEDIATE_MEDIUM' },
      { player_id: 'p-2', profile_name: 'Marco Topspin', declared_level: 'INTERMEDIATE_MEDIUM' },
    ],
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/c/roma-club/play/matches/share-match-1']}>
      <Routes>
        <Route path='/c/:clubSlug/play/matches/:shareToken' element={<SharedMatchPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('SharedMatchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getPublicConfig).mockResolvedValue({
      app_name: 'PadelBooking',
      tenant_id: 'tenant-roma',
      tenant_slug: 'roma-club',
      public_name: 'Roma Club',
      timezone: 'Europe/Rome',
      currency: 'EUR',
      contact_email: 'desk@roma-club.example',
      support_email: 'help@roma-club.example',
      support_phone: '+39021234567',
      booking_hold_minutes: 15,
      cancellation_window_hours: 24,
      member_hourly_rate: 7,
      non_member_hourly_rate: 9,
      member_ninety_minute_rate: 10,
      non_member_ninety_minute_rate: 13,
      stripe_enabled: true,
      paypal_enabled: true,
    });
    vi.mocked(getPlaySession).mockResolvedValue({ player: null, notification_settings: null });
    Object.defineProperty(window.navigator, 'clipboard', {
      configurable: true,
      value: { writeText: clipboardWriteText.mockResolvedValue(undefined) },
    });
    vi.stubGlobal('open', windowOpenMock);
  });

  it('nasconde il join per un match full condiviso e non mostra dati personali assenti', async () => {
    vi.mocked(getPlaySharedMatch).mockResolvedValue({
      player: null,
      match: buildSharedMatch({
        status: 'FULL',
        participant_count: 4,
        available_spots: 0,
        creator_profile_name: null,
        note: null,
        participants: [],
      }),
    });

    renderPage();

    expect(await screen.findByText('Partita condivisa')).toBeInTheDocument();
    expect(screen.getByText('Questa partita e gia completa. Puoi ancora condividerla su WhatsApp, ma non e piu disponibile per il join.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Unisciti' })).not.toBeInTheDocument();
    expect(screen.queryByText('Giocatori attuali')).not.toBeInTheDocument();
    expect(screen.queryByText('Club Captain')).not.toBeInTheDocument();
    expect(screen.queryByText('Porta palline nuove')).not.toBeInTheDocument();
  });

  it('apre il dialog di share e costruisce il fallback WhatsApp', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({ player: basePlayer, notification_settings: null });
    vi.mocked(getPlaySharedMatch).mockResolvedValue({
      player: basePlayer,
      match: buildSharedMatch(),
    });

    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Condividi' }));
    expect(await screen.findByRole('dialog', { name: 'Condividi questa partita' })).toBeInTheDocument();
    const shareLinkInput = screen.getByLabelText('Link partita') as HTMLInputElement;
    expect(shareLinkInput.value).toContain('/c/roma-club/play/matches/share-match-1');

    await user.click(screen.getByRole('button', { name: 'Apri WhatsApp' }));
    await waitFor(() => expect(windowOpenMock).toHaveBeenCalled());

    const whatsAppUrl = windowOpenMock.mock.calls[0]?.[0];
    expect(typeof whatsAppUrl).toBe('string');
    expect(String(whatsAppUrl)).toContain('https://web.whatsapp.com/send?text=');
    const decoded = decodeURIComponent(String(whatsAppUrl).split('text=')[1] || '');
    expect(decoded).toContain('🕒 *Ore 20:00/21:30*');
    expect(decoded).toContain('📈 Livello Intermedio medio\n\nDove si gioca?\n📍 Roma Club');
    expect(decoded).toContain('📍 Roma Club\n\n🎾 Luca Smash');
    expect(decoded).toContain('🎾 Marco Topspin\n\nChi gioca?');
    expect(decoded).toContain('Chi gioca?');
    expect(decoded).toContain('📅 *');
    expect(decoded).toContain('📈 Livello Intermedio medio');
    expect(decoded).toContain('🎾 Luca Smash');
    expect(decoded).toContain('🎾 Marco Topspin');
    expect(decoded).toContain('📍 Roma Club');
  });

  it('mostra il fallback di copia manuale sulla shared page quando la clipboard non e disponibile', async () => {
    const user = userEvent.setup();
    Object.defineProperty(window.navigator, 'clipboard', {
      configurable: true,
      value: {},
    });
    vi.mocked(getPlaySession).mockResolvedValue({ player: basePlayer, notification_settings: null });
    vi.mocked(getPlaySharedMatch).mockResolvedValue({
      player: basePlayer,
      match: buildSharedMatch(),
    });

    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Condividi' }));
    expect((screen.getByLabelText('Link partita') as HTMLInputElement).value).toContain('/c/roma-club/play/matches/share-match-1');
    await user.click(screen.getByRole('button', { name: 'Copia link' }));

    expect(await screen.findByText('Copia manualmente il link qui sotto.')).toBeInTheDocument();
  });
});