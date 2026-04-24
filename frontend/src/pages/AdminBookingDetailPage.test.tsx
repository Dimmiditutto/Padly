import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminBookingDetailPage } from './AdminBookingDetailPage';

vi.mock('../services/adminApi', () => ({
  cancelRecurringSeries: vi.fn(),
  getAdminBooking: vi.fn(),
  getAdminSession: vi.fn(),
  markAdminBalancePaid: vi.fn(),
  updateAdminBooking: vi.fn(),
  updateAdminBookingStatus: vi.fn(),
  updateRecurringSeries: vi.fn(),
}));

vi.mock('../services/publicApi', () => ({
  getAvailability: vi.fn(),
}));

import { cancelRecurringSeries, getAdminBooking, getAdminSession, markAdminBalancePaid, updateAdminBooking, updateAdminBookingStatus, updateRecurringSeries } from '../services/adminApi';
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

const baseBooking = {
  id: 'booking-1',
  public_reference: 'PB-BOOK-001',
  start_at: '2099-04-16T16:00:00Z',
  end_at: '2099-04-16T17:30:00Z',
  duration_minutes: 90,
  booking_date_local: '2099-04-16',
  status: 'CONFIRMED',
  deposit_amount: 20,
  payment_provider: 'STRIPE',
  payment_status: 'PAID',
  customer_name: 'Luca Bianchi',
  customer_email: 'luca@example.com',
  customer_phone: '3331112222',
  note: 'Prenotazione di test',
  created_by: 'admin@padelbooking.app',
  source: 'PUBLIC',
  recurring_series_id: null,
  recurring_series_label: null,
  recurring_series_start_date: null,
  recurring_series_end_date: null,
  recurring_series_weekday: null,
  created_at: '2024-04-10T08:00:00Z',
  cancelled_at: null,
  completed_at: null,
  no_show_at: null,
  balance_paid_at: null,
  payment_reference: 'pi_test_123',
} as const;

const playOriginDetailBooking = {
  ...baseBooking,
  customer_name: null,
  customer_email: null,
  customer_phone: null,
  payment_provider: 'NONE',
  payment_status: 'UNPAID',
  created_by: 'play:match-play-42',
  source: 'ADMIN_MANUAL',
  note: 'Booking finale nata da match /play',
} as const;

function RouteLocation({ label }: { label: string }) {
  const location = useLocation();
  return <div>{`${label} ${location.pathname}${location.search}`}</div>;
}

