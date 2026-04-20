import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminCurrentBookingsPage } from './AdminCurrentBookingsPage';

vi.mock('../services/adminApi', () => ({
  cancelRecurringSeries: vi.fn(),
  getAdminSession: vi.fn(),
  listAdminBookings: vi.fn(),
  logoutAdmin: vi.fn(),
  updateAdminBookingStatus: vi.fn(),
}));

import { cancelRecurringSeries, getAdminSession, listAdminBookings, logoutAdmin, updateAdminBookingStatus } from '../services/adminApi';
import type { BookingSummary } from '../types';

const currentWeekBooking: BookingSummary = {
  id: 'booking-current-1',
  public_reference: 'PB-WEEK-001',
  start_at: '2026-04-21T16:00:00Z',
  end_at: '2026-04-21T17:30:00Z',
  duration_minutes: 90,
  booking_date_local: '2026-04-21',
  status: 'CONFIRMED',
  deposit_amount: 20,
  payment_provider: 'STRIPE',
  payment_status: 'PAID',
  customer_name: 'Luca Bianchi',
  customer_email: 'luca@example.com',
  customer_phone: '3331239876',
  note: 'Partita serale',
  created_by: 'admin@padelbooking.app',
  source: 'PUBLIC',
  recurring_series_id: null,
  recurring_series_label: null,
  created_at: '2026-04-10T08:00:00Z',
  cancelled_at: null,
  completed_at: null,
  no_show_at: null,
  balance_paid_at: null,
};

const currentRecurringBooking: BookingSummary = {
  id: 'booking-current-2',
  public_reference: 'PB-WEEK-002',
  start_at: '2026-04-22T18:00:00Z',
  end_at: '2026-04-22T19:30:00Z',
  duration_minutes: 90,
  booking_date_local: '2026-04-22',
  status: 'NO_SHOW',
  deposit_amount: 0,
  payment_provider: 'NONE',
  payment_status: 'UNPAID',
  customer_name: 'Marco Verdi',
  customer_email: 'marco@example.com',
  customer_phone: '3334442222',
  note: 'Serie ricorrente',
  created_by: 'admin@padelbooking.app',
  source: 'ADMIN_RECURRING',
  recurring_series_id: 'series-42',
  recurring_series_label: 'Allenamento del mercoledi',
  created_at: '2026-04-10T08:00:00Z',
  cancelled_at: null,
  completed_at: null,
  no_show_at: '2026-04-22T19:35:00Z',
  balance_paid_at: null,
};

const cancelledBooking: BookingSummary = {
  ...currentWeekBooking,
  id: 'booking-cancelled',
  public_reference: 'PB-WEEK-CANCELLED',
  booking_date_local: '2026-04-23',
  start_at: '2026-04-23T10:00:00Z',
  end_at: '2026-04-23T11:30:00Z',
  status: 'CANCELLED',
  cancelled_at: '2026-04-22T10:00:00Z',
};

