import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PaymentStatusPage } from './PaymentStatusPage';

vi.mock('../services/publicApi', () => ({
  getPublicBookingStatus: vi.fn(),
}));

import { getPublicBookingStatus } from '../services/publicApi';

const bookingSummary = {
  id: 'booking-1',
  public_reference: 'PB-REF-123',
  start_at: '2025-01-10T18:00:00Z',
  end_at: '2025-01-10T19:30:00Z',
  duration_minutes: 90,
  booking_date_local: '2025-01-10',
  status: 'CONFIRMED',
  deposit_amount: 20,
  payment_provider: 'STRIPE',
  payment_status: 'PAID',
  created_at: '2025-01-08T10:00:00Z',
  cancelled_at: null,
  completed_at: null,
  no_show_at: null,
  balance_paid_at: null,
} as const;

function renderStatusPage(path: string, variant: 'success' | 'cancelled' = 'success') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <PaymentStatusPage variant={variant} />
    </MemoryRouter>
  );
}

describe('PaymentStatusPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getPublicBookingStatus).mockResolvedValue({
      booking: { ...bookingSummary },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('keeps the success message when the booking is confirmed', async () => {
    renderStatusPage('/booking/success?booking=PB-REF-123');

    await waitFor(() => expect(screen.getByText('Pagamento ricevuto')).toBeInTheDocument());
    expect(screen.queryByText('Pagamento non confermato')).not.toBeInTheDocument();
  });

  it('shows a warning instead of a success message when the booking expires after checkout', async () => {
    vi.mocked(getPublicBookingStatus).mockResolvedValue({
      booking: { ...bookingSummary, status: 'EXPIRED', payment_status: 'EXPIRED' },
    });

    renderStatusPage('/booking/success?booking=PB-REF-123');

    await waitFor(() => expect(screen.getByText('Pagamento non confermato')).toBeInTheDocument());
    expect(screen.queryByText('Pagamento ricevuto')).not.toBeInTheDocument();
  });

  it('shows a verification error instead of a success message when status lookup fails', async () => {
    vi.mocked(getPublicBookingStatus).mockRejectedValue(new Error('network error'));

    renderStatusPage('/booking/success?booking=PB-REF-123');

    await waitFor(() => expect(screen.getByText('Verifica pagamento non completata')).toBeInTheDocument());
    expect(screen.queryByText('Pagamento ricevuto')).not.toBeInTheDocument();
  });

  it('stops polling after a terminal confirmed status', async () => {
    const clearIntervalSpy = vi.spyOn(window, 'clearInterval');

    renderStatusPage('/booking/success?booking=PB-REF-123');

    await waitFor(() => expect(screen.getByText('Pagamento ricevuto')).toBeInTheDocument());
    await waitFor(() => expect(clearIntervalSpy).toHaveBeenCalled());
  });

  it('shows the confirmed outcome on the cancelled page when the booking is already paid', async () => {
    renderStatusPage('/booking/cancelled?booking=PB-REF-123', 'cancelled');

    await waitFor(() => expect(screen.getByText('Pagamento già confermato')).toBeInTheDocument());
    expect(screen.queryByText('Pagamento annullato')).not.toBeInTheDocument();
  });

  it('shows the expired outcome on the cancelled page when the booking has already expired', async () => {
    vi.mocked(getPublicBookingStatus).mockResolvedValue({
      booking: { ...bookingSummary, status: 'EXPIRED', payment_status: 'EXPIRED' },
    });

    renderStatusPage('/booking/cancelled?booking=PB-REF-123', 'cancelled');

    await waitFor(() => expect(screen.getByText('Prenotazione scaduta')).toBeInTheDocument());
    expect(screen.queryByText('Pagamento annullato')).not.toBeInTheDocument();
  });

  it('shows the self-service cancellation CTA when a cancel token is available', async () => {
    renderStatusPage('/booking/success?booking=PB-REF-123&cancelToken=cancel-token-123');

    await waitFor(() => expect(screen.getByRole('link', { name: 'Apri annullamento self-service' })).toBeInTheDocument());
    expect(screen.getByRole('link', { name: 'Apri annullamento self-service' })).toHaveAttribute('href', '/booking/cancel?token=cancel-token-123');
  });
});