function renderPage(path = '/admin/bookings/booking-1') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/admin/bookings/:bookingId' element={<AdminBookingDetailPage />} />
        <Route path='/admin/prenotazioni' element={<RouteLocation label='BOOKINGS PAGE' />} />
        <Route path='/admin/login' element={<RouteLocation label='LOGIN PAGE' />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('AdminBookingDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAdminSession).mockResolvedValue({ ...adminSession });
    vi.mocked(getAdminBooking).mockResolvedValue({ ...baseBooking });
    vi.mocked(getAvailability).mockResolvedValue({
      date: baseBooking.booking_date_local,
      duration_minutes: baseBooking.duration_minutes,
      deposit_amount: 20,
      slots: [
        { slot_id: baseBooking.start_at, start_time: '18:00', end_time: '19:30', display_start_time: '18:00', display_end_time: '19:30', available: true, reason: null },
      ],
    });
    vi.mocked(updateAdminBooking).mockResolvedValue({ ...baseBooking, note: 'Prenotazione aggiornata' });
    vi.mocked(updateAdminBookingStatus).mockResolvedValue({ ...baseBooking, status: 'CANCELLED', cancelled_at: '2024-04-16T12:05:00Z' });
    vi.mocked(updateRecurringSeries).mockResolvedValue({ series_id: 'series-1', created_count: 4, skipped_count: 0, skipped: [] });
    vi.mocked(markAdminBalancePaid).mockResolvedValue({ ...baseBooking, balance_paid_at: '2024-04-16T12:06:00Z' });
    vi.mocked(cancelRecurringSeries).mockResolvedValue({ message: 'ok', cancelled_count: 4, skipped_count: 0, booking_ids: ['booking-1'], series_id: 'series-1' });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('redirects to login when the admin session returns 401', async () => {
    vi.mocked(getAdminSession).mockRejectedValue({ response: { status: 401, data: { detail: 'Unauthorized' } } });

    renderPage();

    await screen.findByText('LOGIN PAGE /admin/login');
  });

  it('preserves tenant query on login redirect when session validation fails', async () => {
    vi.mocked(getAdminSession).mockRejectedValue({ response: { status: 401, data: { detail: 'Unauthorized' } } });

    renderPage('/admin/bookings/booking-1?tenant=roma-club');

    await screen.findByText('LOGIN PAGE /admin/login?tenant=roma-club');
    expect(getAdminSession).toHaveBeenCalledWith('roma-club');
  });

  it('preserves tenant query in the back link to bookings', async () => {
    vi.mocked(getAdminSession).mockResolvedValue({
      ...adminSession,
      club_id: 'club-roma',
      club_slug: 'roma-club',
      club_public_name: 'Roma Club',
    });

    renderPage('/admin/bookings/booking-1?tenant=roma-club');

    await screen.findByText('Dettaglio prenotazione');
    const backLink = screen.getByRole('link', { name: 'Torna alle prenotazioni' });
    expect(backLink).toHaveAttribute('href', '/admin/prenotazioni?tenant=roma-club');

    fireEvent.click(backLink);
    await screen.findByText('BOOKINGS PAGE /admin/prenotazioni?tenant=roma-club');
  });

  it('hides payment details and balance actions for recurring bookings', async () => {
    vi.mocked(getAdminBooking).mockResolvedValue({
      ...baseBooking,
      source: 'ADMIN_RECURRING',
      deposit_amount: 0,
      payment_provider: 'NONE',
      payment_status: 'UNPAID',
      recurring_series_id: 'series-1',
      recurring_series_label: 'Serie fissa del mercoledi',
    });

    renderPage();

    await screen.findByText('Le prenotazioni ricorrenti non richiedono caparra online o saldo al campo.');
    expect(screen.queryByText('Caparra')).not.toBeInTheDocument();
    expect(screen.queryByText('Pagamento')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Segna saldo al campo' })).not.toBeInTheDocument();
    expect(screen.getByText('Le prenotazioni ricorrenti non richiedono caparra online o saldo al campo.')).toBeInTheDocument();
  });

  it('lets the admin cancel the full recurring series from the booking detail page', async () => {
    vi.mocked(getAdminBooking)
      .mockResolvedValueOnce({
        ...baseBooking,
        source: 'ADMIN_RECURRING',
        deposit_amount: 0,
        payment_provider: 'NONE',
        payment_status: 'UNPAID',
        recurring_series_id: 'series-1',
        recurring_series_label: 'Serie fissa del mercoledi',
        recurring_series_end_date: '2099-05-14',
        recurring_series_weekday: 3,
      })
      .mockResolvedValueOnce({
        ...baseBooking,
        source: 'ADMIN_RECURRING',
        deposit_amount: 0,
        payment_provider: 'NONE',
        payment_status: 'UNPAID',
        status: 'CANCELLED',
        cancelled_at: '2024-04-16T12:05:00Z',
        recurring_series_id: 'series-1',
        recurring_series_label: 'Serie fissa del mercoledi',
        recurring_series_end_date: '2099-05-14',
        recurring_series_weekday: 3,
      });

    renderPage();

    await screen.findByRole('button', { name: 'Annulla intera serie' });
    fireEvent.click(screen.getByRole('button', { name: 'Annulla intera serie' }));

    await waitFor(() => expect(cancelRecurringSeries).toHaveBeenCalledWith('series-1'));
    expect(screen.getByText('Serie aggiornata: 4 occorrenze future annullate, 0 saltate.')).toBeInTheDocument();
  });

  it('lets the admin update the full recurring series from the booking detail page', async () => {
    vi.mocked(getAdminBooking)
      .mockResolvedValueOnce({
        ...baseBooking,
        source: 'ADMIN_RECURRING',
        deposit_amount: 0,
        payment_provider: 'NONE',
        payment_status: 'UNPAID',
        recurring_series_id: 'series-1',
        recurring_series_label: 'Serie fissa del mercoledi',
        recurring_series_end_date: '2099-05-14',
        recurring_series_weekday: 3,
      })
      .mockResolvedValueOnce({
        ...baseBooking,
        source: 'ADMIN_RECURRING',
        deposit_amount: 0,
        payment_provider: 'NONE',
        payment_status: 'UNPAID',
        recurring_series_id: 'series-1',
        recurring_series_label: 'Serie aggiornata admin',
        recurring_series_end_date: '2099-05-21',
        recurring_series_weekday: 3,
      });

    renderPage();

    await screen.findByRole('button', { name: 'Modifica intera serie' });
    fireEvent.click(screen.getByRole('button', { name: 'Modifica intera serie' }));
    fireEvent.change(screen.getByLabelText('Nome serie ricorrente'), { target: { value: 'Serie aggiornata admin' } });
    fireEvent.change(screen.getByLabelText('Fino al'), { target: { value: '2099-05-21' } });
    fireEvent.click(screen.getByRole('button', { name: 'Salva serie' }));

    await waitFor(() => expect(updateRecurringSeries).toHaveBeenCalledWith('series-1', expect.objectContaining({
      label: 'Serie aggiornata admin',
      start_date: '2099-04-16',
      end_date: '2099-05-21',
      weekday: 3,
      start_time: '18:00',
      slot_id: '2099-04-16T16:00:00Z',
      duration_minutes: 90,
    })));
    expect(screen.getByText('Serie aggiornata. Nuove occorrenze create: 4. Saltate: 0.')).toBeInTheDocument();
  });

  it('uses the tenant timezone when saving a booking update for a non-Rome tenant', async () => {
    vi.mocked(getAdminSession).mockResolvedValue({
      ...adminSession,
      club_id: 'club-new-york',
      club_slug: 'new-york-club',
      club_public_name: 'New York Club',
      timezone: 'America/New_York',
    });
    vi.mocked(getAvailability).mockResolvedValue({
      date: baseBooking.booking_date_local,
      duration_minutes: baseBooking.duration_minutes,
      deposit_amount: 20,
      slots: [
        { slot_id: baseBooking.start_at, start_time: '12:00', end_time: '13:30', display_start_time: '12:00', display_end_time: '13:30', available: true, reason: null },
      ],
    });

    renderPage();

    await screen.findByText('Dettaglio prenotazione');
    fireEvent.click(screen.getByRole('button', { name: 'Modifica data e orario' }));
    fireEvent.click(screen.getByRole('button', { name: 'Salva modifica' }));

    await waitFor(() => expect(updateAdminBooking).toHaveBeenCalledWith('booking-1', expect.objectContaining({
      slot_id: '2099-04-16T16:00:00Z',
      start_time: '12:00',
    })));
  });

  it('uses the tenant timezone when saving the recurring series form for a non-Rome tenant', async () => {
    vi.mocked(getAdminSession).mockResolvedValue({
      ...adminSession,
      club_id: 'club-new-york',
      club_slug: 'new-york-club',
      club_public_name: 'New York Club',
      timezone: 'America/New_York',
    });
    vi.mocked(getAdminBooking)
      .mockResolvedValueOnce({
        ...baseBooking,
        source: 'ADMIN_RECURRING',
        deposit_amount: 0,
        payment_provider: 'NONE',
        payment_status: 'UNPAID',
        recurring_series_id: 'series-1',
        recurring_series_label: 'Serie fissa del mercoledi',
        recurring_series_end_date: '2099-05-14',
        recurring_series_weekday: 3,
      })
      .mockResolvedValueOnce({
        ...baseBooking,
        source: 'ADMIN_RECURRING',
        deposit_amount: 0,
        payment_provider: 'NONE',
        payment_status: 'UNPAID',
        recurring_series_id: 'series-1',
        recurring_series_label: 'Serie aggiornata admin',
        recurring_series_end_date: '2099-05-21',
        recurring_series_weekday: 3,
      });
    vi.mocked(getAvailability).mockResolvedValue({
      date: baseBooking.booking_date_local,
      duration_minutes: baseBooking.duration_minutes,
      deposit_amount: 20,
      slots: [
        { slot_id: baseBooking.start_at, start_time: '12:00', end_time: '13:30', display_start_time: '12:00', display_end_time: '13:30', available: true, reason: null },
      ],
    });

    renderPage();

    await screen.findByRole('button', { name: 'Modifica intera serie' });
    fireEvent.click(screen.getByRole('button', { name: 'Modifica intera serie' }));
    fireEvent.change(screen.getByLabelText('Nome serie ricorrente'), { target: { value: 'Serie aggiornata admin' } });
    fireEvent.change(screen.getByLabelText('Fino al'), { target: { value: '2099-05-21' } });
    fireEvent.click(screen.getByRole('button', { name: 'Salva serie' }));

    await waitFor(() => expect(updateRecurringSeries).toHaveBeenCalledWith('series-1', expect.objectContaining({
      start_time: '12:00',
      slot_id: '2099-04-16T16:00:00Z',
      end_date: '2099-05-21',
    })));
  });

  it('saves an admin booking update using the current selected slot from the picker', async () => {
    renderPage();

    await screen.findByText('Dettaglio prenotazione');
    fireEvent.click(screen.getByRole('button', { name: 'Modifica data e orario' }));
    fireEvent.change(screen.getByLabelText('Nota'), { target: { value: 'Prenotazione aggiornata' } });
    fireEvent.click(screen.getByRole('button', { name: 'Salva modifica' }));

    await waitFor(() => expect(updateAdminBooking).toHaveBeenCalledWith('booking-1', expect.objectContaining({
      slot_id: '2099-04-16T16:00:00Z',
      start_time: '18:00',
      note: 'Prenotazione aggiornata',
    })));
    expect(screen.getByText('Prenotazione aggiornata con successo.')).toBeInTheDocument();
  });

  it('shows explicit play origin details for bookings generated from /play', async () => {
    vi.mocked(getAdminBooking).mockResolvedValue({ ...playOriginDetailBooking });

    renderPage();

    await screen.findByText('Dettaglio prenotazione');
    expect(screen.getByText('Play community')).toBeInTheDocument();
    expect(screen.getByText(/completamento di un match/)).toBeInTheDocument();
    expect(screen.getAllByText(/match-play-42/).length).toBeGreaterThan(0);
  });

  it('preserves the selected fallback slot id when editing a DST-ambiguous booking', async () => {
    vi.mocked(getAdminBooking).mockResolvedValue({
      ...baseBooking,
      start_at: '2026-10-25T01:00:00Z',
      end_at: '2026-10-25T02:00:00Z',
      duration_minutes: 60,
      booking_date_local: '2026-10-25',
    });
    vi.mocked(getAvailability).mockResolvedValue({
      date: '2026-10-25',
      duration_minutes: 60,
      deposit_amount: 20,
      slots: [
        { slot_id: '2026-10-25T00:00:00Z', start_time: '02:00', end_time: '02:00', display_start_time: '02:00 CEST', display_end_time: '02:00 CET', available: true, reason: null },
        { slot_id: '2026-10-25T01:00:00Z', start_time: '02:00', end_time: '03:00', display_start_time: '02:00 CET', display_end_time: '03:00', available: true, reason: null },
      ],
    });

    renderPage();

    await screen.findByText('Dettaglio prenotazione');
    fireEvent.click(screen.getByRole('button', { name: 'Modifica data e orario' }));
    fireEvent.click(screen.getByRole('button', { name: 'Salva modifica' }));

    await waitFor(() => expect(updateAdminBooking).toHaveBeenCalledWith('booking-1', expect.objectContaining({
      start_time: '02:00',
      slot_id: '2026-10-25T01:00:00Z',
      duration_minutes: 60,
    })));
  });
});
