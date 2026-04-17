import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminBookingDetailPage } from './AdminBookingDetailPage';

vi.mock('../services/adminApi', () => ({
  getAdminBooking: vi.fn(),
  getAdminSession: vi.fn(),
  markAdminBalancePaid: vi.fn(),
  updateAdminBooking: vi.fn(),
  updateAdminBookingStatus: vi.fn(),
}));

vi.mock('../services/publicApi', () => ({
  getAvailability: vi.fn(),
}));

import { getAdminBooking, getAdminSession, markAdminBalancePaid, updateAdminBooking, updateAdminBookingStatus } from '../services/adminApi';
import { getAvailability } from '../services/publicApi';

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
  created_at: '2024-04-10T08:00:00Z',
  cancelled_at: null,
  completed_at: null,
  no_show_at: null,
  balance_paid_at: null,
  payment_reference: 'pi_test_123',
} as const;

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/bookings/booking-1']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/admin/bookings/:bookingId' element={<AdminBookingDetailPage />} />
        <Route path='/admin' element={<div>ADMIN DASHBOARD</div>} />
        <Route path='/admin/login' element={<div>LOGIN PAGE</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('AdminBookingDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAdminSession).mockResolvedValue({ email: 'admin@padelbooking.app', full_name: 'Admin' });
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
    vi.mocked(markAdminBalancePaid).mockResolvedValue({ ...baseBooking, balance_paid_at: '2024-04-16T12:06:00Z' });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('redirects to login when the admin session returns 401', async () => {
    vi.mocked(getAdminSession).mockRejectedValue({ response: { status: 401, data: { detail: 'Unauthorized' } } });

    renderPage();

    await screen.findByText('LOGIN PAGE');
  });

  it('shows a readable error when booking detail loading fails for non-auth reasons', async () => {
    vi.mocked(getAdminBooking).mockRejectedValue({ response: { status: 500, data: { detail: 'Dettaglio prenotazione non disponibile' } } });

    renderPage();

    await waitFor(() => expect(screen.getByText('Dettaglio prenotazione non disponibile')).toBeInTheDocument());
    expect(screen.queryByText('LOGIN PAGE')).not.toBeInTheDocument();
  });

  it('updates status successfully and clears previous errors', async () => {
    vi.mocked(updateAdminBookingStatus)
      .mockRejectedValueOnce({ response: { data: { detail: 'Aggiornamento stato non riuscito' } } })
      .mockResolvedValueOnce({ ...baseBooking, status: 'CANCELLED', cancelled_at: '2024-04-16T12:05:00Z' });

    renderPage();

    await screen.findByText('Dettaglio prenotazione');
    fireEvent.click(screen.getByRole('button', { name: 'Annulla prenotazione' }));

    await waitFor(() => expect(screen.getByText('Aggiornamento stato non riuscito')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Annulla prenotazione' }));

    await waitFor(() => expect(screen.getByText('Stato aggiornato a CANCELLED.')).toBeInTheDocument());
    expect(screen.queryByText('Aggiornamento stato non riuscito')).not.toBeInTheDocument();
  });

  it('marks the balance as paid and shows coherent feedback', async () => {
    vi.mocked(getAdminBooking).mockResolvedValue({
      ...baseBooking,
      start_at: '2024-04-16T09:00:00Z',
      end_at: '2024-04-16T10:30:00Z',
      booking_date_local: '2024-04-16',
    });

    renderPage();

    await screen.findByText('Dettaglio prenotazione');
    fireEvent.click(screen.getByRole('button', { name: 'Segna saldo al campo' }));

    await waitFor(() => expect(screen.getByText('Saldo segnato come pagato al campo.')).toBeInTheDocument());
  });

  it('shows backend errors when a booking action fails', async () => {
    vi.mocked(markAdminBalancePaid).mockRejectedValue({ response: { data: { detail: 'Saldo non registrato' } } });
    vi.mocked(getAdminBooking).mockResolvedValue({
      ...baseBooking,
      start_at: '2024-04-16T09:00:00Z',
      end_at: '2024-04-16T10:30:00Z',
      booking_date_local: '2024-04-16',
    });

    renderPage();

    await screen.findByText('Dettaglio prenotazione');
    fireEvent.click(screen.getByRole('button', { name: 'Segna saldo al campo' }));

    await waitFor(() => expect(screen.getByText('Saldo non registrato')).toBeInTheDocument());
  });

  it('shows the restore button only when the booking status is restorable', async () => {
    vi.mocked(getAdminBooking).mockResolvedValue({
      ...baseBooking,
      status: 'COMPLETED',
      completed_at: '2024-04-16T11:00:00Z',
    });

    renderPage();

    await screen.findByText('Dettaglio prenotazione');
    expect(screen.getByRole('button', { name: 'Ripristina confermata' })).toBeInTheDocument();
  });

  it('saves an admin booking update and shows coherent feedback', async () => {
    renderPage();

    await screen.findByText('Dettaglio prenotazione');
    fireEvent.click(screen.getByRole('button', { name: 'Modifica data e orario' }));
    fireEvent.change(screen.getByLabelText('Nota'), { target: { value: 'Prenotazione aggiornata' } });
    fireEvent.click(screen.getByRole('button', { name: 'Salva modifica' }));

    await waitFor(() => expect(screen.getByText('Prenotazione aggiornata con successo.')).toBeInTheDocument());
    expect(updateAdminBooking).toHaveBeenCalled();
  });

  it('shows backend errors when an admin booking update fails', async () => {
    vi.mocked(updateAdminBooking).mockRejectedValue({ response: { data: { detail: 'Slot non piu disponibile' } } });

    renderPage();

    await screen.findByText('Dettaglio prenotazione');
    fireEvent.click(screen.getByRole('button', { name: 'Modifica data e orario' }));
    fireEvent.click(screen.getByRole('button', { name: 'Salva modifica' }));

    await waitFor(() => expect(screen.getByText('Slot non piu disponibile')).toBeInTheDocument());
  });

  it('preserves the selected fallback slot_id when the local start time is ambiguous', async () => {
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

    await screen.findByLabelText('Occorrenza slot');
    fireEvent.change(screen.getByLabelText('Occorrenza slot'), { target: { value: '2026-10-25T01:00:00Z' } });
    fireEvent.click(screen.getByRole('button', { name: 'Salva modifica' }));

    await waitFor(() => expect(updateAdminBooking).toHaveBeenCalledWith('booking-1', expect.objectContaining({
      start_time: '02:00',
      slot_id: '2026-10-25T01:00:00Z',
      duration_minutes: 60,
    })));
  });

  it('disables slot editing for confirmed bookings already in the past', async () => {
    vi.mocked(getAdminBooking).mockResolvedValue({
      ...baseBooking,
      start_at: '2024-04-16T09:00:00Z',
      end_at: '2024-04-16T10:30:00Z',
      booking_date_local: '2024-04-16',
    });

    renderPage();

    await screen.findByText('Dettaglio prenotazione');
    expect(screen.getByRole('button', { name: 'Modifica data e orario' })).toBeDisabled();
    expect(screen.getByText('La modifica e disponibile solo per prenotazioni future.')).toBeInTheDocument();
  });
});