const januaryBooking: BookingSummary = {
  ...currentWeekBooking,
  id: 'booking-january',
  public_reference: 'PB-WEEK-JAN',
  booking_date_local: '2027-01-14',
  start_at: '2027-01-14T17:00:00Z',
  end_at: '2027-01-14T18:30:00Z',
  customer_name: 'Giulia Neri',
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/prenotazioni-attuali']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/admin' element={<div>CREATE PAGE</div>} />
        <Route path='/admin/prenotazioni-attuali' element={<AdminCurrentBookingsPage />} />
        <Route path='/admin/prenotazioni' element={<div>LIST PAGE</div>} />
        <Route path='/admin/log' element={<div>LOG PAGE</div>} />
        <Route path='/admin/login' element={<div>LOGIN PAGE</div>} />
        <Route path='/admin/bookings/:bookingId' element={<div>DETAIL PAGE</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('AdminCurrentBookingsPage', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date('2026-04-20T12:00:00Z'));
    vi.clearAllMocks();
    vi.mocked(getAdminSession).mockResolvedValue({ email: 'admin@padelbooking.app', full_name: 'Admin' });
    vi.mocked(logoutAdmin).mockResolvedValue({ message: 'ok' });
    vi.mocked(updateAdminBookingStatus).mockResolvedValue({ ...currentWeekBooking, status: 'CANCELLED', cancelled_at: '2026-04-20T12:05:00Z' });
    vi.mocked(cancelRecurringSeries).mockResolvedValue({ message: 'ok', cancelled_count: 3, skipped_count: 0, booking_ids: ['booking-current-2'], series_id: 'series-42' });
    vi.mocked(listAdminBookings).mockImplementation(async (filters) => {
      if (filters.start_date === '2027-01-11' && filters.end_date === '2027-01-17') {
        return { items: [januaryBooking], total: 1 };
      }

      return { items: [currentWeekBooking, currentRecurringBooking, cancelledBooking], total: 3 };
    });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('loads the current week by default and shows the updated admin navigation', async () => {
    renderPage();

    await screen.findByText('Calendario settimanale prenotazioni');
    await waitFor(() => expect(listAdminBookings).toHaveBeenLastCalledWith(expect.objectContaining({
      start_date: '2026-04-20',
      end_date: '2026-04-26',
    })));

    expect(screen.getByRole('link', { name: 'Crea Prenotazioni' })).toHaveAttribute('href', '/admin');
    expect(screen.getAllByRole('link', { name: 'Prenotazioni Attuali' })[0]).toHaveAttribute('href', '/admin/prenotazioni-attuali');
    expect(screen.getAllByRole('link', { name: 'Elenco Prenotazioni' })[0]).toHaveAttribute('href', '/admin/prenotazioni');
    expect(screen.getByRole('button', { name: 'Esci' })).toBeInTheDocument();
    expect(screen.getByText('Luca Bianchi')).toBeInTheDocument();
    expect(screen.getByText('Marco Verdi')).toBeInTheDocument();
    expect(screen.getByText('Allenamento del mercoledi')).toBeInTheDocument();
    expect(screen.getByText('Serie ricorrente')).toBeInTheDocument();
    expect(screen.queryByText('PB-WEEK-CANCELLED')).not.toBeInTheDocument();
  });

  it('allows cancelling a single saved booking from the weekly calendar', async () => {
    renderPage();

    await screen.findByText('Calendario settimanale prenotazioni');
    fireEvent.click(screen.getByLabelText('Annulla PB-WEEK-001'));

    await waitFor(() => expect(updateAdminBookingStatus).toHaveBeenCalledWith('booking-current-1', { status: 'CANCELLED' }));
    expect(screen.getByText('Prenotazione annullata con successo.')).toBeInTheDocument();
  });

  it('allows cancelling the full recurring series from the weekly calendar', async () => {
    renderPage();

    await screen.findByText('Calendario settimanale prenotazioni');
    fireEvent.click(screen.getByLabelText('Annulla serie Allenamento del mercoledi'));

    await waitFor(() => expect(cancelRecurringSeries).toHaveBeenCalledWith('series-42'));
    expect(screen.getByText('Serie aggiornata: 3 occorrenze future annullate, 0 saltate.')).toBeInTheDocument();
  });

  it('limits quick navigation to two weeks back from the current week', async () => {
    renderPage();

    await screen.findByText('Calendario settimanale prenotazioni');
    const previousButton = screen.getByRole('button', { name: 'Settimana precedente' });

    fireEvent.click(previousButton);
    await waitFor(() => expect(listAdminBookings).toHaveBeenLastCalledWith(expect.objectContaining({
      start_date: '2026-04-13',
      end_date: '2026-04-19',
    })));

    fireEvent.click(previousButton);
    await waitFor(() => expect(listAdminBookings).toHaveBeenLastCalledWith(expect.objectContaining({
      start_date: '2026-04-06',
      end_date: '2026-04-12',
    })));

    await waitFor(() => expect(previousButton).toBeDisabled());
  });

  it('limits quick navigation to four weeks ahead from the current week', async () => {
    renderPage();

    await screen.findByText('Calendario settimanale prenotazioni');
    const nextButton = screen.getByRole('button', { name: 'Settimana successiva' });

    for (const expectedStartDate of ['2026-04-27', '2026-05-04', '2026-05-11', '2026-05-18']) {
      fireEvent.click(nextButton);
      await waitFor(() => expect(listAdminBookings).toHaveBeenLastCalledWith(expect.objectContaining({
        start_date: expectedStartDate,
      })));
    }

    await waitFor(() => expect(nextButton).toBeDisabled());
  });

  it('jumps to the selected month, week and year and opens the booking detail to modify the booking', async () => {
    renderPage();

    await screen.findByText('Calendario settimanale prenotazioni');
    fireEvent.change(screen.getByLabelText('Anno'), { target: { value: '2027' } });
    fireEvent.change(screen.getByLabelText('Mese'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('Settimana del mese'), { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Vai alla settimana' }));

    await waitFor(() => expect(listAdminBookings).toHaveBeenLastCalledWith(expect.objectContaining({
      start_date: '2027-01-11',
      end_date: '2027-01-17',
    })));

    fireEvent.click(screen.getByLabelText('Modifica PB-WEEK-JAN'));
    await screen.findByText('DETAIL PAGE');
  });
});