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

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={['/admin']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/admin' element={<AdminDashboardPage />} />
        <Route path='/admin/login' element={<div>LOGIN PAGE</div>} />
        <Route path='/admin/prenotazioni' element={<div>BOOKINGS PAGE</div>} />
        <Route path='/admin/log' element={<div>LOG PAGE</div>} />
      </Routes>
    </MemoryRouter>
  );
}

function mockBootstrapSuccess() {
  vi.mocked(getAdminSession).mockResolvedValue({ email: 'admin@padelbooking.app', full_name: 'Admin' });
  vi.mocked(getAdminReport).mockResolvedValue({ total_bookings: 0, confirmed_bookings: 0, pending_bookings: 0, cancelled_bookings: 0, collected_deposits: 0 });
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

describe('AdminDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBootstrapSuccess();
    vi.mocked(createAdminBooking).mockResolvedValue({} as never);
    vi.mocked(createBlackout).mockResolvedValue({ id: 'blackout-1', message: 'ok' });
    vi.mocked(createRecurring).mockResolvedValue({ series_id: 'series-1', created_count: 1, skipped_count: 0, skipped: [] });
    vi.mocked(logoutAdmin).mockResolvedValue({ message: 'ok' });
    vi.mocked(previewRecurring).mockResolvedValue({ occurrences: [] });
    vi.mocked(updateAdminSettings).mockResolvedValue({
      timezone: 'Europe/Rome',
      currency: 'EUR',
      booking_hold_minutes: 15,
      cancellation_window_hours: 24,
      reminder_window_hours: 24,
      stripe_enabled: true,
      paypal_enabled: true,
    });
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

  it('links the dashboard to the dedicated bookings and log pages', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');
    expect(screen.getByRole('link', { name: 'Apri prenotazioni' })).toHaveAttribute('href', '/admin/prenotazioni');
    expect(screen.getByRole('link', { name: 'Apri log' })).toHaveAttribute('href', '/admin/log');
  });

  it('submits a manual booking after selecting a slot from the compact picker', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.click(screen.getAllByRole('button', { name: '18:00' })[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Crea prenotazione' }));

    await waitFor(() => expect(createAdminBooking).toHaveBeenCalledWith(expect.objectContaining({
      start_time: '18:00',
      slot_id: '2099-04-16T16:00:00Z',
    })));
  });

  it('derives the recurring weekday from the selected start date and forwards the selected recurring slot_id', async () => {
    renderDashboard();

    await screen.findByText('Dashboard admin');
    fireEvent.change(screen.getByLabelText('Data di partenza'), { target: { value: '2026-10-25' } });

    const recurringSection = screen.getByText('Serie ricorrente').closest('section');
    expect(recurringSection).not.toBeNull();

    await waitFor(() => expect(within(recurringSection as HTMLElement).getByRole('button', { name: '02:00 CET' })).toBeInTheDocument());

    fireEvent.click(within(recurringSection as HTMLElement).getByRole('button', { name: '02:00 CET' }));
    fireEvent.click(within(recurringSection as HTMLElement).getByRole('button', { name: 'Crea serie' }));

    await waitFor(() => expect(createRecurring).toHaveBeenCalledWith(expect.objectContaining({
      start_date: '2026-10-25',
      weekday: 6,
      start_time: '02:00',
      slot_id: '2026-10-25T01:00:00+00:00',
    })));
  });
});
