import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import type { AvailabilityResponse, PlayMatchSummary, PlayNotificationSettings, PlayPlayerSummary } from '../types';

const originalLocation = window.location;

vi.mock('../services/playApi', () => ({
  acceptCommunityInvite: vi.fn(),
  cancelPlayMatch: vi.fn(),
  createPlayMatch: vi.fn(),
  getPlayMatches: vi.fn(),
  getPlaySession: vi.fn(),
  getPlaySharedMatch: vi.fn(),
  identifyPlayPlayer: vi.fn(),
  joinPlayMatch: vi.fn(),
  leavePlayMatch: vi.fn(),
  markPlayNotificationRead: vi.fn(),
  resendPlayAccessOtp: vi.fn(),
  registerPlayPushSubscription: vi.fn(),
  revokePlayMatchShareToken: vi.fn(),
  searchPlayMatchPlayers: vi.fn(),
  startPlayAccessOtp: vi.fn(),
  rotatePlayMatchShareToken: vi.fn(),
  revokePlayPushSubscription: vi.fn(),
  startPlayBookingCheckout: vi.fn(),
  updatePlayMatch: vi.fn(),
  updatePlayNotificationPreferences: vi.fn(),
  verifyPlayAccessOtp: vi.fn(),
}));

vi.mock('../utils/playPush', () => ({
  getBrowserPlayPushEndpoint: vi.fn(),
  isPlayPushSupported: vi.fn(() => true),
  subscribeBrowserToPlayPush: vi.fn(),
  unsubscribeBrowserFromPlayPush: vi.fn(),
}));

vi.mock('../pages/MatchinnHomePage', () => ({
  MatchinnHomePage: () => <div>MATCHINN HOME ROUTE</div>,
}));

vi.mock('../services/publicApi', () => ({
  getAvailability: vi.fn(),
  getPublicConfig: vi.fn(),
  prefetchAvailabilityWindow: vi.fn(),
}));

import { getAvailability } from '../services/publicApi';
import { getPublicConfig, prefetchAvailabilityWindow } from '../services/publicApi';
import {
  acceptCommunityInvite,
  cancelPlayMatch,
  createPlayMatch,
  getPlayMatches,
  getPlaySession,
  getPlaySharedMatch,
  identifyPlayPlayer,
  joinPlayMatch,
  leavePlayMatch,
  markPlayNotificationRead,
  resendPlayAccessOtp,
  registerPlayPushSubscription,
  revokePlayMatchShareToken,
  searchPlayMatchPlayers,
  startPlayAccessOtp,
  rotatePlayMatchShareToken,
  revokePlayPushSubscription,
  startPlayBookingCheckout,
  updatePlayMatch,
  updatePlayNotificationPreferences,
  verifyPlayAccessOtp,
} from '../services/playApi';
import { getBrowserPlayPushEndpoint, subscribeBrowserToPlayPush, unsubscribeBrowserFromPlayPush } from '../utils/playPush';

const basePlayer: PlayPlayerSummary = {
  id: 'player-1',
  profile_name: 'Luca Smash',
  phone: '+393331112233',
  declared_level: 'INTERMEDIATE_MEDIUM',
  privacy_accepted_at: '2026-04-24T10:00:00Z',
  created_at: '2026-04-24T10:00:00Z',
};

const baseNotificationSettings: PlayNotificationSettings = {
  preferences: {
    in_app_enabled: true,
    web_push_enabled: true,
    notify_match_three_of_four: true,
    notify_match_two_of_four: true,
    notify_match_one_of_four: false,
    level_compatibility_only: true,
  },
  push: {
    push_supported: true,
    public_vapid_key: 'BElocalPlayPushKey',
    service_worker_path: '/play-service-worker.js',
    has_active_subscription: false,
    active_subscription_count: 0,
  },
  recent_notifications: [],
  unread_notifications_count: 0,
};

const baseAvailability: AvailabilityResponse = {
  date: '2026-05-10',
  duration_minutes: 90,
  deposit_amount: 20,
  slots: [],
  courts: [
    {
      court_id: 'court-1',
      court_name: 'Campo 1',
      badge_label: 'Indoor',
      slots: [
        {
          slot_id: '2026-05-10T18:00:00Z',
          court_id: 'court-1',
          court_name: 'Campo 1',
          court_badge_label: 'Indoor',
          start_time: '18:00',
          end_time: '19:30',
          display_start_time: '18:00',
          display_end_time: '19:30',
          available: true,
          reason: null,
        },
        {
          slot_id: '2026-05-10T18:30:00Z',
          court_id: 'court-1',
          court_name: 'Campo 1',
          court_badge_label: 'Indoor',
          start_time: '18:30',
          end_time: '20:00',
          display_start_time: '18:30',
          display_end_time: '20:00',
          available: false,
          reason: 'Lo slot non e piu disponibile',
        },
      ],
    },
  ],
};

function buildMatch(id: string, note: string, participantCount: number): PlayMatchSummary {
  const participants = Array.from({ length: participantCount }, (_, index) => ({
    player_id: `${id}-player-${index + 1}`,
    profile_name: `Player ${index + 1}`,
    declared_level: 'INTERMEDIATE_MEDIUM' as const,
  }));

  return {
    id,
    share_token: `share-${id}`,
    court_id: 'court-1',
    court_name: 'Campo 1',
    court_badge_label: 'Indoor',
    created_by_player_id: `${id}-creator`,
    creator_profile_name: 'Club Captain',
    start_at: '2026-05-10T18:00:00Z',
    end_at: '2026-05-10T19:30:00Z',
    duration_minutes: 90,
    status: 'OPEN',
    level_requested: 'INTERMEDIATE_MEDIUM',
    note,
    participant_count: participantCount,
    available_spots: 4 - participantCount,
    joined_by_current_player: false,
    created_at: '2026-05-01T10:00:00Z',
    participants,
  };
}

function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </MemoryRouter>
  );
}

async function expandSection(user: ReturnType<typeof userEvent.setup>, title: string) {
  await user.click(screen.getByRole('button', { name: `Espandi ${title}` }));
}

