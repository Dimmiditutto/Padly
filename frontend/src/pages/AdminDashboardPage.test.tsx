import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
  listAdminBookings: vi.fn(),
  listAdminEvents: vi.fn(),
  listBlackouts: vi.fn(),
  logoutAdmin: vi.fn(),
  markAdminBalancePaid: vi.fn(),
  previewRecurring: vi.fn(),
  updateAdminBookingStatus: vi.fn(),
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
  listAdminBookings,
  listAdminEvents,
  listBlackouts,
  logoutAdmin,
  markAdminBalancePaid,
  previewRecurring,
  updateAdminBookingStatus,
  updateAdminSettings,
} from '../services/adminApi';
import { getAvailability } from '../services/publicApi';

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={['/admin']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/admin' element={<AdminDashboardPage />} />
        <Route path='/admin/login' element={<div>LOGIN PAGE</div>} />
      </Routes>
    </MemoryRouter>
  );
}

function mockBootstrapSuccess() {
  vi.mocked(getAdminSession).mockResolvedValue({ email: 'admin@padelbooking.app', full_name: 'Admin' });
  vi.mocked(listAdminBookings).mockResolvedValue({ items: [], total: 0 });
  vi.mocked(getAdminReport).mockResolvedValue({ total_bookings: 0, confirmed_bookings: 0, pending_bookings: 0, cancelled_bookings: 0, collected_deposits: 0 });
  vi.mocked(listAdminEvents).mockResolvedValue([]);
  vi.mocked(listBlackouts).mockResolvedValue([]);
  vi.mocked(getAdminSettings).mockResolvedValue({
    timezone: 'Europe/Rome',
    currency: 'EUR',
    booking_hold_minutes: 15,
    cancellation_window_hours: 24,
    reminder_window_hours: 24,
    stripe_enabled: true,
    paypal_enabled: true,
  });
}

describe('AdminDashboardPage bootstrap', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBootstrapSuccess();
    vi.mocked(createAdminBooking).mockResolvedValue({} as never);
    vi.mocked(createBlackout).mockResolvedValue({ id: 'blackout-1', message: 'ok' });
    vi.mocked(createRecurring).mockResolvedValue({ series_id: 'series-1', created_count: 1, skipped_count: 0, skipped: [] });
    vi.mocked(logoutAdmin).mockResolvedValue({ message: 'ok' });
    vi.mocked(markAdminBalancePaid).mockResolvedValue({} as never);
    vi.mocked(previewRecurring).mockResolvedValue({ occurrences: [] });
    vi.mocked(updateAdminBookingStatus).mockResolvedValue({} as never);
    vi.mocked(updateAdminSettings).mockResolvedValue({
      timezone: 'Europe/Rome',
      currency: 'EUR',
      booking_hold_minutes: 15,
      cancellation_window_hours: 24,
      reminder_window_hours: 24,
      stripe_enabled: true,
      paypal_enabled: true,
    });
    vi.mocked(getAvailability).mockResolvedValue({
      date: '2099-04-16',
      duration_minutes: 90,
      deposit_amount: 20,
      slots: [
        { slot_id: '2099-04-16T16:00:00Z', start_time: '18:00', end_time: '19:30', display_start_time: '18:00', display_end_time: '19:30', available: true, reason: null },
      ],
    });
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

  it('closes loading and shows feedback when session validation fails without 401', async () => {
    vi.mocked(getAdminSession).mockRejectedValue({ response: { status: 500, data: { detail: 'Sessione non disponibile' } } });

    renderDashboard();

    await waitFor(() => expect(screen.getByText('Sessione non disponibile')).toBeInTheDocument());
    expect(screen.queryByText(/Sto sincronizzando dashboard/)).not.toBeInTheDocument();
    expect(screen.queryByText('LOGIN PAGE')).not.toBeInTheDocument();
  });

  it('shows feedback when a manual refresh fails', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');
    vi.mocked(listAdminBookings).mockRejectedValueOnce({ response: { status: 500, data: { detail: 'Refresh non disponibile' } } });

    fireEvent.click(screen.getByRole('button', { name: 'Aggiorna' }));

    await waitFor(() => expect(screen.getByText('Refresh non disponibile')).toBeInTheDocument());
  });

  it('shows feedback when filter application fails', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');
    vi.mocked(listAdminBookings).mockRejectedValueOnce({ response: { status: 500, data: { detail: 'Filtro non disponibile' } } });

    fireEvent.click(screen.getByRole('button', { name: 'Filtra' }));

    await waitFor(() => expect(screen.getByText('Filtro non disponibile')).toBeInTheDocument());
  });

  it('submits the selected fallback slot_id for ambiguous manual bookings', async () => {
    vi.mocked(getAvailability).mockResolvedValue({
      date: '2026-10-25',
      duration_minutes: 60,
      deposit_amount: 20,
      slots: [
        { slot_id: '2026-10-25T00:00:00Z', start_time: '02:00', end_time: '02:00', display_start_time: '02:00 CEST', display_end_time: '02:00 CET', available: true, reason: null },
        { slot_id: '2026-10-25T01:00:00Z', start_time: '02:00', end_time: '03:00', display_start_time: '02:00 CET', display_end_time: '03:00', available: true, reason: null },
      ],
    });

    renderDashboard();

    await screen.findByText('Dashboard admin');
    const createButton = screen.getByRole('button', { name: 'Crea prenotazione' });
    const form = createButton.closest('form');
    if (!form) {
      throw new Error('Form prenotazione manuale non trovato');
    }

    const timeInput = form.querySelector("input[type='time']") as HTMLInputElement | null;
    if (!timeInput) {
      throw new Error('Campo orario manuale non trovato');
    }

    fireEvent.change(timeInput, { target: { value: '02:00' } });

    await screen.findByLabelText('Occorrenza slot');
    fireEvent.change(screen.getByLabelText('Occorrenza slot'), { target: { value: '2026-10-25T01:00:00Z' } });
    fireEvent.click(createButton);

    await waitFor(() => expect(createAdminBooking).toHaveBeenCalledWith(expect.objectContaining({
      start_time: '02:00',
      slot_id: '2026-10-25T01:00:00Z',
    })));
  });
});