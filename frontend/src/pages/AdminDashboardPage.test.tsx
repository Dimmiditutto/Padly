import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminDashboardPage } from './AdminDashboardPage';

vi.mock('../services/adminApi', () => ({
  createAdminCourt: vi.fn(),
  createAdminBooking: vi.fn(),
  createBlackout: vi.fn(),
  createAdminCommunityAccessLink: vi.fn(),
  createAdminCommunityInvite: vi.fn(),
  createRecurring: vi.fn(),
  getAdminReport: vi.fn(),
  getAdminSession: vi.fn(),
  getAdminSettings: vi.fn(),
  getSubscriptionStatus: vi.fn(),
  listAdminCommunityAccessLinks: vi.fn(),
  listAdminPlayMatchLinks: vi.fn(),
  listAdminCourts: vi.fn(),
  listAdminCommunityInvites: vi.fn(),
  listBlackouts: vi.fn(),
  logoutAdmin: vi.fn(),
  previewRecurring: vi.fn(),
  revokeAdminCommunityAccessLink: vi.fn(),
  revokeAdminCommunityInvite: vi.fn(),
  updateAdminSettings: vi.fn(),
}));

vi.mock('../services/publicApi', () => ({
  getAvailability: vi.fn(),
}));

import {
  createAdminCourt,
  createAdminBooking,
  createBlackout,
  createAdminCommunityAccessLink,
  createAdminCommunityInvite,
  createRecurring,
  getAdminReport,
  getAdminSession,
  getAdminSettings,
  getSubscriptionStatus,
  listAdminCommunityAccessLinks,
  listAdminCommunityInvites,
  listAdminPlayMatchLinks,
  listAdminCourts,
  listBlackouts,
  logoutAdmin,
  previewRecurring,
  revokeAdminCommunityAccessLink,
  revokeAdminCommunityInvite,
  updateAdminSettings,
} from '../services/adminApi';
import { getAvailability } from '../services/publicApi';

const adminSession = {
  email: 'admin@padelbooking.app',
  full_name: 'Admin',
  role: 'SUPERADMIN',
  club_id: 'club-default',
  club_slug: 'default-club',
  club_public_name: 'PadelBooking',
  timezone: 'Europe/Rome',
} as const;

const adminSettings = {
  club_id: 'club-default',
  club_slug: 'default-club',
  public_name: 'PadelBooking',
  timezone: 'Europe/Rome',
  currency: 'EUR',
  notification_email: 'desk@padelbooking.app',
  support_email: 'help@padelbooking.app',
  support_phone: '+390101010101',
  public_address: 'Via dei Campi 1',
  public_postal_code: '17100',
  public_city: 'Savona',
  public_province: 'SV',
  public_latitude: 44.30941,
  public_longitude: 8.47715,
  is_community_open: false,
  booking_hold_minutes: 15,
  cancellation_window_hours: 24,
  reminder_window_hours: 24,
  member_hourly_rate: 7,
  non_member_hourly_rate: 9,
  member_ninety_minute_rate: 10,
  non_member_ninety_minute_rate: 13,
  public_booking_deposit_enabled: true,
  public_booking_base_amount: 20,
  public_booking_included_minutes: 90,
  public_booking_extra_amount: 10,
  public_booking_extra_step_minutes: 30,
  public_booking_extras: [] as string[],
  play_community_deposit_enabled: false,
  play_community_deposit_amount: 20,
  play_community_payment_timeout_minutes: 15,
  play_community_use_public_deposit: false,
  stripe_enabled: true,
  paypal_enabled: true,
} as const;

function renderDashboard(path = '/admin') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/admin' element={<AdminDashboardPage />} />
        <Route path='/admin/login' element={<div>LOGIN PAGE</div>} />
        <Route path='/admin/prenotazioni-attuali' element={<div>CURRENT BOOKINGS PAGE</div>} />
        <Route path='/admin/prenotazioni' element={<div>BOOKINGS PAGE</div>} />
        <Route path='/admin/log' element={<div>LOG PAGE</div>} />
      </Routes>
    </MemoryRouter>
  );
}

function mockBootstrapSuccess() {
  vi.mocked(getAdminSession).mockResolvedValue({ ...adminSession });
  vi.mocked(listBlackouts).mockResolvedValue([]);
  vi.mocked(getAdminSettings).mockResolvedValue({ ...adminSettings });
}

