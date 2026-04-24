import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminBookingsPage } from './AdminBookingsPage';

vi.mock('../services/adminApi', () => ({
  cancelRecurringOccurrences: vi.fn(),
  cancelRecurringSeries: vi.fn(),
  deleteAdminBooking: vi.fn(),
  deleteRecurringSeries: vi.fn(),
  getAdminSession: vi.fn(),
  listAdminBookings: vi.fn(),
  logoutAdmin: vi.fn(),
  markAdminBalancePaid: vi.fn(),
  updateAdminBookingStatus: vi.fn(),
}));

import {
  cancelRecurringOccurrences,
  cancelRecurringSeries,
  deleteAdminBooking,
  deleteRecurringSeries,
  getAdminSession,
  listAdminBookings,
  logoutAdmin,
  markAdminBalancePaid,
  updateAdminBookingStatus,
} from '../services/adminApi';
import type { BookingSummary } from '../types';

const adminSession = {
  email: 'admin@padelbooking.app',
  full_name: 'Admin',
  role: 'SUPERADMIN',
  club_id: 'club-default',
  club_slug: 'default-club',
  club_public_name: 'PadelBooking',
  timezone: 'Europe/Rome',
} as const;

const singleBooking: BookingSummary = {
  id: 'booking-public-1',
  public_reference: 'PB-BOOK-100',
  start_at: '2099-04-16T16:00:00Z',
  end_at: '2099-04-16T17:30:00Z',
  duration_minutes: 90,
  booking_date_local: '2099-04-16',
  status: 'CONFIRMED',
  deposit_amount: 20,
  payment_provider: 'STRIPE',
  payment_status: 'PAID',
  customer_name: 'Cliente Singolo',
  customer_email: 'single@example.com',
  customer_phone: '3331231234',
  note: 'Prenotazione singola',
  created_by: 'admin@padelbooking.app',
  source: 'PUBLIC',
  recurring_series_id: null,
  recurring_series_label: null,
  created_at: '2024-04-10T08:00:00Z',
  cancelled_at: null,
  completed_at: null,
  no_show_at: null,
  balance_paid_at: null,
};

const playOriginBooking: BookingSummary = {
  ...singleBooking,
  id: 'booking-play-1',
  public_reference: 'PB-PLAY-100',
  customer_name: 'Match /play completato',
  customer_email: null,
  customer_phone: null,
  payment_provider: 'NONE',
  payment_status: 'UNPAID',
  created_by: 'play:match-play-42',
  source: 'ADMIN_MANUAL',
  note: 'Booking finale nata da match /play',
};

const recurringBookings: BookingSummary[] = [
  {
    id: 'rec-1',
    public_reference: 'PB-REC-001',
    start_at: '2099-04-17T18:00:00Z',
    end_at: '2099-04-17T19:30:00Z',
    duration_minutes: 90,
    booking_date_local: '2099-04-17',
    status: 'CONFIRMED',
    deposit_amount: 0,
    payment_provider: 'NONE',
    payment_status: 'UNPAID',
    customer_name: 'Mario Rossi',
    customer_email: null,
    customer_phone: null,
    note: 'Serie ricorrente: Corso serale',
    created_by: 'admin@padelbooking.app',
    source: 'ADMIN_RECURRING',
    recurring_series_id: 'series-1',
    recurring_series_label: 'Corso serale',
    created_at: '2024-04-10T08:00:00Z',
    cancelled_at: null,
    completed_at: null,
    no_show_at: null,
    balance_paid_at: null,
  },
  {
    id: 'rec-2',
    public_reference: 'PB-REC-002',
    start_at: '2099-04-24T18:00:00Z',
    end_at: '2099-04-24T19:30:00Z',
    duration_minutes: 90,
    booking_date_local: '2099-04-24',
    status: 'CONFIRMED',
    deposit_amount: 0,
    payment_provider: 'NONE',
    payment_status: 'UNPAID',
    customer_name: 'Mario Rossi',
    customer_email: null,
    customer_phone: null,
    note: 'Serie ricorrente: Corso serale',
    created_by: 'admin@padelbooking.app',
    source: 'ADMIN_RECURRING',
    recurring_series_id: 'series-1',
    recurring_series_label: 'Corso serale',
    created_at: '2024-04-10T08:00:00Z',
    cancelled_at: null,
    completed_at: null,
    no_show_at: null,
    balance_paid_at: null,
  },
];

