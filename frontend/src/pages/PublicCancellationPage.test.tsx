import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PublicCancellationPage } from './PublicCancellationPage';

vi.mock('../services/publicApi', () => ({
  cancelPublicBooking: vi.fn(),
  getPublicCancellation: vi.fn(),
  getPublicConfig: vi.fn(),
}));

import { cancelPublicBooking, getPublicCancellation, getPublicConfig } from '../services/publicApi';

const previewPayload = {
  booking: {
    id: 'booking-1',
    public_reference: 'PB-CANCEL-001',
    start_at: '2026-05-01T18:00:00Z',
    end_at: '2026-05-01T19:30:00Z',
    duration_minutes: 90,
    booking_date_local: '2026-05-01',
    status: 'CONFIRMED',
    deposit_amount: 20,
    payment_provider: 'STRIPE',
    payment_status: 'PAID',
    created_at: '2026-04-20T09:00:00Z',
    cancelled_at: null,
    completed_at: null,
    no_show_at: null,
    balance_paid_at: null,
  },
  cancellable: true,
  cancellation_reason: null,
  refund_required: true,
  refund_status: 'PENDING',
  refund_amount: 20,
  refund_message: 'Confermando l\'annullamento la caparra verra rimborsata automaticamente.',
  message: null,
} as const;

function renderPage(path = '/booking/cancel?token=cancel-token-1') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <PublicCancellationPage />
    </MemoryRouter>
  );
}

describe('PublicCancellationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getPublicCancellation).mockResolvedValue({ ...previewPayload });
    vi.mocked(cancelPublicBooking).mockResolvedValue({
      ...previewPayload,
      booking: { ...previewPayload.booking, status: 'CANCELLED', cancelled_at: '2026-04-20T09:10:00Z' },
      cancellable: false,
      cancellation_reason: 'Prenotazione gia annullata',
      refund_status: 'SUCCEEDED',
      refund_message: 'Caparra rimborsata automaticamente.',
      message: 'Prenotazione annullata e caparra rimborsata automaticamente',
    });
    vi.mocked(getPublicConfig).mockResolvedValue({
      app_name: 'PadelBooking',
      tenant_id: 'club-1',
      tenant_slug: 'default-club',
      public_name: 'PadelBooking Savona',
      timezone: 'Europe/Rome',
      currency: 'EUR',
      contact_email: 'help@padelbooking.app',
      support_email: 'help@padelbooking.app',
      support_phone: '+390101010101',
      booking_hold_minutes: 15,
      cancellation_window_hours: 24,
      stripe_enabled: true,
      paypal_enabled: true,
    });
  });

  it('completes the public cancellation flow and shows the refund result', async () => {
    renderPage();

    await screen.findByText('Annullamento self-service');
    fireEvent.click(screen.getByRole('button', { name: 'Conferma annullamento e rimborso' }));

    await waitFor(() => expect(screen.getByText('Prenotazione annullata e caparra rimborsata automaticamente')).toBeInTheDocument());
    expect(getPublicCancellation).toHaveBeenCalledWith('cancel-token-1', null);
    expect(getPublicConfig).toHaveBeenCalledWith(null);
    expect(cancelPublicBooking).toHaveBeenCalledWith('cancel-token-1', null);
  });

  it('shows a clear no-refund warning for late cancellations', async () => {
    vi.mocked(getPublicCancellation).mockResolvedValueOnce({
      ...previewPayload,
      refund_required: false,
      refund_status: 'NOT_REQUIRED',
      refund_message: 'Annullando nelle ultime 24 ore la caparra non verra rimborsata automaticamente.',
    });
    vi.mocked(cancelPublicBooking).mockResolvedValueOnce({
      ...previewPayload,
      booking: { ...previewPayload.booking, status: 'CANCELLED', cancelled_at: '2026-04-20T09:10:00Z' },
      cancellable: false,
      cancellation_reason: 'Prenotazione gia annullata',
      refund_required: false,
      refund_status: 'NOT_REQUIRED',
      refund_message: 'Nessun rimborso automatico: la cancellazione e avvenuta nelle ultime 24 ore.',
      message: 'Prenotazione annullata. Annullando nelle ultime 24 ore la caparra non verra rimborsata automaticamente.',
    });

    renderPage();

    await screen.findByText('Annullamento self-service');
    expect(screen.getByText('Annullando nelle ultime 24 ore la caparra non verra rimborsata automaticamente.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Conferma annullamento' }));

    await waitFor(() => expect(screen.getByText('Nessun rimborso automatico: la cancellazione e avvenuta nelle ultime 24 ore.')).toBeInTheDocument());
  });

  it('shows a readable error when the cancellation token is invalid', async () => {
    vi.mocked(getPublicCancellation).mockRejectedValue({ response: { data: { detail: 'Link annullamento non valido' } } });

    renderPage('/booking/cancel?token=bad-token');

    await screen.findByText('Link annullamento non disponibile');
    expect(screen.getByText('Link annullamento non valido')).toBeInTheDocument();
  });

  it('keeps the cancellation state visible when the refund fails after the booking is cancelled', async () => {
    vi.mocked(cancelPublicBooking).mockRejectedValue({ response: { data: { detail: 'Rimborso automatico non riuscito' } } });
    vi.mocked(getPublicCancellation)
      .mockResolvedValueOnce({ ...previewPayload })
      .mockResolvedValueOnce({
        ...previewPayload,
        booking: { ...previewPayload.booking, status: 'CANCELLED', cancelled_at: '2026-04-20T09:10:00Z' },
        cancellable: false,
        cancellation_reason: 'Prenotazione gia annullata',
        refund_status: 'FAILED',
        refund_message: 'Rimborso automatico non riuscito. Il team gestira il caso manualmente.',
        message: null,
      });

    renderPage();

    await screen.findByText('Annullamento self-service');
    fireEvent.click(screen.getByRole('button', { name: 'Conferma annullamento e rimborso' }));

    await waitFor(() => expect(screen.getByText('Rimborso automatico non riuscito')).toBeInTheDocument());
    expect(screen.getByText('Rimborso automatico non riuscito. Il team gestira il caso manualmente.')).toBeInTheDocument();
    expect(screen.getByText('Prenotazione gia annullata')).toBeInTheDocument();
  });

  it('preserves tenant context in api calls and back links', async () => {
    renderPage('/booking/cancel?token=cancel-token-1&tenant=roma-club');

    await screen.findByText('Annullamento self-service');

    expect(getPublicCancellation).toHaveBeenCalledWith('cancel-token-1', 'roma-club');
    expect(getPublicConfig).toHaveBeenCalledWith('roma-club');
    expect(screen.getByRole('link', { name: 'Torna alla prenotazione' })).toHaveAttribute('href', '/?tenant=roma-club');
    expect(screen.getByRole('link', { name: 'Mantieni la prenotazione' })).toHaveAttribute('href', '/?tenant=roma-club');

    fireEvent.click(screen.getByRole('button', { name: 'Conferma annullamento e rimborso' }));
    await waitFor(() => expect(cancelPublicBooking).toHaveBeenCalledWith('cancel-token-1', 'roma-club'));
  });
});