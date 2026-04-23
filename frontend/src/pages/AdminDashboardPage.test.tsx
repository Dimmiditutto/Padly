import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminDashboardPage } from './AdminDashboardPage';

vi.mock('../services/adminApi', () => ({
  createAdminBooking: vi.fn(),
  createBlackout: vi.fn(),
  createRecurring: vi.fn(),
  getAdminReport: vi.fn(),
  getAdminSession: vi.fn(),
  getAdminSettings: vi.fn(),
  listBlackouts: vi.fn(),
  logoutAdmin: vi.fn(),
  previewRecurring: vi.fn(),
  updateAdminSettings: vi.fn(),
}));

vi.mock('../services/publicApi', () => ({
  getAvailability: vi.fn(),
}));

import {
  createAdminBooking,
  createBlackout,
  createRecurring,
  getAdminReport,
  getAdminSession,
  getAdminSettings,
  listBlackouts,
  logoutAdmin,
  previewRecurring,
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
  booking_hold_minutes: 15,
  cancellation_window_hours: 24,
  reminder_window_hours: 24,
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
  vi.mocked(getAdminReport).mockResolvedValue({ total_bookings: 987, confirmed_bookings: 654, pending_bookings: 32, cancelled_bookings: 0, collected_deposits: 140 });
  vi.mocked(listBlackouts).mockResolvedValue([]);
  vi.mocked(getAdminSettings).mockResolvedValue({ ...adminSettings });
}

describe('AdminDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBootstrapSuccess();
    vi.mocked(createAdminBooking).mockResolvedValue({} as never);
    vi.mocked(createBlackout).mockResolvedValue({ id: 'blackout-1', message: 'ok' });
    vi.mocked(createRecurring).mockResolvedValue({ series_id: 'series-1', created_count: 1, skipped_count: 0, skipped: [] });
    vi.mocked(logoutAdmin).mockResolvedValue({ message: 'ok' });
    vi.mocked(previewRecurring).mockResolvedValue({ occurrences: [] });
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
    vi.mocked(getAdminReport).mockRejectedValue({ response: { status: 500, data: { detail: 'Errore report' } } });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    await waitFor(() => expect(screen.getByText('Dashboard caricata solo parzialmente. Alcuni pannelli non sono disponibili al momento.')).toBeInTheDocument());
    expect(screen.queryByText('LOGIN PAGE')).not.toBeInTheDocument();
  });

  it('redirects to login when session validation returns 401', async () => {
    vi.mocked(getAdminSession).mockRejectedValue({ response: { status: 401, data: { detail: 'Unauthorized' } } });

    renderDashboard();

    await screen.findByText('LOGIN PAGE');
  });

  it('shows the updated admin navigation and links the dashboard to weekly bookings, list and log pages', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');
    expect(screen.getByText('Padly')).toBeInTheDocument();
    expect(screen.getByText('Tenant attivo: PadelBooking')).toBeInTheDocument();
    expect(screen.getByText('Slug: default-club')).toBeInTheDocument();
    expect(screen.getByText('Notifiche: desk@padelbooking.app')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Crea Prenotazioni' })).toHaveAttribute('href', '/admin');
    expect(screen.getAllByRole('link', { name: 'Prenotazioni Attuali' })[0]).toHaveAttribute('href', '/admin/prenotazioni-attuali');
    expect(screen.getByRole('link', { name: 'Elenco Prenotazioni' })).toHaveAttribute('href', '/admin/prenotazioni');
    expect(screen.getByRole('link', { name: 'Elenco prenotazioni' })).toHaveAttribute('href', '/admin/prenotazioni');
    expect(screen.getByRole('link', { name: 'Apri log' })).toHaveAttribute('href', '/admin/log');
    expect(screen.getByRole('button', { name: 'Esci' })).toBeInTheDocument();
  });

  it('makes metrics and admin sections collapsible, removes helper cards and keeps log as the last section', async () => {
    vi.mocked(getAvailability).mockReturnValue(new Promise(() => {}));

    renderDashboard();

    await screen.findByText('Dashboard admin');

    expect(screen.queryByText('Promemoria pagine admin')).not.toBeInTheDocument();
    expect(screen.queryByText('Settimana corrente o ricerca avanzata')).not.toBeInTheDocument();
    expect(screen.queryByText('Audit e attività recenti')).not.toBeInTheDocument();

    const sectionTitles = screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent);
    expect(sectionTitles.at(-1)).toBe('Log operativi');

    expect(screen.queryByText('987')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Espandi Prenotazioni totali' }));
    expect(screen.getByText('987')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Comprimi Prenotazioni totali' }));
    expect(screen.queryByText('987')).not.toBeInTheDocument();

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
    fireEvent.change(screen.getByLabelText('Data di partenza'), { target: { value: '2026-10-25' } });

    expect(screen.getAllByText(/Domenica/).length).toBeGreaterThan(0);
    expect(timezoneCalls).not.toContain('Europe/Rome');

    formatterSpy.mockRestore();
  });

  it('shows the explicit DST ambiguity error when the blackout time is ambiguous', async () => {
    vi.mocked(createBlackout).mockRejectedValue({ response: { data: { detail: 'Data/ora ambigua per il cambio ora legale. Scegli un orario non ambiguo o specifica un offset esplicito.' } } });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi Blocca fascia oraria' }));
    fireEvent.change(screen.getByLabelText('Data e ora inizio'), { target: { value: '2026-10-25T02:15' } });
    fireEvent.change(screen.getByLabelText('Data e ora fine'), { target: { value: '2026-10-25T03:15' } });
    fireEvent.click(screen.getByRole('button', { name: 'Crea blackout' }));

    await waitFor(() => expect(createBlackout).toHaveBeenCalledWith(expect.objectContaining({
      start_at: '2026-10-25T02:15',
      end_at: '2026-10-25T03:15',
    })));
    expect(screen.getByText('Data/ora ambigua per il cambio ora legale. Scegli un orario non ambiguo o specifica un offset esplicito.')).toBeInTheDocument();
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
    });

    renderDashboard('/admin?tenant=roma-club');

    await screen.findByText('Tenant attivo: Roma Club');
    expect(screen.getByRole('link', { name: 'Apri log' })).toHaveAttribute('href', '/admin/log?tenant=roma-club');

    fireEvent.click(screen.getByRole('button', { name: 'Espandi Profilo tenant e regole operative' }));
    fireEvent.change(screen.getByLabelText('Nome pubblico tenant'), { target: { value: 'Roma Club Elite' } });
    fireEvent.change(screen.getByLabelText('Email notifiche operative'), { target: { value: 'ops@roma-club.example' } });
    fireEvent.change(screen.getByLabelText('Email supporto pubblico'), { target: { value: 'help@roma-club.example' } });
    fireEvent.change(screen.getByLabelText('Telefono supporto pubblico'), { target: { value: '+39029876543' } });
    fireEvent.click(screen.getByRole('button', { name: 'Salva impostazioni tenant' }));

    await waitFor(() => expect(updateAdminSettings).toHaveBeenCalledWith({
      public_name: 'Roma Club Elite',
      notification_email: 'ops@roma-club.example',
      support_email: 'help@roma-club.example',
      support_phone: '+39029876543',
      booking_hold_minutes: 15,
      cancellation_window_hours: 24,
      reminder_window_hours: 24,
    }));
    await screen.findByText('Regole operative aggiornate.');
  });
});