const cancelledSingleBooking: BookingSummary = {
  ...singleBooking,
  id: 'booking-public-cancelled',
  public_reference: 'PB-BOOK-CANCELLED',
  customer_name: 'Cliente Cancellato',
  status: 'CANCELLED',
  cancelled_at: '2024-04-11T08:00:00Z',
};

const cancelledRecurringBookings: BookingSummary[] = recurringBookings.map((booking, index) => ({
  ...booking,
  id: `rec-cancelled-${index + 1}`,
  public_reference: `PB-REC-CANCELLED-${index + 1}`,
  recurring_series_id: 'series-cancelled',
  recurring_series_label: 'Corso cancellato',
  status: 'CANCELLED',
  cancelled_at: '2024-04-11T08:00:00Z',
}));

function renderPage(path = '/admin/prenotazioni') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/admin/prenotazioni' element={<AdminBookingsPage />} />
        <Route path='/admin/prenotazioni-attuali' element={<div>CURRENT BOOKINGS PAGE</div>} />
        <Route path='/admin/login' element={<div>LOGIN PAGE</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('AdminBookingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAdminSession).mockResolvedValue({ ...adminSession });
    vi.mocked(listAdminBookings).mockResolvedValue({ items: [singleBooking, ...recurringBookings], total: 3 });
    vi.mocked(logoutAdmin).mockResolvedValue({ message: 'ok' });
    vi.mocked(cancelRecurringOccurrences).mockResolvedValue({ message: 'ok', cancelled_count: 1, skipped_count: 0, booking_ids: ['rec-1'], series_id: null });
    vi.mocked(cancelRecurringSeries).mockResolvedValue({ message: 'ok', cancelled_count: 2, skipped_count: 0, booking_ids: ['rec-1', 'rec-2'], series_id: 'series-1' });
    vi.mocked(deleteAdminBooking).mockResolvedValue({ message: 'Prenotazione eliminata definitivamente.' });
    vi.mocked(deleteRecurringSeries).mockResolvedValue({ message: 'Serie ricorrente eliminata definitivamente.' });
    vi.mocked(markAdminBalancePaid).mockResolvedValue({} as never);
    vi.mocked(updateAdminBookingStatus).mockResolvedValue({} as never);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('groups recurring bookings and submits filters by period and query', async () => {
    renderPage();

    await screen.findByText('Ricerca avanzata e gestione ricorrenze');
    expect(screen.queryByText('Tenant attivo: PadelBooking')).not.toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Prenotazioni Attuali' })[0]).toHaveAttribute('href', '/admin/prenotazioni-attuali');
    expect(screen.getByRole('link', { name: 'Elenco Prenotazioni' })).toHaveAttribute('href', '/admin/prenotazioni');
    expect(screen.queryByRole('link', { name: 'Log' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Aggiorna pagina' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Esci' })).toBeInTheDocument();
    expect(screen.getByText('Corso serale')).toBeInTheDocument();
    expect(screen.getByText('Cliente Singolo')).toBeInTheDocument();
    expect(screen.queryByText('PB-BOOK-100')).not.toBeInTheDocument();
    expect(screen.getAllByText('Durata 90 minuti').length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText('Data inizio'), { target: { value: '2099-04-16' } });
    fireEvent.change(screen.getByLabelText('Data fine'), { target: { value: '2099-04-24' } });
    fireEvent.change(screen.getByLabelText('Cliente o serie'), { target: { value: 'Corso serale' } });
    fireEvent.click(screen.getByRole('button', { name: 'Applica filtri' }));

    await waitFor(() => expect(listAdminBookings).toHaveBeenLastCalledWith(expect.objectContaining({
      start_date: '2099-04-16',
      end_date: '2099-04-24',
      query: 'Corso serale',
    })));
  });

  it('cancels selected recurring occurrences from the grouped accordion', async () => {
    renderPage();

    await screen.findByText('Ricerca avanzata e gestione ricorrenze');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi' }));
    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Annulla selezionate' }));

    await waitFor(() => expect(cancelRecurringOccurrences).toHaveBeenCalledWith(['rec-1']));
    expect(screen.getByText('Occorrenze aggiornate: 1 annullate, 0 saltate.')).toBeInTheDocument();
  });

  it('cancels the full recurring series from the grouped actions', async () => {
    renderPage();

    await screen.findByText('Ricerca avanzata e gestione ricorrenze');
    fireEvent.click(screen.getByRole('button', { name: 'Annulla tutta la serie' }));

    await waitFor(() => expect(cancelRecurringSeries).toHaveBeenCalledWith('series-1'));
    expect(screen.getByText('Serie aggiornata: 2 occorrenze future annullate, 0 saltate.')).toBeInTheDocument();
  });

  it('deletes a cancelled single booking from the list', async () => {
    vi.mocked(listAdminBookings).mockResolvedValue({ items: [cancelledSingleBooking], total: 1 });

    renderPage();

    await screen.findByText('Cliente Cancellato');
    fireEvent.click(screen.getByRole('button', { name: 'Elimina' }));

    await waitFor(() => expect(deleteAdminBooking).toHaveBeenCalledWith('booking-public-cancelled'));
    expect(screen.getByText('Prenotazione eliminata definitivamente.')).toBeInTheDocument();
  });

  it('deletes a cancelled recurring occurrence from the grouped list', async () => {
    vi.mocked(listAdminBookings).mockResolvedValue({ items: cancelledRecurringBookings, total: 2 });

    renderPage();

    await screen.findByText('Corso cancellato');
    fireEvent.click(screen.getByRole('button', { name: 'Espandi' }));
    fireEvent.click(screen.getByRole('button', { name: 'Elimina singola Mario Rossi 2099-04-17' }));

    await waitFor(() => expect(deleteAdminBooking).toHaveBeenCalledWith('rec-cancelled-1'));
    expect(screen.getByText('Prenotazione eliminata definitivamente.')).toBeInTheDocument();
  });

  it('deletes a cancelled recurring series from the grouped actions', async () => {
    vi.mocked(listAdminBookings).mockResolvedValue({ items: cancelledRecurringBookings, total: 2 });

    renderPage();

    await screen.findByText('Corso cancellato');
    fireEvent.click(screen.getByRole('button', { name: 'Elimina tutta la serie' }));

    await waitFor(() => expect(deleteRecurringSeries).toHaveBeenCalledWith('series-cancelled'));
    expect(screen.getByText('Serie ricorrente eliminata definitivamente.')).toBeInTheDocument();
  });

  it('preserves tenant query in admin nav and booking detail links', async () => {
    vi.mocked(getAdminSession).mockResolvedValue({
      email: 'admin@roma-club.example',
      full_name: 'Admin Roma',
      role: 'SUPERADMIN',
      club_id: 'club-roma',
      club_slug: 'roma-club',
      club_public_name: 'Roma Club',
      timezone: 'Europe/Rome',
    });

    renderPage('/admin/prenotazioni?tenant=roma-club');

    await screen.findByText('Ricerca avanzata e gestione ricorrenze');
    expect(screen.queryByText('Tenant attivo: Roma Club')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Crea Prenotazioni' })).toHaveAttribute('href', '/admin?tenant=roma-club');
    expect(screen.getAllByRole('link', { name: 'Prenotazioni Attuali' })[0]).toHaveAttribute('href', '/admin/prenotazioni-attuali?tenant=roma-club');
    expect(screen.getByRole('link', { name: 'Elenco Prenotazioni' })).toHaveAttribute('href', '/admin/prenotazioni?tenant=roma-club');
    expect(screen.getAllByRole('link', { name: /Dettaglio/ })[0]).toHaveAttribute('href', '/admin/bookings/booking-public-1?tenant=roma-club');
  });

  it('marks and filters bookings originating from /play', async () => {
    vi.mocked(listAdminBookings).mockResolvedValue({ items: [singleBooking, playOriginBooking, ...recurringBookings], total: 4 });

    renderPage();

    await screen.findByText('Ricerca avanzata e gestione ricorrenze');
    expect(screen.getByText('Booking da /play')).toBeInTheDocument();
    expect(screen.getByText('Match /play completato')).toBeInTheDocument();
    expect(screen.getAllByText('Play community').length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText('Origine'), { target: { value: 'PLAY_ONLY' } });

    expect(screen.getByText('Match /play completato')).toBeInTheDocument();
    expect(screen.queryByText('Cliente Singolo')).not.toBeInTheDocument();
    expect(screen.queryByText('Corso serale')).not.toBeInTheDocument();
  });
});