describe('AdminDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBootstrapSuccess();
    vi.mocked(createAdminBooking).mockResolvedValue({} as never);
    vi.mocked(createAdminCourt).mockResolvedValue({ id: 'court-2', name: 'Campo 2', badge_label: null, sort_order: 2, is_active: true } as never);
    vi.mocked(createBlackout).mockResolvedValue({ id: 'blackout-1', message: 'ok' });
    vi.mocked(createAdminCommunityAccessLink).mockResolvedValue({
      message: 'Link accesso community creato.',
      link_id: 'group-link-1',
      access_token: 'group-token-123',
      access_path: '/c/default-club/play/access/group-token-123',
      label: 'Gruppo WhatsApp Open Match',
      max_uses: 200,
      used_count: 0,
      expires_at: '2026-05-09T23:59:00',
    });
    vi.mocked(createAdminCommunityInvite).mockResolvedValue({
      message: 'Invito community creato.',
      invite_id: 'invite-1',
      invite_token: 'invite-token-123',
      invite_path: '/c/default-club/play/invite/invite-token-123',
      profile_name: 'Giulia Spin',
      phone: '+393331112222',
      invited_level: 'INTERMEDIATE_MEDIUM',
      expires_at: '2026-05-04T10:30:00Z',
    });
    vi.mocked(createRecurring).mockResolvedValue({ series_id: 'series-1', created_count: 1, skipped_count: 0, skipped: [] });
    vi.mocked(getAdminReport).mockResolvedValue({
      total_bookings: 0,
      confirmed_bookings: 0,
      pending_bookings: 0,
      cancelled_bookings: 0,
      collected_deposits: 0,
    });
    vi.mocked(getSubscriptionStatus).mockResolvedValue({
      status: 'ACTIVE',
      plan_code: 'basic',
      plan_name: 'Basic',
      trial_ends_at: null,
      current_period_end: null,
      is_access_blocked: false,
    });
    vi.mocked(listAdminCommunityAccessLinks).mockResolvedValue({ items: [] });
    vi.mocked(listAdminPlayMatchLinks).mockResolvedValue({ items: [] });
    vi.mocked(listAdminCourts).mockResolvedValue({ items: [] });
    vi.mocked(listAdminCommunityInvites).mockResolvedValue({ items: [] });
    vi.mocked(logoutAdmin).mockResolvedValue({ message: 'ok' });
    vi.mocked(previewRecurring).mockResolvedValue({ occurrences: [] });
    vi.mocked(revokeAdminCommunityAccessLink).mockResolvedValue({
      message: 'Link accesso community revocato.',
      item: {
        id: 'group-link-active',
        label: 'Gruppo WhatsApp Open Match',
        max_uses: 200,
        used_count: 12,
        created_at: '2026-04-27T09:00:00Z',
        expires_at: '2026-05-04T09:00:00Z',
        revoked_at: '2026-04-27T10:00:00Z',
        status: 'REVOKED',
        can_revoke: false,
      },
    });
    vi.mocked(revokeAdminCommunityInvite).mockResolvedValue({
      message: 'Invito community revocato.',
      item: {
        id: 'invite-active',
        profile_name: 'Marco Guest',
        phone: '+393331111111',
        invited_level: 'INTERMEDIATE_LOW',
        created_at: '2026-04-27T09:00:00Z',
        expires_at: '2026-05-04T09:00:00Z',
        used_at: null,
        revoked_at: '2026-04-27T10:00:00Z',
        accepted_player_name: null,
        status: 'REVOKED',
        can_revoke: false,
      },
    });
    vi.mocked(updateAdminSettings).mockResolvedValue({ ...adminSettings });
    vi.mocked(getAvailability).mockImplementation(async (bookingDate: string, durationMinutes: number) => ({
      date: bookingDate,
      duration_minutes: durationMinutes,
      deposit_amount: 20,
      slots: bookingDate === '2026-10-25'
        ? [
            {
              slot_id: '2026-10-25T00:00:00+00:00',
              start_time: '02:00',
              end_time: '02:00',
              display_start_time: '02:00 CEST',
              display_end_time: '02:00 CET',
              available: true,
              reason: null,
            },
            {
              slot_id: '2026-10-25T01:00:00+00:00',
              start_time: '02:00',
              end_time: '03:00',
              display_start_time: '02:00 CET',
              display_end_time: '03:00 CET',
              available: true,
              reason: null,
            },
          ]
        : [
            { slot_id: '2099-04-16T16:00:00Z', start_time: '18:00', end_time: '19:30', display_start_time: '18:00', display_end_time: '19:30', available: true, reason: null },
          ],
    }));
  });

  it('shows feedback without redirecting when a non-auth dashboard request fails', async () => {
    vi.mocked(listBlackouts).mockRejectedValue({ response: { status: 500, data: { detail: 'Errore blackout' } } });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    await waitFor(() => expect(screen.getByText('Dashboard caricata solo parzialmente. Alcuni pannelli non sono disponibili al momento.')).toBeInTheDocument());
    expect(screen.queryByText('LOGIN PAGE')).not.toBeInTheDocument();
  });

  it('orders hero actions on the right and shows the logged club name below them', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');

    const heroActions = screen.getByTestId('admin-hero-actions');
    const orderedLabels = Array.from(heroActions.querySelectorAll('button, a')).map((element) => element.textContent?.trim());

    expect(orderedLabels).toEqual(['Aggiorna pagina', 'Torna alla home', 'Esci']);
    expect(screen.getByTestId('admin-hero-club-pill')).toHaveTextContent('PadelBooking');
  });

  it('redirects to login when session validation returns 401', async () => {
    vi.mocked(getAdminSession).mockRejectedValue({ response: { status: 401, data: { detail: 'Unauthorized' } } });

    renderDashboard();

    await screen.findByText('LOGIN PAGE');
  });

  it('shows the updated admin navigation and links the dashboard to weekly bookings, list and log pages', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');
    expect(screen.queryByText('Padly')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Crea Prenotazioni' })).toHaveAttribute('href', '/admin');
    expect(screen.getAllByRole('link', { name: 'Prenotazioni Attuali' })[0]).toHaveAttribute('href', '/admin/prenotazioni-attuali');
    expect(screen.getByRole('link', { name: 'Elenco Prenotazioni' })).toHaveAttribute('href', '/admin/prenotazioni');
    expect(screen.queryByText('Tenant attivo: PadelBooking')).not.toBeInTheDocument();
    expect(screen.queryByText('Slug: default-club')).not.toBeInTheDocument();
    expect(screen.queryByText('Notifiche: desk@padelbooking.app')).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Log' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Apri log' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Esci' })).toBeInTheDocument();
  });

  it('makes metrics and admin sections collapsible, removes helper cards and keeps log as the last section', async () => {
    vi.mocked(getAvailability).mockReturnValue(new Promise(() => {}));

    renderDashboard();

    await screen.findByText('Dashboard admin');

    expect(screen.queryByText('Promemoria pagine admin')).not.toBeInTheDocument();
    expect(screen.queryByText('Settimana corrente o ricerca avanzata')).not.toBeInTheDocument();
    expect(screen.queryByText('Audit e attività recenti')).not.toBeInTheDocument();
    expect(screen.queryByText('Prenotazioni totali')).not.toBeInTheDocument();
    expect(screen.queryByText('Confermate')).not.toBeInTheDocument();
    expect(screen.queryByText('In attesa')).not.toBeInTheDocument();
    expect(screen.queryByText('Caparre incassate')).not.toBeInTheDocument();
    expect(screen.queryByText('Prenotazioni e occupazione')).not.toBeInTheDocument();
    expect(screen.queryByText('Log operativi')).not.toBeInTheDocument();

    expect(screen.queryByLabelText('Nome')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Espandi Prenotazione manuale' }));
    expect(screen.getByLabelText('Nome')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Comprimi Prenotazione manuale' }));
    expect(screen.queryByLabelText('Nome')).not.toBeInTheDocument();
  });

  it('submits a manual booking after selecting a slot from the compact picker', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Prenotazione manuale' }));

    const manualSection = screen.getByText('Prenotazione manuale').closest('section');
    expect(manualSection).not.toBeNull();

    await waitFor(() => expect(within(manualSection as HTMLElement).getByRole('button', { name: '18:00' })).toBeInTheDocument());

    fireEvent.click(within(manualSection as HTMLElement).getByRole('button', { name: '18:00' }));
    fireEvent.click(screen.getByRole('button', { name: 'Crea prenotazione' }));

    await waitFor(() => expect(createAdminBooking).toHaveBeenCalledWith(expect.objectContaining({
      start_time: '18:00',
      slot_id: '2099-04-16T16:00:00Z',
    })));
    expect(within(manualSection as HTMLElement).getByText('Prenotazione manuale creata con successo.')).toBeInTheDocument();
  });

  it('derives the recurring weekday from the selected start date and forwards the selected recurring slot_id', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Serie ricorrente' }));

    fireEvent.change(screen.getByLabelText('Data di partenza'), { target: { value: '2026-10-25' } });
    expect(screen.getByLabelText('Fino al')).toHaveValue('2026-10-25');

    const recurringSection = screen.getByText('Serie ricorrente').closest('section');
    expect(recurringSection).not.toBeNull();

    await waitFor(() => expect(within(recurringSection as HTMLElement).getByRole('button', { name: '02:00 CET' })).toBeInTheDocument());

    fireEvent.click(within(recurringSection as HTMLElement).getByRole('button', { name: '02:00 CET' }));
    fireEvent.click(within(recurringSection as HTMLElement).getByRole('button', { name: 'Crea serie' }));

    await waitFor(() => expect(createRecurring).toHaveBeenCalledWith(expect.objectContaining({
      start_date: '2026-10-25',
      end_date: '2026-10-25',
      weekday: 6,
      start_time: '02:00',
      slot_id: '2026-10-25T01:00:00+00:00',
    })));
    expect(within(recurringSection as HTMLElement).getByText('Serie creata. Occorrenze create: 1. Saltate: 0.')).toBeInTheDocument();
  });

  it('renders recurring weekday labels without hardcoded Europe/Rome formatters', async () => {
    const originalDateTimeFormat = Intl.DateTimeFormat;
    const timezoneCalls: Array<string | undefined> = [];
    const formatterSpy = vi.spyOn(Intl, 'DateTimeFormat').mockImplementation(((locales: any, options?: Intl.DateTimeFormatOptions) => {
      timezoneCalls.push(options?.timeZone);
      return new originalDateTimeFormat(locales, options);
    }) as unknown as typeof Intl.DateTimeFormat);

    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Serie ricorrente' }));
    const recurringSection = screen.getByText('Serie ricorrente').closest('section');
    expect(recurringSection).not.toBeNull();

    await waitFor(() => expect(within(recurringSection as HTMLElement).getByRole('button', { name: '18:00' })).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('Data di partenza'), { target: { value: '2026-10-25' } });
    await waitFor(() => expect(within(recurringSection as HTMLElement).getByRole('button', { name: '02:00 CET' })).toBeInTheDocument());

    expect(screen.getAllByText(/Domenica/).length).toBeGreaterThan(0);
    expect(screen.queryByText('Prima ricorrenza')).not.toBeInTheDocument();
    expect(timezoneCalls).not.toContain('Europe/Rome');

    formatterSpy.mockRestore();
  });

  it('shows the explicit DST ambiguity error when the blackout time is ambiguous', async () => {
    vi.mocked(createBlackout).mockRejectedValue({ response: { data: { detail: 'Data/ora ambigua per il cambio ora legale. Scegli un orario non ambiguo o specifica un offset esplicito.' } } });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Blocca fascia oraria' }));
    fireEvent.change(screen.getByLabelText('Data inizio'), { target: { value: '2026-10-25' } });
    fireEvent.change(screen.getByLabelText('Ora inizio'), { target: { value: '02:15' } });
    fireEvent.change(screen.getByLabelText('Data fine'), { target: { value: '2026-10-25' } });
    fireEvent.change(screen.getByLabelText('Ora fine'), { target: { value: '03:15' } });
    fireEvent.click(screen.getByRole('button', { name: 'Crea blackout' }));

    await waitFor(() => expect(createBlackout).toHaveBeenCalledWith(expect.objectContaining({
      start_at: '2026-10-25T02:15',
      end_at: '2026-10-25T03:15',
    })));
    expect(screen.getByText('Data/ora ambigua per il cambio ora legale. Scegli un orario non ambiguo o specifica un offset esplicito.')).toBeInTheDocument();
  });

  it('creates a new court without submitting the settings form', async () => {
    vi.mocked(listAdminCourts)
      .mockResolvedValueOnce({ items: [{ id: 'court-1', name: 'Campo 1', sort_order: 1, is_active: true }] })
      .mockResolvedValueOnce({
        items: [
          { id: 'court-1', name: 'Campo 1', badge_label: null, sort_order: 1, is_active: true },
          { id: 'court-2', name: 'Campo 2', badge_label: 'Indoor', sort_order: 2, is_active: true },
        ],
      });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));

    const settingsSection = screen.getByText('Profilo tenant e regole operative').closest('section');
    expect(settingsSection).not.toBeNull();

    await waitFor(() => expect(within(settingsSection as HTMLElement).getByDisplayValue('Campo 1')).toBeInTheDocument());
    fireEvent.change(within(settingsSection as HTMLElement).getByLabelText('Etichetta nuovo campo'), { target: { value: 'Indoor' } });

    fireEvent.click(within(settingsSection as HTMLElement).getByRole('button', { name: 'Crea campo' }));

    await waitFor(() => expect(createAdminCourt).toHaveBeenCalledWith({ name: 'Campo 2', badge_label: 'Indoor' }));
    expect(updateAdminSettings).not.toHaveBeenCalled();
    await waitFor(() => expect(within(settingsSection as HTMLElement).getByText('Campo creato correttamente.')).toBeInTheDocument());
    expect(within(settingsSection as HTMLElement).getByDisplayValue('Campo 2')).toBeInTheDocument();
    expect(within(settingsSection as HTMLElement).getByDisplayValue('Indoor')).toBeInTheDocument();
  });

  it('saves tenant profile fields and preserves tenant query in admin links', async () => {
    vi.mocked(getAdminSession).mockResolvedValue({
      ...adminSession,
      club_slug: 'roma-club',
      club_public_name: 'Roma Club',
    });
    vi.mocked(getAdminSettings).mockResolvedValue({
      ...adminSettings,
      club_slug: 'roma-club',
      public_name: 'Roma Club',
      notification_email: 'desk@roma-club.example',
      support_email: 'support@roma-club.example',
      support_phone: '+39021234567',
    });
    vi.mocked(updateAdminSettings).mockResolvedValue({
      ...adminSettings,
      club_slug: 'roma-club',
      public_name: 'Roma Club Elite',
      notification_email: 'ops@roma-club.example',
      support_email: 'help@roma-club.example',
      support_phone: '+39029876543',
      member_hourly_rate: 8,
      non_member_hourly_rate: 11,
      member_ninety_minute_rate: 12,
      non_member_ninety_minute_rate: 15,
    });

    renderDashboard('/admin?tenant=roma-club');

    await screen.findByText('Dashboard admin');
    expect(screen.getByRole('link', { name: 'Crea Prenotazioni' })).toHaveAttribute('href', '/admin?tenant=roma-club');
    expect(screen.getByRole('link', { name: 'Prenotazioni Attuali' })).toHaveAttribute('href', '/admin/prenotazioni-attuali?tenant=roma-club');
    expect(screen.getByRole('link', { name: 'Elenco Prenotazioni' })).toHaveAttribute('href', '/admin/prenotazioni?tenant=roma-club');
    expect(screen.queryByText('Tenant attivo: Roma Club')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));
    expect(screen.queryByText('Slug tenant')).not.toBeInTheDocument();
    expect(screen.queryByText('Timezone')).not.toBeInTheDocument();
    expect(screen.queryByText('Valuta')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Nome club'), { target: { value: 'Roma Club Elite' } });
    fireEvent.change(screen.getByLabelText('Email notifiche operative'), { target: { value: 'ops@roma-club.example' } });
    fireEvent.change(screen.getByLabelText('Email supporto pubblico'), { target: { value: 'help@roma-club.example' } });
    fireEvent.change(screen.getByLabelText('Telefono supporto pubblico'), { target: { value: '+39029876543' } });
    fireEvent.change(screen.getByLabelText('Tesserati, tariffa oraria per giocatore'), { target: { value: '8' } });
    fireEvent.change(screen.getByLabelText('Non tesserati, tariffa oraria per giocatore'), { target: { value: '11' } });
    fireEvent.change(screen.getByLabelText('Tesserati, tariffa 90 minuti per giocatore'), { target: { value: '12' } });
    fireEvent.change(screen.getByLabelText('Non tesserati, tariffa 90 minuti per giocatore'), { target: { value: '15' } });
    const settingsSection = screen.getByText('Profilo tenant e regole operative').closest('section');
    expect(settingsSection).not.toBeNull();
    fireEvent.click(within(settingsSection as HTMLElement).getByRole('button', { name: 'Salva impostazioni' }));

    await waitFor(() => expect(updateAdminSettings).toHaveBeenCalledWith({
      public_name: 'Roma Club Elite',
      notification_email: 'ops@roma-club.example',
      support_email: 'help@roma-club.example',
      support_phone: '+39029876543',
      public_address: 'Via dei Campi 1',
      public_postal_code: '17100',
      public_city: 'Savona',
      public_province: 'SV',
      public_latitude: 44.30941,
      public_longitude: 8.47715,
      is_community_open: false,
      booking_hold_minutes: 15,
      cancellation_window_hours: 24,
      reminder_window_hours: 24,
      member_hourly_rate: 8,
      non_member_hourly_rate: 11,
      member_ninety_minute_rate: 12,
      non_member_ninety_minute_rate: 15,
      public_booking_deposit_enabled: true,
      public_booking_base_amount: 20,
      public_booking_included_minutes: 90,
      public_booking_extra_amount: 10,
      public_booking_extra_step_minutes: 30,
      public_booking_extras: [],
      play_community_deposit_enabled: false,
      play_community_deposit_amount: 20,
      play_community_payment_timeout_minutes: 15,
      play_community_use_public_deposit: false,
    }));
    await waitFor(() => expect(within(settingsSection as HTMLElement).getByText('Regole operative aggiornate.')).toBeInTheDocument());
  });

  it('saves public club identity fields inside the existing settings block', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));

    fireEvent.change(screen.getByLabelText('Nome club'), { target: { value: 'Savona Centro' } });
    fireEvent.change(screen.getByLabelText('Indirizzo (via, piazza, ecc.)'), { target: { value: 'Piazza Padel 7' } });
    fireEvent.change(screen.getByLabelText('CAP'), { target: { value: '17100' } });
    fireEvent.change(screen.getByLabelText('Citta'), { target: { value: 'Savona' } });
    fireEvent.change(screen.getByLabelText('Provincia'), { target: { value: 'sv' } });
    fireEvent.click(screen.getByLabelText('Community aperta a nuovi ingressi'));
    fireEvent.change(screen.getByLabelText('Latitudine (opzionale)'), { target: { value: '44.30941' } });
    fireEvent.change(screen.getByLabelText('Longitudine (opzionale)'), { target: { value: '8.47715' } });

    const settingsSection = screen.getByText('Profilo tenant e regole operative').closest('section');
    expect(settingsSection).not.toBeNull();
    fireEvent.click(within(settingsSection as HTMLElement).getByRole('button', { name: 'Salva impostazioni' }));

    await waitFor(() => expect(updateAdminSettings).toHaveBeenCalledWith(expect.objectContaining({
      public_name: 'Savona Centro',
      public_address: 'Piazza Padel 7',
      public_postal_code: '17100',
      public_city: 'Savona',
      public_province: 'sv',
      public_latitude: 44.30941,
      public_longitude: 8.47715,
      is_community_open: true,
    })));
  });

  it('saves community play deposit settings from the admin form', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));

    fireEvent.click(screen.getByLabelText('Attiva caparra community online sul quarto player'));
    fireEvent.change(screen.getByLabelText('Importo caparra community'), { target: { value: '12.5' } });
    fireEvent.change(screen.getByLabelText('Timeout checkout community'), { target: { value: '45' } });

    const settingsSection = screen.getByText('Profilo tenant e regole operative').closest('section');
    expect(settingsSection).not.toBeNull();
    fireEvent.click(within(settingsSection as HTMLElement).getByRole('button', { name: 'Salva impostazioni' }));

    await waitFor(() => expect(updateAdminSettings).toHaveBeenCalledWith(expect.objectContaining({
      play_community_deposit_enabled: true,
      play_community_deposit_amount: 12.5,
      play_community_payment_timeout_minutes: 45,
    })));
  });

  it('saves the public booking deposit policy and lets Play inherit it', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));

    fireEvent.change(screen.getByLabelText('Importo base'), { target: { value: '18' } });
    fireEvent.change(screen.getByLabelText('Minuti inclusi'), { target: { value: '90' } });
    fireEvent.change(screen.getByLabelText('Importo extra'), { target: { value: '9' } });
    fireEvent.change(screen.getByLabelText('Step extra minuti'), { target: { value: '30' } });
    fireEvent.change(screen.getByLabelText('Extra del club'), { target: { value: 'Luci serali\nNoleggio racchette' } });
    fireEvent.click(screen.getByLabelText('Usa la stessa caparra del booking pubblico del club'));

    const settingsSection = screen.getByText('Profilo tenant e regole operative').closest('section');
    expect(settingsSection).not.toBeNull();
    fireEvent.click(within(settingsSection as HTMLElement).getByRole('button', { name: 'Salva impostazioni' }));

    await waitFor(() => expect(updateAdminSettings).toHaveBeenCalledWith(expect.objectContaining({
      public_booking_deposit_enabled: true,
      public_booking_base_amount: 18,
      public_booking_included_minutes: 90,
      public_booking_extra_amount: 9,
      public_booking_extra_step_minutes: 30,
      public_booking_extras: ['Luci serali', 'Noleggio racchette'],
      play_community_use_public_deposit: true,
    })));
  });

  it('creates and exposes a shareable community invite from the admin section', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));

    fireEvent.change(screen.getByLabelText('Nome profilo invito community'), { target: { value: 'Giulia Spin' } });
    fireEvent.change(screen.getByLabelText('Telefono invito community'), { target: { value: '+39 333 111 2222' } });
    fireEvent.change(screen.getByLabelText('Livello iniziale'), { target: { value: 'INTERMEDIATE_MEDIUM' } });

    const settingsSection = screen.getByText('Profilo tenant e regole operative').closest('section');
    expect(settingsSection).not.toBeNull();
    fireEvent.click(within(settingsSection as HTMLElement).getByRole('button', { name: 'Genera link invito community' }));

    await waitFor(() => expect(createAdminCommunityInvite).toHaveBeenCalledWith({
      profile_name: 'Giulia Spin',
      phone: '+39 333 111 2222',
      invited_level: 'INTERMEDIATE_MEDIUM',
    }));
    const expectedInviteUrl = `${window.location.origin}/c/default-club/play/invite/invite-token-123`;
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expectedInviteUrl));
    expect(within(settingsSection as HTMLElement).getByDisplayValue(expectedInviteUrl)).toBeInTheDocument();
    expect(within(settingsSection as HTMLElement).getByText('Link accesso community copiato negli appunti.')).toBeInTheDocument();
  });

  it('lists issued community invites with status and lets admin revoke an active link', async () => {
    vi.mocked(listAdminCommunityInvites).mockResolvedValue({
      items: [
        {
          id: 'invite-active',
          profile_name: 'Marco Guest',
          phone: '+393331111111',
          invited_level: 'INTERMEDIATE_LOW',
          created_at: '2026-04-27T09:00:00Z',
          expires_at: '2026-05-04T09:00:00Z',
          used_at: null,
          revoked_at: null,
          accepted_player_name: null,
          status: 'ACTIVE',
          can_revoke: true,
        },
        {
          id: 'invite-used',
          profile_name: 'Luca Used',
          phone: '+393332222222',
          invited_level: 'ADVANCED',
          created_at: '2026-04-25T09:00:00Z',
          expires_at: '2026-05-02T09:00:00Z',
          used_at: '2026-04-25T10:00:00Z',
          revoked_at: null,
          accepted_player_name: 'Luca Used',
          status: 'USED',
          can_revoke: false,
        },
      ],
    });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));

    expect(await screen.findByText('Marco Guest')).toBeInTheDocument();
  const activeCard = screen.getByText('Marco Guest').closest('div.rounded-2xl');
    const usedCard = screen.getAllByText('Luca Used')[0].closest('div.rounded-2xl');
  expect(activeCard).not.toBeNull();
  expect(usedCard).not.toBeNull();
  expect(within(activeCard as HTMLElement).getByText('Attivo')).toBeInTheDocument();
  expect(within(usedCard as HTMLElement).getByText('Usato')).toBeInTheDocument();
    expect(screen.getByText(/Per sicurezza il link completo viene mostrato solo subito dopo la generazione/)).toBeInTheDocument();

    await screen.findByRole('button', { name: 'Revoca link Marco Guest' });
    fireEvent.click(screen.getByRole('button', { name: 'Revoca link Marco Guest' }));

    await waitFor(() => expect(revokeAdminCommunityInvite).toHaveBeenCalledWith('invite-active'));
    expect(await screen.findByText('Invito community revocato.')).toBeInTheDocument();
    const revokedCard = screen.getByText('Marco Guest').closest('div.rounded-2xl');
    expect(revokedCard).not.toBeNull();
    expect(within(revokedCard as HTMLElement).getByText('Revocato')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Revoca link Marco Guest' })).not.toBeInTheDocument();
  });

  it('creates and exposes a shareable group community link from the admin section', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));

    fireEvent.change(screen.getByLabelText('Etichetta link gruppo'), { target: { value: 'Gruppo WhatsApp Open Match' } });
    fireEvent.change(screen.getByLabelText('Utilizzi massimi'), { target: { value: '200' } });
    fireEvent.change(screen.getByLabelText('Scadenza link gruppo'), { target: { value: '2026-05-09' } });

    const settingsSection = screen.getByText('Profilo tenant e regole operative').closest('section');
    expect(settingsSection).not.toBeNull();
    fireEvent.click(within(settingsSection as HTMLElement).getByRole('button', { name: 'Genera link gruppo community' }));

    await waitFor(() => expect(createAdminCommunityAccessLink).toHaveBeenCalledWith({
      label: 'Gruppo WhatsApp Open Match',
      max_uses: 200,
      expires_at: '2026-05-09T23:59:00',
    }));
    const expectedLinkUrl = `${window.location.origin}/c/default-club/play/access/group-token-123`;
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expectedLinkUrl));
    expect(within(settingsSection as HTMLElement).getByDisplayValue(expectedLinkUrl)).toBeInTheDocument();
    expect(within(settingsSection as HTMLElement).getByText('Link gruppo community copiato negli appunti.')).toBeInTheDocument();
  });

  it('lists issued group community links and lets admin revoke an active one', async () => {
    vi.mocked(listAdminCommunityAccessLinks).mockResolvedValue({
      items: [
        {
          id: 'group-link-active',
          label: 'Gruppo WhatsApp Open Match',
          max_uses: 200,
          used_count: 12,
          created_at: '2026-04-27T09:00:00Z',
          expires_at: '2026-05-04T09:00:00Z',
          revoked_at: null,
          status: 'ACTIVE',
          can_revoke: true,
        },
        {
          id: 'group-link-expired',
          label: 'Newsletter Open Match',
          max_uses: null,
          used_count: 31,
          created_at: '2026-04-20T09:00:00Z',
          expires_at: '2026-04-21T09:00:00Z',
          revoked_at: null,
          status: 'EXPIRED',
          can_revoke: false,
        },
      ],
    });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));

    expect(await screen.findByText('Gruppo WhatsApp Open Match')).toBeInTheDocument();
    const activeCard = screen.getByText('Gruppo WhatsApp Open Match').closest('div.rounded-2xl');
    expect(activeCard).not.toBeNull();
    expect(within(activeCard as HTMLElement).getByText('Attivo')).toBeInTheDocument();
    expect(screen.getByText('Newsletter Open Match')).toBeInTheDocument();
    expect(screen.getByText(/Utilizzi: 12 \/ 200/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Revoca link gruppo Gruppo WhatsApp Open Match' }));

    await waitFor(() => expect(revokeAdminCommunityAccessLink).toHaveBeenCalledWith('group-link-active'));
    expect(await screen.findByText('Link accesso community revocato.')).toBeInTheDocument();
    const revokedCard = screen.getByText('Gruppo WhatsApp Open Match').closest('div.rounded-2xl');
    expect(revokedCard).not.toBeNull();
    expect(within(revokedCard as HTMLElement).getByText('Revocato')).toBeInTheDocument();
  });

  it('lists shareable Play matches for the club and opens the WhatsApp share dialog', async () => {
    const openMock = vi.fn();
    vi.stubGlobal('open', openMock);
    vi.mocked(listAdminPlayMatchLinks).mockResolvedValue({
      items: [
        {
          id: 'play-match-1',
          share_token: 'share-match-1',
          share_path: '/c/default-club/play/matches/share-match-1',
          court_name: 'Campo Centrale',
          start_at: '2026-05-10T18:00:00Z',
          end_at: '2026-05-10T19:30:00Z',
          status: 'OPEN',
          level_requested: 'INTERMEDIATE_MEDIUM',
          participant_count: 2,
          participant_names: ['Luca Smash', 'Marco Topspin'],
        },
      ],
    });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));

    expect(await screen.findByText('Link partite Play')).toBeInTheDocument();
    expect(screen.getByDisplayValue(`${window.location.origin}/c/default-club/play/matches/share-match-1`)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Condividi match' }));

    expect(await screen.findByRole('dialog', { name: 'Condividi partita Play del club' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Apri WhatsApp' }));

    await waitFor(() => expect(openMock).toHaveBeenCalled());
    const whatsAppUrl = openMock.mock.calls[0]?.[0];
    expect(String(whatsAppUrl)).toContain('https://web.whatsapp.com/send?text=');
    const decoded = decodeURIComponent(String(whatsAppUrl).split('text=')[1] || '');
    expect(decoded).toContain('🕒 *Ore 20:00/21:30*');
    expect(decoded).toContain('📈 Livello Intermedio medio\n📍 PadelBooking');
    expect(decoded).toContain('📍 PadelBooking\n\n🎾 Luca Smash');
    expect(decoded).toContain('🎾 Marco Topspin\n\nClicca ed unisciti alla partita! `👇🏻`');
    expect(decoded).toContain('📅 *');
    expect(decoded).toContain('📈 Livello Intermedio medio');
    expect(decoded).toContain('📍 PadelBooking');
    expect(decoded).toContain('🎾 Luca Smash');
    expect(decoded).toContain('🎾 Marco Topspin');
  });

  it('filters and searches community invites by status, name and phone', async () => {
    vi.mocked(listAdminCommunityInvites).mockResolvedValue({
      items: [
        {
          id: 'invite-active',
          profile_name: 'Marco Guest',
          phone: '+393331111111',
          invited_level: 'INTERMEDIATE_LOW',
          created_at: '2026-04-27T09:00:00Z',
          expires_at: '2026-05-04T09:00:00Z',
          used_at: null,
          revoked_at: null,
          accepted_player_name: null,
          status: 'ACTIVE',
          can_revoke: true,
        },
        {
          id: 'invite-expired',
          profile_name: 'Giulia Scaduta',
          phone: '+393332222222',
          invited_level: 'BEGINNER',
          created_at: '2026-04-20T09:00:00Z',
          expires_at: '2026-04-21T09:00:00Z',
          used_at: null,
          revoked_at: null,
          accepted_player_name: null,
          status: 'EXPIRED',
          can_revoke: false,
        },
        {
          id: 'invite-revoked',
          profile_name: 'Luca Revocato',
          phone: '+393333333333',
          invited_level: 'ADVANCED',
          created_at: '2026-04-22T09:00:00Z',
          expires_at: '2026-04-29T09:00:00Z',
          used_at: null,
          revoked_at: '2026-04-23T09:00:00Z',
          accepted_player_name: null,
          status: 'REVOKED',
          can_revoke: false,
        },
      ],
    });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));

    fireEvent.change(screen.getByLabelText('Filtra inviti community'), { target: { value: 'REVOKED' } });
    expect(await screen.findByText('Luca Revocato')).toBeInTheDocument();
    expect(screen.queryByText('Marco Guest')).not.toBeInTheDocument();
    expect(screen.queryByText('Giulia Scaduta')).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Filtra inviti community'), { target: { value: 'ALL' } });
    fireEvent.change(screen.getByLabelText('Cerca inviti community'), { target: { value: 'Giulia' } });
    expect(await screen.findByText('Giulia Scaduta')).toBeInTheDocument();
    expect(screen.queryByText('Marco Guest')).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Cerca inviti community'), { target: { value: '3333333333' } });
    expect(await screen.findByText('Luca Revocato')).toBeInTheDocument();
    expect(screen.queryByText('Giulia Scaduta')).not.toBeInTheDocument();
  });

  it('paginates community invites 10 at a time with previous and next buttons', async () => {
    vi.mocked(listAdminCommunityInvites).mockResolvedValue({
      items: Array.from({ length: 12 }, (_, index) => ({
        id: `invite-${index + 1}`,
        profile_name: `Guest ${index + 1}`,
        phone: `+3933300000${String(index + 1).padStart(2, '0')}`,
        invited_level: 'NO_PREFERENCE' as const,
        created_at: '2026-04-27T09:00:00Z',
        expires_at: '2026-05-04T09:00:00Z',
        used_at: null,
        revoked_at: null,
        accepted_player_name: null,
        status: 'ACTIVE' as const,
        can_revoke: true,
      })),
    });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));

    expect(await screen.findByText('Guest 1')).toBeInTheDocument();
    expect(screen.getByText('Guest 10')).toBeInTheDocument();
    expect(screen.queryByText('Guest 11')).not.toBeInTheDocument();
    expect(screen.getByText('Mostro 1-10 di 12 inviti')).toBeInTheDocument();
    expect(screen.getByText('Pagina 1 di 2')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Inviti successivi' }));

    expect(await screen.findByText('Guest 11')).toBeInTheDocument();
    expect(screen.getByText('Guest 12')).toBeInTheDocument();
    expect(screen.queryByText('Guest 1')).not.toBeInTheDocument();
    expect(screen.getByText('Mostro 11-12 di 12 inviti')).toBeInTheDocument();
    expect(screen.getByText('Pagina 2 di 2')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Inviti precedenti' }));

    expect(await screen.findByText('Guest 1')).toBeInTheDocument();
    expect(screen.queryByText('Guest 11')).not.toBeInTheDocument();
    expect(screen.getByText('Pagina 1 di 2')).toBeInTheDocument();
  });
});
