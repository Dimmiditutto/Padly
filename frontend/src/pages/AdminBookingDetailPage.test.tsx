import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminBookingDetailPage } from './AdminBookingDetailPage';

vi.mock('../services/adminApi', () => ({
  getAdminBooking: vi.fn(),
  getAdminSession: vi.fn(),
  markAdminBalancePaid: vi.fn(),
  updateAdminBookingStatus: vi.fn(),
}));

import { getAdminBooking, getAdminSession, markAdminBalancePaid, updateAdminBookingStatus } from '../services/adminApi';

const baseBooking = {
  id: 'booking-1',
  public_reference: 'PB-BOOK-001',
  start_at: '2024-04-16T09:00:00Z',
  end_at: '2024-04-16T10:30:00Z',
  duration_minutes: 90,
  booking_date_local: '2026-04-16',
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
    renderPage();

    await screen.findByText('Dettaglio prenotazione');
    fireEvent.click(screen.getByRole('button', { name: 'Segna saldo al campo' }));

    await waitFor(() => expect(screen.getByText('Saldo segnato come pagato al campo.')).toBeInTheDocument());
  });

  it('shows backend errors when a booking action fails', async () => {
    vi.mocked(markAdminBalancePaid).mockRejectedValue({ response: { data: { detail: 'Saldo non registrato' } } });

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
});