describe('Play phase 2 pages', () => {
  beforeEach(() => {
    const assignMock = vi.fn();
    vi.clearAllMocks();
    window.localStorage.clear();
    vi.stubGlobal('location', { ...originalLocation, assign: assignMock });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    vi.mocked(getAvailability).mockResolvedValue({ ...baseAvailability });
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
    vi.mocked(prefetchAvailabilityWindow).mockResolvedValue(undefined);
    vi.mocked(getPlaySession).mockResolvedValue({ player: null, notification_settings: null });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: null,
      open_matches: [
        buildMatch('match-3of4', '3 su 4', 3),
        buildMatch('match-2of4', '2 su 4', 2),
        buildMatch('match-1of4', '1 su 4', 1),
      ],
      my_matches: [],
    });
    vi.mocked(identifyPlayPlayer).mockResolvedValue({
      message: 'Profilo play identificato',
      player: { ...basePlayer },
    });
    vi.mocked(acceptCommunityInvite).mockResolvedValue({
      message: 'Ingresso community completato',
      player: { ...basePlayer },
    });
    vi.mocked(startPlayAccessOtp).mockResolvedValue({
      message: 'Ti abbiamo inviato un codice via email. Inseriscilo per completare l’accesso.',
      challenge_id: 'challenge-1',
      email_hint: 'in*****@e***.com',
      expires_at: '2026-05-10T18:10:00Z',
      resend_available_at: '2026-05-10T18:00:00Z',
    });
    vi.mocked(verifyPlayAccessOtp).mockResolvedValue({
      message: 'Accesso community completato.',
      player: { ...basePlayer },
    });
    vi.mocked(resendPlayAccessOtp).mockResolvedValue({
      message: 'Ti abbiamo inviato un nuovo codice via email.',
      challenge_id: 'challenge-1',
      email_hint: 'in*****@e***.com',
      expires_at: '2026-05-10T18:12:00Z',
      resend_available_at: '2026-05-10T18:02:00Z',
    });
    vi.mocked(createPlayMatch).mockResolvedValue({
      created: true,
      message: 'Partita play creata correttamente.',
      match: buildMatch('match-created', 'created', 1),
      suggested_matches: [],
    });
    vi.mocked(joinPlayMatch).mockResolvedValue({
      action: 'JOINED',
      message: 'Ti sei unito alla partita.',
      match: buildMatch('match-shared', 'shared 4 su 4', 4),
      booking: null,
      payment_action: null,
    });
    vi.mocked(leavePlayMatch).mockResolvedValue({
      action: 'LEFT',
      message: 'Hai lasciato la partita.',
      match: buildMatch('match-left', 'left', 2),
    });
    vi.mocked(updatePlayMatch).mockResolvedValue({
      action: 'UPDATED',
      message: 'Partita aggiornata.',
      match: buildMatch('match-updated', 'updated', 2),
    });
    vi.mocked(cancelPlayMatch).mockResolvedValue({
      action: 'CANCELLED',
      message: 'Partita annullata.',
      match: { ...buildMatch('match-cancelled', 'cancelled', 1), status: 'CANCELLED' },
    });
    vi.mocked(updatePlayNotificationPreferences).mockResolvedValue({
      message: 'Preferenze notifiche aggiornate.',
      settings: { ...baseNotificationSettings },
    });
    vi.mocked(registerPlayPushSubscription).mockResolvedValue({
      message: 'Subscription web push registrata.',
      settings: {
        ...baseNotificationSettings,
        push: {
          ...baseNotificationSettings.push,
          has_active_subscription: true,
          active_subscription_count: 1,
        },
      },
    });
    vi.mocked(revokePlayPushSubscription).mockResolvedValue({
      message: 'Subscription web push revocata.',
      settings: { ...baseNotificationSettings },
    });
    vi.mocked(startPlayBookingCheckout).mockResolvedValue({
      booking_id: 'booking-play-1',
      public_reference: 'PB-PLAY-001',
      provider: 'STRIPE',
      checkout_url: '/checkout/play/stripe',
      payment_status: 'INITIATED',
    });
    vi.mocked(subscribeBrowserToPlayPush).mockResolvedValue({
      endpoint: 'https://push.example/sub-1',
      keys: { p256dh: 'p256dh-key', auth: 'auth-key' },
      user_agent: 'Vitest Browser',
    });
    vi.mocked(getBrowserPlayPushEndpoint).mockResolvedValue(null);
    vi.mocked(unsubscribeBrowserFromPlayPush).mockResolvedValue('https://push.example/sub-1');
    vi.mocked(getPlaySharedMatch).mockResolvedValue({
      player: null,
      match: buildMatch('match-shared', 'shared 3 su 4', 3),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('renders the canonical /c/:clubSlug/play route, preserves tenant slug and keeps the visual order of open matches', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Partite aperte' });
    await expandSection(user, 'Crea nuova partita');

    expect(getPlaySession).toHaveBeenCalledWith('roma-club');
    expect(getPlayMatches).toHaveBeenCalledWith('roma-club');
    await waitFor(() => expect(getAvailability).toHaveBeenCalledWith(expect.any(String), 90, 'roma-club'));

    const cards = await screen.findAllByTestId('play-open-match-card');
    expect(within(cards[0]).getByText('3 su 4')).toBeInTheDocument();
    expect(within(cards[1]).getByText('2 su 4')).toBeInTheDocument();
    expect(within(cards[2]).getByText('1 su 4')).toBeInTheDocument();
  });

  it('shows the same slot-grid language as the public booking page and keeps occupied slots visible', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Partite aperte' });
    await expandSection(user, 'Crea nuova partita');

    expect(await screen.findByText('Orari disponibili per campo')).toBeInTheDocument();
    expect(await screen.findByText('1 slot libero • 1 slot occupato')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: '18:00' })).toBeEnabled();
    expect(await screen.findByRole('button', { name: '18:30' })).toBeDisabled();
  });

  it('retries the initial availability load before showing an error in the create form', async () => {
    const user = userEvent.setup();

    vi.mocked(getAvailability)
      .mockRejectedValueOnce(new Error('temporary mobile timeout'))
      .mockResolvedValueOnce({ ...baseAvailability });

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Partite aperte' });
    await expandSection(user, 'Crea nuova partita');

    expect(await screen.findByText('Orari disponibili per campo')).toBeInTheDocument();
    expect(screen.queryByText('Non riesco a leggere gli slot disponibili per preparare una nuova partita.')).not.toBeInTheDocument();
    expect(getAvailability).toHaveBeenCalledTimes(2);
  });

  it('shows the club name in header, exposes 7 upcoming days and lets the user change duration', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Partite aperte' });
    await expandSection(user, 'Crea nuova partita');

    expect(screen.getByText((_, node) => node?.textContent === 'Community ROMA CLUB')).toBeInTheDocument();
    expect(screen.getByText('Trova match da completare ed organizza le tue partite!')).toBeInTheDocument();
    expect(screen.getByText('Prossimi 7 giorni')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /^Seleziona / })).toHaveLength(7);

    fireEvent.change(screen.getByLabelText('Durata'), { target: { value: '120' } });

    await waitFor(() => expect(getAvailability).toHaveBeenCalledWith(expect.any(String), 120, 'roma-club'));
    expect(prefetchAvailabilityWindow).toHaveBeenLastCalledWith(expect.any(String), 120, 'roma-club', 6);
  });

  it('uses the remembered club name for the default play alias when public config has no public name', async () => {
    window.localStorage.setItem('play-club-name:default-club', 'Padelsavona.it');

    vi.mocked(getPublicConfig).mockResolvedValue({
      app_name: 'PadelBooking',
      tenant_id: 'tenant-default',
      tenant_slug: 'default-club',
      public_name: '',
      timezone: 'Europe/Rome',
      currency: 'EUR',
      contact_email: 'desk@default-club.example',
      support_email: 'help@default-club.example',
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

    renderApp('/c/default-club/play');

    await screen.findByRole('heading', { name: 'Partite aperte' });

    expect(screen.getByText((_, node) => node?.textContent === 'Community PADELSAVONA.IT')).toBeInTheDocument();
    expect(screen.queryByText((_, node) => node?.textContent === 'Community IL TUO CLUB')).not.toBeInTheDocument();
    expect(screen.queryByText((_, node) => node?.textContent === 'Community DEFAULT CLUB')).not.toBeInTheDocument();
  });

  it('renders the main sections in the requested order for a recognized player', async () => {
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings, unread_notifications_count: 2 } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [],
    });

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Partite aperte' });

    const completareHeading = screen.getByRole('heading', { name: 'Partite da completare' });
    const mieHeading = screen.getByRole('heading', { name: 'Le mie partite' });
    const createHeading = screen.getByRole('heading', { name: 'Crea nuova partita' });
    const notificheHeading = screen.getByRole('heading', { name: 'Preferenze notifiche' });

    expect(completareHeading.compareDocumentPosition(mieHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(mieHeading.compareDocumentPosition(createHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(createHeading.compareDocumentPosition(notificheHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.queryByText('Profilo Matchinn attivo')).not.toBeInTheDocument();
    expect(screen.getByText('Scegli lo slot e gioca!')).toBeInTheDocument();
    expect(screen.getByText((_, node) => node?.textContent === 'Scegli cosa matchinn ti notifica')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Notifiche utente (2 da visualizzare)' })).toHaveClass('hero-icon-button-alert');
    expect(screen.queryByRole('button', { name: 'Utente' })).not.toBeInTheDocument();
  });

  it('redirects the /play alias to the canonical tenant route and keeps tenant propagation', async () => {
    renderApp('/play?tenant=roma-club');

    await screen.findByRole('heading', { name: 'Partite aperte' });
    expect(getPlayMatches).toHaveBeenCalledWith('roma-club');
  });

  it('shows a single clear community access path for anonymous users', async () => {
    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Partite aperte' });

    expect(screen.getByRole('link', { name: 'Entra o rientra nella community' })).toHaveAttribute('href', '/c/roma-club/play/access');
    expect(screen.queryByRole('link', { name: 'Apri accesso community' })).not.toBeInTheDocument();
  });

  it('asks for identification when an anonymous user tries to join a match', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play');

    await waitFor(() => expect(screen.getAllByRole('button', { name: 'Unisciti' }).length).toBeGreaterThan(0));
    await user.click(screen.getAllByRole('button', { name: 'Unisciti' })[0]);

    await screen.findByRole('heading', { name: 'Identificati per unirti alla partita' });
    await user.type(screen.getByLabelText('Nome profilo'), 'Luca Smash');
    await user.type(screen.getByLabelText('Telefono'), '+39 333 1112233');
    await user.click(screen.getByText('Accetto la privacy per essere riconosciuto nel club e usare il modulo play.'));
    await user.click(screen.getByRole('button', { name: 'Conferma profilo' }));

    await waitFor(() => expect(identifyPlayPlayer).toHaveBeenCalledWith(expect.objectContaining({
      profile_name: 'Luca Smash',
      phone: '+39 333 1112233',
      privacy_accepted: true,
    }), 'roma-club'));
    await waitFor(() => expect(joinPlayMatch).toHaveBeenCalledWith('match-3of4', 'roma-club'));
    expect(await screen.findByText('Ti sei unito alla partita.')).toBeInTheDocument();
  });

  it('continues the create flow immediately after identification', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Partite aperte' });
    await expandSection(user, 'Crea nuova partita');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Crea nuova partita' })).toBeEnabled());
    const noteField = screen.getByLabelText('Nota opzionale');
    await user.type(noteField, 'cerco ultimo giocatore');
    fireEvent.submit(noteField.closest('form')!);

    await screen.findByRole('heading', { name: 'Identificati per creare una nuova partita' });
    await user.type(screen.getByLabelText('Nome profilo'), 'Luca Smash');
    await user.type(screen.getByLabelText('Telefono'), '+39 333 1112233');
    await user.click(screen.getByText('Accetto la privacy per essere riconosciuto nel club e usare il modulo play.'));
    await user.click(screen.getByRole('button', { name: 'Conferma profilo' }));

    await waitFor(() => expect(createPlayMatch).toHaveBeenCalledWith(expect.objectContaining({
      court_id: 'court-1',
      start_time: '18:00',
      slot_id: '2026-05-10T18:00:00Z',
      duration_minutes: 90,
      level_requested: 'NO_PREFERENCE',
      note: 'cerco ultimo giocatore',
      force_create: false,
    }), 'roma-club'));
    expect(await screen.findByText('Partita play creata correttamente.')).toBeInTheDocument();
  });

  it('shows the backend detail when create fails', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [],
    });
    vi.mocked(createPlayMatch).mockRejectedValueOnce({
      response: {
        data: {
          detail: 'Puoi creare solo partite future',
        },
      },
    });

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Partite aperte' });
    await expandSection(user, 'Crea nuova partita');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Crea nuova partita' })).toBeEnabled());
    fireEvent.submit(screen.getByLabelText('Nota opzionale').closest('form')!);

    await waitFor(() => expect(createPlayMatch).toHaveBeenCalled());
    expect(await screen.findByText('Puoi creare solo partite future')).toBeInTheDocument();
  });

  it('requires privacy before accepting a community invite', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play/invite/invite-123');

    await screen.findByRole('heading', { name: 'Completa il tuo invito community' });
    await user.type(screen.getByLabelText('Email'), 'invite@example.com');
    await user.click(screen.getByRole('button', { name: 'Invia codice OTP' }));

    expect(startPlayAccessOtp).not.toHaveBeenCalled();
    expect(await screen.findByText('Per entrare nella community devi accettare la privacy.')).toBeInTheDocument();
  });

  it('redirects to Partite aperte after a successful community invite acceptance', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play/invite/invite-123');

    await screen.findByRole('heading', { name: 'Completa il tuo invito community' });
    await user.type(screen.getByLabelText('Email'), 'invite@example.com');
    await user.click(screen.getByText('Accetto la privacy per attivare o recuperare il mio profilo community su Matchinn.'));
    await user.click(screen.getByRole('button', { name: 'Invia codice OTP' }));

    await waitFor(() => expect(startPlayAccessOtp).toHaveBeenCalledWith(
      expect.objectContaining({ privacy_accepted: true }),
      'roma-club',
    ));
    expect(startPlayAccessOtp).toHaveBeenCalledWith(
      expect.objectContaining({
        purpose: 'INVITE',
        invite_token: 'invite-123',
        email: 'invite@example.com',
      }),
      'roma-club',
    );

    await user.type(await screen.findByLabelText('Codice OTP'), '123456');
    await user.click(screen.getByRole('button', { name: 'Verifica e accedi' }));

    await waitFor(() => expect(verifyPlayAccessOtp).toHaveBeenCalledWith(
      { challenge_id: 'challenge-1', otp_code: '123456' },
      'roma-club',
    ));
    await waitFor(() => expect(window.location.assign).toHaveBeenCalledWith('/c/roma-club/play'));
  });

  it('shows a clear error when the invite alias is opened without a tenant context', async () => {
    renderApp('/play/invite/invite-123');

    await screen.findByRole('heading', { name: 'Link invito incompleto' });
    expect(screen.getByText(/Questo invito play richiede il club corretto/)).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Torna al booking' })).toHaveLength(2);
    expect(screen.getAllByRole('link', { name: 'Torna al booking' })[0]).toHaveAttribute('href', '/booking');
    expect(screen.getAllByRole('link', { name: 'Torna alla home' })).toHaveLength(2);
    expect(screen.getAllByRole('link', { name: 'Torna alla home' })[0]).toHaveAttribute('href', '/');
    expect(acceptCommunityInvite).not.toHaveBeenCalled();
  });

  it('shows the branded fallback shell when the access alias is opened without a tenant context', async () => {
    renderApp('/play/access');

    await screen.findByRole('heading', { name: 'Link accesso incompleto' });
    expect(screen.getAllByRole('link', { name: 'Torna al booking' })).toHaveLength(2);
    expect(screen.getAllByRole('link', { name: 'Torna al booking' })[0]).toHaveAttribute('href', '/booking');
    expect(screen.getAllByRole('link', { name: 'Torna alla home' })).toHaveLength(2);
    expect(screen.getAllByRole('link', { name: 'Torna alla home' })[0]).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'Torna alla home Matchinn' })).toHaveAttribute('href', '/');
  });

  it('shows a clear error when the match alias is opened without a tenant context', async () => {
    renderApp('/play/matches/share-match-shared');

    await screen.findByRole('heading', { name: 'Link partita incompleto' });
    expect(screen.getByText(/Questo link partita richiede il club corretto/)).toBeInTheDocument();
    expect(getPlaySharedMatch).not.toHaveBeenCalled();
  });

  it('shows the shared match page for an anonymous visitor and requests identification before join', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play/matches/share-match-shared');

    await screen.findByRole('heading', { name: 'Partita condivisa' });
    expect(getPlaySharedMatch).toHaveBeenCalledWith('share-match-shared', 'roma-club');
    expect(await screen.findByText('Per unirti da questa pagina devi prima attivare il tuo profilo sul club corrente.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Identificati per unirti' }));
    expect(await screen.findByRole('heading', { name: 'Identificati per proseguire dal link condiviso' })).toBeInTheDocument();
  });

  it('shows the shared match page for a recognized player', async () => {
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlaySharedMatch).mockResolvedValue({
      player: { ...basePlayer },
      match: buildMatch('match-shared', 'shared 3 su 4', 3),
    });

    renderApp('/c/roma-club/play/matches/share-match-shared');

    await screen.findByRole('heading', { name: 'Partita condivisa' });
    expect(await screen.findByText(/Profilo attivo:/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Unisciti' })).toBeInTheDocument();
  });

  it('shows a sober error when the shared link is no longer available', async () => {
    vi.mocked(getPlaySharedMatch).mockRejectedValueOnce({ response: { data: { detail: 'Link partita non disponibile' } } });

    renderApp('/c/roma-club/play/matches/share-match-shared');

    await screen.findByRole('heading', { name: 'Partita condivisa' });
    expect(await screen.findByText('Link partita non disponibile')).toBeInTheDocument();
  });

  it('shows compatible matches before forcing a new create flow', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [buildMatch('match-3of4', '3 su 4', 3)],
      my_matches: [],
    });
    vi.mocked(createPlayMatch)
      .mockResolvedValueOnce({
        created: false,
        message: 'Esistono gia partite compatibili da completare prima di aprirne una nuova.',
        match: null,
        suggested_matches: [buildMatch('match-suggested', '3 su 4 compatibile', 3)],
      })
      .mockResolvedValueOnce({
        created: true,
        message: 'Partita play creata correttamente.',
        match: buildMatch('match-created', 'created', 1),
        suggested_matches: [],
      });

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Partite aperte' });
    await expandSection(user, 'Crea nuova partita');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Crea nuova partita' })).toBeEnabled());
    fireEvent.submit(screen.getByLabelText('Nota opzionale').closest('form')!);

    expect(await screen.findByRole('heading', { name: 'Prima completa queste partite compatibili' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Crea comunque una nuova partita' }));

    await waitFor(() => expect(createPlayMatch).toHaveBeenNthCalledWith(2, expect.objectContaining({ force_create: true }), 'roma-club'));
    expect(await screen.findByText('Partita play creata correttamente.')).toBeInTheDocument();
  });

  it('continues shared onboarding and joins after identification', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play/matches/share-match-shared');

    await screen.findByRole('heading', { name: 'Partita condivisa' });
    await user.click(screen.getByRole('button', { name: 'Identificati per unirti' }));
    await user.type(screen.getByLabelText('Nome profilo'), 'Luca Smash');
    await user.type(screen.getByLabelText('Telefono'), '+39 333 1112233');
    await user.click(screen.getByText('Accetto la privacy per essere riconosciuto nel club e usare il modulo play.'));
    await user.click(screen.getByRole('button', { name: 'Conferma profilo' }));

    await waitFor(() => expect(joinPlayMatch).toHaveBeenCalledWith('match-shared', 'roma-club'));
    expect(await screen.findByText('Ti sei unito alla partita.')).toBeInTheDocument();
  });

  it('shows the community deposit CTA for the fourth player and starts the selected checkout', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches)
      .mockResolvedValueOnce({
        player: { ...basePlayer },
        open_matches: [buildMatch('match-3of4', '3 su 4', 3)],
        my_matches: [],
      })
      .mockResolvedValueOnce({
        player: { ...basePlayer },
        open_matches: [],
        my_matches: [],
        pending_payment: {
          booking: {
            id: 'booking-play-1',
            public_reference: 'PB-PLAY-001',
            court_id: 'court-1',
            start_at: '2026-05-10T18:00:00Z',
            end_at: '2026-05-10T19:30:00Z',
            status: 'PENDING_PAYMENT',
            deposit_amount: 12.5,
            payment_provider: 'NONE',
            payment_status: 'UNPAID',
            expires_at: '2026-05-10T17:45:00Z',
            source: 'ADMIN_MANUAL',
          },
          payment_action: {
            required: true,
            payer_player_id: basePlayer.id,
            deposit_amount: 12.5,
            payment_timeout_minutes: 45,
            expires_at: '2026-05-10T17:45:00Z',
            available_providers: ['STRIPE', 'PAYPAL'],
            selected_provider: null,
          },
        },
      });
    vi.mocked(joinPlayMatch).mockResolvedValueOnce({
      action: 'COMPLETED',
      message: 'Quarto player confermato: partita completata. Versa ora la caparra community per confermare definitivamente il campo.',
      match: { ...buildMatch('match-3of4', '4 su 4', 4), status: 'FULL', participant_count: 4, available_spots: 0 },
      booking: {
        id: 'booking-play-1',
        public_reference: 'PB-PLAY-001',
        court_id: 'court-1',
        start_at: '2026-05-10T18:00:00Z',
        end_at: '2026-05-10T19:30:00Z',
        status: 'PENDING_PAYMENT',
        deposit_amount: 12.5,
        payment_provider: 'NONE',
        payment_status: 'UNPAID',
        expires_at: '2026-05-10T17:45:00Z',
        source: 'ADMIN_MANUAL',
      },
      payment_action: {
        required: true,
        payer_player_id: basePlayer.id,
        deposit_amount: 12.5,
        payment_timeout_minutes: 45,
        expires_at: '2026-05-10T17:45:00Z',
        available_providers: ['STRIPE', 'PAYPAL'],
        selected_provider: null,
      },
    });

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Partite aperte' });
    await user.click(screen.getAllByRole('button', { name: 'Unisciti' })[0]);

    expect(await screen.findByRole('heading', { name: 'Caparra community da completare' })).toBeInTheDocument();
    expect(screen.getByText(/Prenotazione PB-PLAY-001/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Paga con Stripe' }));

    await waitFor(() => expect(startPlayBookingCheckout).toHaveBeenCalledWith('booking-play-1', { provider: 'STRIPE' }, 'roma-club'));
    expect(window.location.assign).toHaveBeenCalledWith('/checkout/play/stripe');
  });

  it('recovers the community deposit CTA after reload from the play matches payload', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [buildMatch('match-3of4', '3 su 4', 3)],
      my_matches: [],
      pending_payment: {
        booking: {
          id: 'booking-play-recover',
          public_reference: 'PB-PLAY-RECOVER',
          court_id: 'court-1',
          start_at: '2026-05-10T18:00:00Z',
          end_at: '2026-05-10T19:30:00Z',
          status: 'PENDING_PAYMENT',
          deposit_amount: 12.5,
          payment_provider: 'PAYPAL',
          payment_status: 'INITIATED',
          expires_at: '2026-05-10T17:45:00Z',
          source: 'ADMIN_MANUAL',
        },
        payment_action: {
          required: true,
          payer_player_id: basePlayer.id,
          deposit_amount: 12.5,
          payment_timeout_minutes: 45,
          expires_at: '2026-05-10T17:45:00Z',
          available_providers: ['PAYPAL'],
          selected_provider: 'PAYPAL',
        },
      },
    });
    vi.mocked(startPlayBookingCheckout).mockResolvedValueOnce({
      booking_id: 'booking-play-recover',
      public_reference: 'PB-PLAY-RECOVER',
      provider: 'PAYPAL',
      checkout_url: '/checkout/play/paypal',
      payment_status: 'INITIATED',
    });

    renderApp('/c/roma-club/play');

    expect(await screen.findByRole('heading', { name: 'Caparra community da completare' })).toBeInTheDocument();
    expect(screen.getByText(/Prenotazione PB-PLAY-RECOVER/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Paga con PayPal' }));

    await waitFor(() => expect(startPlayBookingCheckout).toHaveBeenCalledWith('booking-play-recover', { provider: 'PAYPAL' }, 'roma-club'));
    expect(window.location.assign).toHaveBeenCalledWith('/checkout/play/paypal');
  });

  it('shows leave action for joined personal matches and calls the leave endpoint', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [
        {
          ...buildMatch('match-my-open', 'mia partita', 3),
          joined_by_current_player: true,
          participants: [
            {
              player_id: basePlayer.id,
              profile_name: basePlayer.profile_name,
              declared_level: basePlayer.declared_level,
            },
          ],
        },
      ],
    });

    renderApp('/c/roma-club/play');

    const card = (await screen.findAllByTestId('play-my-match-card'))[0];
    expect(within(card).getByRole('button', { name: 'Lascia' })).toBeInTheDocument();
    expect(within(card).queryByRole('button', { name: 'Modifica' })).not.toBeInTheDocument();

    await user.click(within(card).getByRole('button', { name: 'Lascia' }));

    await waitFor(() => expect(leavePlayMatch).toHaveBeenCalledWith('match-my-open', 'roma-club'));
    expect(await screen.findByText('Hai lasciato la partita.')).toBeInTheDocument();
  });

  it('lets the creator update level and note from the manage panel', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [
        {
          ...buildMatch('match-my-edit', 'nota iniziale', 2),
          created_by_player_id: basePlayer.id,
          creator_profile_name: basePlayer.profile_name,
          joined_by_current_player: true,
        },
      ],
    });

    renderApp('/c/roma-club/play');

    const card = (await screen.findAllByTestId('play-my-match-card'))[0];
    await user.click(within(card).getByRole('button', { name: 'Modifica' }));

    await screen.findByRole('heading', { name: 'Gestisci il tuo match' });
    await user.selectOptions(screen.getByLabelText('Livello match'), 'ADVANCED');
    await user.clear(screen.getByLabelText('Nota'));
    await user.type(screen.getByLabelText('Nota'), 'solo partita mista');
    await user.click(screen.getByRole('button', { name: 'Salva modifiche' }));

    await waitFor(() => expect(updatePlayMatch).toHaveBeenCalledWith('match-my-edit', {
      level_requested: 'ADVANCED',
      note: 'solo partita mista',
    }, 'roma-club'));
    expect(await screen.findByText('Partita aggiornata.')).toBeInTheDocument();
  });

  it('lets the creator cancel an open match from personal actions', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [
        {
          ...buildMatch('match-my-cancel', 'da annullare', 2),
          created_by_player_id: basePlayer.id,
          creator_profile_name: basePlayer.profile_name,
          joined_by_current_player: true,
        },
      ],
    });

    renderApp('/c/roma-club/play');

    const card = (await screen.findAllByTestId('play-my-match-card'))[0];
    await user.click(within(card).getByRole('button', { name: 'Annulla match' }));

    await waitFor(() => expect(window.confirm).toHaveBeenCalled());
    await waitFor(() => expect(cancelPlayMatch).toHaveBeenCalledWith('match-my-cancel', 'roma-club'));
    expect(await screen.findByText('Partita annullata.')).toBeInTheDocument();
  });

  it('lets the creator rotate and disable the shared link from personal actions', async () => {
    const user = userEvent.setup();
    const creatorMatch = {
      ...buildMatch('match-my-share', 'da condividere', 2),
      created_by_player_id: basePlayer.id,
      creator_profile_name: basePlayer.profile_name,
      joined_by_current_player: true,
    };
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches)
      .mockResolvedValueOnce({
        player: { ...basePlayer },
        open_matches: [],
        my_matches: [creatorMatch],
      })
      .mockResolvedValueOnce({
        player: { ...basePlayer },
        open_matches: [],
        my_matches: [{ ...creatorMatch, share_token: 'share-rotated' }],
      })
      .mockResolvedValueOnce({
        player: { ...basePlayer },
        open_matches: [],
        my_matches: [{ ...creatorMatch, share_token: null }],
      });
    vi.mocked(rotatePlayMatchShareToken).mockResolvedValue({
      action: 'ROTATED',
      message: 'Link partita rigenerato.',
      match: { ...creatorMatch, share_token: 'share-rotated' },
    });
    vi.mocked(revokePlayMatchShareToken).mockResolvedValue({
      action: 'REVOKED',
      message: 'Link partita disattivato.',
      match: { ...creatorMatch, share_token: null },
    });

    renderApp('/c/roma-club/play');

    const card = (await screen.findAllByTestId('play-my-match-card'))[0];
    await user.click(within(card).getByRole('button', { name: 'Rigenera link' }));

    await waitFor(() => expect(rotatePlayMatchShareToken).toHaveBeenCalledWith('match-my-share', 'roma-club'));
    expect(await screen.findByText('Link partita rigenerato.')).toBeInTheDocument();

    const updatedCard = (await screen.findAllByTestId('play-my-match-card'))[0];
    await user.click(within(updatedCard).getByRole('button', { name: 'Disattiva link' }));

    await waitFor(() => expect(window.confirm).toHaveBeenCalled());
    await waitFor(() => expect(revokePlayMatchShareToken).toHaveBeenCalledWith('match-my-share', 'roma-club'));
    expect(await screen.findByText('Link partita disattivato.')).toBeInTheDocument();
    expect(await within((await screen.findAllByTestId('play-my-match-card'))[0]).findByText('Link disattivato')).toBeInTheDocument();
  });

  it('opens the share dialog from play cards and builds the WhatsApp fallback text', async () => {
    const user = userEvent.setup();
    const openMock = vi.fn();
    const creatorMatch = {
      ...buildMatch('match-my-share', 'da condividere', 2),
      created_by_player_id: basePlayer.id,
      creator_profile_name: basePlayer.profile_name,
      joined_by_current_player: true,
    };
    vi.stubGlobal('open', openMock);
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [creatorMatch],
    });

    renderApp('/c/roma-club/play');

    const card = (await screen.findAllByTestId('play-my-match-card'))[0];
    await user.click(within(card).getByRole('button', { name: 'Condividi' }));

    expect(await screen.findByRole('dialog', { name: 'Condividi questa partita' })).toBeInTheDocument();
    const shareLinkInput = screen.getByLabelText('Link partita') as HTMLInputElement;
    expect(shareLinkInput.value).toContain('/c/roma-club/play/matches/share-match-my-share');

    await user.click(screen.getByRole('button', { name: 'Apri WhatsApp' }));
    await waitFor(() => expect(openMock).toHaveBeenCalled());

    const whatsAppUrl = openMock.mock.calls[0]?.[0];
    expect(String(whatsAppUrl)).toContain('https://wa.me/?text=');
    const decoded = decodeURIComponent(String(whatsAppUrl).split('text=')[1] || '');
    expect(decoded).toContain('Chi gioca?');
    expect(decoded).toContain('🎾 Player 1');
    expect(decoded).toContain('🎾 Player 2');
    expect(decoded).toContain('📍 Roma Club');
  });

  it('lets a joined participant share the same match link and falls back to manual copy when clipboard is unavailable', async () => {
    const user = userEvent.setup();
    const clipboardWriteText = vi.fn().mockRejectedValueOnce(new Error('clipboard unavailable'));
    Object.defineProperty(window.navigator, 'clipboard', {
      configurable: true,
      value: { writeText: clipboardWriteText },
    });
    const participantMatch = {
      ...buildMatch('match-my-share-participant', 'gia dentro', 2),
      created_by_player_id: 'creator-other-player',
      creator_profile_name: 'Club Captain',
      joined_by_current_player: true,
      participants: [
        {
          player_id: basePlayer.id,
          profile_name: basePlayer.profile_name,
          declared_level: basePlayer.declared_level,
        },
        {
          player_id: 'creator-other-player',
          profile_name: 'Club Captain',
          declared_level: 'INTERMEDIATE_MEDIUM' as const,
        },
      ],
    };
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [participantMatch],
    });

    renderApp('/c/roma-club/play');

    const card = (await screen.findAllByTestId('play-my-match-card'))[0];
    expect(within(card).getByRole('button', { name: 'Condividi' })).toBeInTheDocument();
    expect(within(card).queryByRole('button', { name: 'Cerca giocatori' })).not.toBeInTheDocument();

    await user.click(within(card).getByRole('button', { name: 'Condividi' }));

    const shareLinkInput = screen.getByLabelText('Link partita') as HTMLInputElement;
    await user.click(screen.getByRole('button', { name: 'Copia link' }));

    await waitFor(() => expect(clipboardWriteText).toHaveBeenCalledWith(shareLinkInput.value));
    expect(await screen.findByText('Copia manualmente il link qui sotto.')).toBeInTheDocument();
  });

  it('lets the creator trigger Cerca giocatori from personal match actions', async () => {
    const user = userEvent.setup();
    const creatorMatch = {
      ...buildMatch('match-my-search', 'cerca player', 1),
      created_by_player_id: basePlayer.id,
      creator_profile_name: basePlayer.profile_name,
      joined_by_current_player: true,
    };
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [creatorMatch],
    });
    vi.mocked(searchPlayMatchPlayers).mockResolvedValue({
      message: 'Abbiamo avvisato 3 player compatibili.',
      notifications_created: 3,
      cooldown_remaining_seconds: 0,
      match: creatorMatch,
    });

    renderApp('/c/roma-club/play');

    const card = (await screen.findAllByTestId('play-my-match-card'))[0];
    await user.click(within(card).getByRole('button', { name: 'Cerca giocatori' }));

    await waitFor(() => expect(searchPlayMatchPlayers).toHaveBeenCalledWith('match-my-search', 'roma-club'));
    expect(await screen.findByText('Abbiamo avvisato 3 player compatibili.')).toBeInTheDocument();
  });

  it('shows an informative feedback when Cerca giocatori finds no new compatible players', async () => {
    const user = userEvent.setup();
    const creatorMatch = {
      ...buildMatch('match-my-search-empty', 'nessun candidato', 1),
      created_by_player_id: basePlayer.id,
      creator_profile_name: basePlayer.profile_name,
      joined_by_current_player: true,
    };
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [creatorMatch],
    });
    vi.mocked(searchPlayMatchPlayers).mockResolvedValue({
      message: 'Nessun nuovo player compatibile da avvisare in questo momento.',
      notifications_created: 0,
      cooldown_remaining_seconds: 0,
      match: creatorMatch,
    });

    renderApp('/c/roma-club/play');

    const card = (await screen.findAllByTestId('play-my-match-card'))[0];
    await user.click(within(card).getByRole('button', { name: 'Cerca giocatori' }));

    await waitFor(() => expect(searchPlayMatchPlayers).toHaveBeenCalledWith('match-my-search-empty', 'roma-club'));
    expect(await screen.findByText('Nessun nuovo player compatibile da avvisare in questo momento.')).toBeInTheDocument();
  });

  it('shows the cooldown feedback when Cerca giocatori was triggered too recently', async () => {
    const user = userEvent.setup();
    const creatorMatch = {
      ...buildMatch('match-my-search-cooldown', 'cooldown attivo', 2),
      created_by_player_id: basePlayer.id,
      creator_profile_name: basePlayer.profile_name,
      joined_by_current_player: true,
    };
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer }, notification_settings: { ...baseNotificationSettings } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [creatorMatch],
    });
    vi.mocked(searchPlayMatchPlayers).mockResolvedValue({
      message: 'Abbiamo gia cercato giocatori compatibili poco fa. Riprova tra qualche minuto.',
      notifications_created: 0,
      cooldown_remaining_seconds: 872,
      match: creatorMatch,
    });

    renderApp('/c/roma-club/play');

    const card = (await screen.findAllByTestId('play-my-match-card'))[0];
    await user.click(within(card).getByRole('button', { name: 'Cerca giocatori' }));

    await waitFor(() => expect(searchPlayMatchPlayers).toHaveBeenCalledWith('match-my-search-cooldown', 'roma-club'));
    expect(await screen.findByText('Abbiamo gia cercato giocatori compatibili poco fa. Riprova tra qualche minuto.')).toBeInTheDocument();
  });

  it('saves notification preferences from the play panel', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({
      player: { ...basePlayer },
      notification_settings: { ...baseNotificationSettings },
    });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [],
    });
    vi.mocked(updatePlayNotificationPreferences).mockResolvedValue({
      message: 'Preferenze notifiche aggiornate.',
      settings: {
        ...baseNotificationSettings,
        preferences: {
          ...baseNotificationSettings.preferences,
          notify_match_two_of_four: false,
        },
      },
    });

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Preferenze notifiche' });
    await expandSection(user, 'Preferenze notifiche');
    const saveButton = screen.getByRole('button', { name: 'Salva preferenze notifiche' });
    const preferencesCard = saveButton.closest('.surface-muted');
    expect(preferencesCard).not.toBeNull();

    await user.click(screen.getByLabelText('Avvisami per match 2/4'));
    await user.click(saveButton);

    await waitFor(() => expect(updatePlayNotificationPreferences).toHaveBeenCalledWith(expect.objectContaining({
      notify_match_two_of_four: false,
    }), 'roma-club'));
    expect(await within(preferencesCard as HTMLElement).findByText('Preferenze notifiche aggiornate.')).toBeInTheDocument();
  });

  it('registers and revokes web push from the play panel', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({
      player: { ...basePlayer },
      notification_settings: { ...baseNotificationSettings },
    });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [],
    });

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Preferenze notifiche' });
    await expandSection(user, 'Preferenze notifiche');
    const activateButton = screen.getByRole('button', { name: 'Attiva web push' });
    const pushCard = activateButton.closest('aside');
    expect(pushCard).not.toBeNull();

    await user.click(activateButton);

    await waitFor(() => expect(subscribeBrowserToPlayPush).toHaveBeenCalledWith('BElocalPlayPushKey', '/play-service-worker.js'));
    await waitFor(() => expect(registerPlayPushSubscription).toHaveBeenCalledWith({
      endpoint: 'https://push.example/sub-1',
      keys: { p256dh: 'p256dh-key', auth: 'auth-key' },
      user_agent: 'Vitest Browser',
    }, 'roma-club'));

    expect(await within(pushCard as HTMLElement).findByText('Subscription web push registrata.')).toBeInTheDocument();

    await user.click(within(pushCard as HTMLElement).getByRole('button', { name: 'Disattiva web push' }));

    await waitFor(() => expect(unsubscribeBrowserFromPlayPush).toHaveBeenCalled());
    await waitFor(() => expect(revokePlayPushSubscription).toHaveBeenCalledWith({ endpoint: 'https://push.example/sub-1' }, 'roma-club'));
    expect(await within(pushCard as HTMLElement).findByText('Subscription web push revocata.')).toBeInTheDocument();
  });

  it('shows unread count and marks a notification as read from the play panel', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({
      player: { ...basePlayer },
      notification_settings: {
        ...baseNotificationSettings,
        recent_notifications: [
          {
            id: 'notification-1',
            match_id: 'match-3of4',
            channel: 'IN_APP',
            kind: 'MATCH_THREE_OF_FOUR',
            title: 'Match quasi completo',
            message: 'Manca un player per chiudere il match.',
            payload: { match_id: 'match-3of4' },
            sent_at: '2026-05-02T10:00:00Z',
            read_at: null,
            created_at: '2026-05-02T10:00:00Z',
          },
        ],
        unread_notifications_count: 1,
      },
    });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [],
    });
    vi.mocked(markPlayNotificationRead).mockResolvedValue({
      message: 'Notifica play marcata come letta.',
      settings: {
        ...baseNotificationSettings,
        recent_notifications: [
          {
            id: 'notification-1',
            match_id: 'match-3of4',
            channel: 'IN_APP',
            kind: 'MATCH_THREE_OF_FOUR',
            title: 'Match quasi completo',
            message: 'Manca un player per chiudere il match.',
            payload: { match_id: 'match-3of4' },
            sent_at: '2026-05-02T10:00:00Z',
            read_at: '2026-05-02T10:05:00Z',
            created_at: '2026-05-02T10:00:00Z',
          },
        ],
        unread_notifications_count: 0,
      },
    });

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Preferenze notifiche' });
    await expandSection(user, 'Preferenze notifiche');
    expect(screen.getByText('Non lette: 1')).toBeInTheDocument();
    expect(screen.getByText('Non letta')).toBeInTheDocument();

    const readButton = screen.getByRole('button', { name: 'Segna come letta' });
    const notificationCard = readButton.closest('.rounded-2xl');
    expect(notificationCard).not.toBeNull();

    await user.click(readButton);

    await waitFor(() => expect(markPlayNotificationRead).toHaveBeenCalledWith('notification-1', 'roma-club'));
    expect(await within(notificationCard as HTMLElement).findByText('Notifica play marcata come letta.')).toBeInTheDocument();
    expect(screen.getByText('Non lette: 0')).toBeInTheDocument();
    expect(screen.getByText('Letta')).toBeInTheDocument();
  });

  it('shows only the enable action when the profile has push on other devices but not on this browser', async () => {
    const user = userEvent.setup();

    vi.mocked(getPlaySession).mockResolvedValue({
      player: { ...basePlayer },
      notification_settings: {
        ...baseNotificationSettings,
        push: {
          ...baseNotificationSettings.push,
          has_active_subscription: true,
          active_subscription_count: 2,
        },
      },
    });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [],
    });
    vi.mocked(unsubscribeBrowserFromPlayPush).mockResolvedValue(null);

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Preferenze notifiche' });
  await expandSection(user, 'Preferenze notifiche');
    expect(screen.getByText('Web push attiva su 2 dispositivi.')).toBeInTheDocument();
    expect(screen.getByText('Attiva su 2 dispositivi del tuo profilo, ma non su questo browser.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Attiva web push' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Disattiva web push' })).not.toBeInTheDocument();
    expect(revokePlayPushSubscription).not.toHaveBeenCalled();
    expect(unsubscribeBrowserFromPlayPush).not.toHaveBeenCalled();
  });

  it('shows a warning when subscriptions exist but the server cannot deliver web push', async () => {
    const user = userEvent.setup();

    vi.mocked(getPlaySession).mockResolvedValue({
      player: { ...basePlayer },
      notification_settings: {
        ...baseNotificationSettings,
        push: {
          ...baseNotificationSettings.push,
          push_supported: false,
          public_vapid_key: null,
          has_active_subscription: true,
          active_subscription_count: 2,
        },
      },
    });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [],
    });

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Preferenze notifiche' });
    await expandSection(user, 'Preferenze notifiche');
    expect(screen.getByText('Web push non disponibile da questo server.')).toBeInTheDocument();
    expect(screen.queryByText('Web push attiva su 2 dispositivi.')).not.toBeInTheDocument();
  });
});