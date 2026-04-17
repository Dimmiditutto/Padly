import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PublicBookingPage } from './PublicBookingPage';

vi.mock('../services/publicApi', () => ({
  createPublicBooking: vi.fn(),
  createPublicCheckout: vi.fn(),
  getAvailability: vi.fn(),
  getPublicConfig: vi.fn(),
}));

import { createPublicBooking, createPublicCheckout, getAvailability, getPublicConfig } from '../services/publicApi';

const originalLocation = window.location;

const baseConfig = {
  app_name: 'PadelBooking',
  timezone: 'Europe/Rome',
  currency: 'EUR',
  booking_hold_minutes: 15,
  cancellation_window_hours: 24,
  stripe_enabled: true,
  paypal_enabled: true,
} as const;

const availabilityResponse = {
  date: '2026-05-10',
  duration_minutes: 90,
  deposit_amount: 20,
  slots: [
    { slot_id: '2026-05-10T18:00:00+00:00', start_time: '18:00', end_time: '19:30', display_start_time: '18:00', display_end_time: '19:30', available: true, reason: null },
    { slot_id: '2026-05-10T18:30:00+00:00', start_time: '18:30', end_time: '20:00', display_start_time: '18:30', display_end_time: '20:00', available: false, reason: 'Lo slot non è più disponibile' },
  ],
};

const createdBooking = {
  id: 'booking-1',
  public_reference: 'PB-REF-001',
  start_at: '2026-05-10T18:00:00Z',
  end_at: '2026-05-10T19:30:00Z',
  duration_minutes: 90,
  booking_date_local: '2026-05-10',
  status: 'PENDING_PAYMENT',
  deposit_amount: 20,
  payment_provider: 'STRIPE',
  payment_status: 'UNPAID',
  created_at: '2026-05-01T10:00:00Z',
  cancelled_at: null,
  completed_at: null,
  no_show_at: null,
  balance_paid_at: null,
} as const;

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <PublicBookingPage />
    </MemoryRouter>
  );
}

async function fillBookingForm() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText('Nome'), 'Luca');
  await user.type(screen.getByLabelText('Cognome'), 'Bianchi');
  await user.type(screen.getByLabelText('Telefono'), '3331112222');
  await user.type(screen.getByLabelText('Email'), 'luca@example.com');
  await user.click(screen.getByLabelText('Accetto il trattamento dei dati per la gestione della prenotazione.'));
}

describe('PublicBookingPage', () => {
  beforeEach(() => {
    const assignMock = vi.fn();
    vi.clearAllMocks();
    vi.stubGlobal('location', { ...originalLocation, assign: assignMock });
    vi.mocked(getPublicConfig).mockResolvedValue({ ...baseConfig });
    vi.mocked(getAvailability).mockResolvedValue({ ...availabilityResponse });
    vi.mocked(createPublicBooking).mockResolvedValue({
      booking: { ...createdBooking },
      checkout_ready: true,
      next_action_url: null,
    });
    vi.mocked(createPublicCheckout).mockResolvedValue({
      booking_id: createdBooking.id,
      public_reference: createdBooking.public_reference,
      provider: 'STRIPE',
      checkout_url: '/checkout/mock',
      payment_status: 'INITIATED',
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('loads public config and availability, then completes checkout with Stripe when it is the only provider', async () => {
    vi.mocked(getPublicConfig).mockResolvedValue({ ...baseConfig, paypal_enabled: false });

    renderPage();

    await screen.findByText('15 minuti');
    await screen.findByRole('button', { name: '18:00' });
    expect(screen.getByRole('img', { name: 'Logo BR' })).toBeInTheDocument();
    expect(screen.getByText('Campo aperto da Lunedì a Domenica dalle 7 alle 24. La disponibilità cambia in tempo reale.')).toBeInTheDocument();
    expect(screen.getByText("Self-service fino all'inizio della prenotazione")).toBeInTheDocument();
    expect(screen.getByText('Rimborso automatico solo se annulli prima di 24 ore. Nelle ultime 24 ore la caparra non e rimborsabile.')).toBeInTheDocument();
    expect(screen.getByText('Tempo massimo per completare il checkout.')).toBeInTheDocument();
    expect(screen.getByText('Tariffe informative per giocatore')).toBeInTheDocument();
    expect(screen.getByText('Tariffe informative: non sostituiscono la caparra online.')).toBeInTheDocument();
    expect(screen.getByText('Giorno')).toBeInTheDocument();

    expect(getPublicConfig).toHaveBeenCalledTimes(1);
    expect(getAvailability).toHaveBeenCalledWith(expect.any(String), 90);
    expect(screen.getByRole('button', { name: 'Stripe' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'PayPal' })).not.toBeInTheDocument();

    await fillBookingForm();
    fireEvent.click(screen.getByRole('button', { name: '18:00' }));
    fireEvent.click(screen.getByRole('button', { name: 'Continua al pagamento della caparra' }));

    await waitFor(() => expect(createPublicBooking).toHaveBeenCalledWith(expect.objectContaining({
      start_time: '18:00',
      slot_id: '2026-05-10T18:00:00+00:00',
      duration_minutes: 90,
      payment_provider: 'STRIPE',
    })));
    expect(createPublicCheckout).toHaveBeenCalledWith(createdBooking.id);
    expect(window.location.assign).toHaveBeenCalledWith('/checkout/mock');
  });

  it('falls back to PayPal when Stripe is not available and uses that provider for booking creation', async () => {
    vi.mocked(getPublicConfig).mockResolvedValue({ ...baseConfig, stripe_enabled: false, paypal_enabled: true });
    vi.mocked(createPublicCheckout).mockResolvedValue({
      booking_id: createdBooking.id,
      public_reference: createdBooking.public_reference,
      provider: 'PAYPAL',
      checkout_url: '/checkout/paypal',
      payment_status: 'INITIATED',
    });

    renderPage();

    await screen.findByRole('button', { name: 'PayPal' });
    expect(screen.queryByRole('button', { name: 'Stripe' })).not.toBeInTheDocument();

    await fillBookingForm();
    fireEvent.click(screen.getByRole('button', { name: '18:00' }));
    fireEvent.click(screen.getByRole('button', { name: 'Continua al pagamento della caparra' }));

    await waitFor(() => expect(createPublicBooking).toHaveBeenCalledWith(expect.objectContaining({ payment_provider: 'PAYPAL', slot_id: '2026-05-10T18:00:00+00:00' })));
    expect(window.location.assign).toHaveBeenCalledWith('/checkout/paypal');
  });

  it('shows only slots within the 7:00–24:00 opening window', async () => {
    vi.mocked(getAvailability).mockResolvedValue({
      date: '2026-10-25',
      duration_minutes: 60,
      deposit_amount: 20,
      slots: [
        { slot_id: '2026-10-25T00:00:00+00:00', start_time: '02:00', end_time: '02:00', display_start_time: '02:00 CEST', display_end_time: '02:00 CET', available: true, reason: null },
        { slot_id: '2026-10-25T05:30:00+00:00', start_time: '06:30', end_time: '07:30', display_start_time: '06:30', display_end_time: '07:30', available: true, reason: null },
        { slot_id: '2026-10-25T06:00:00+00:00', start_time: '07:00', end_time: '08:00', display_start_time: '07:00', display_end_time: '08:00', available: true, reason: null },
        { slot_id: '2026-10-25T22:00:00+00:00', start_time: '23:00', end_time: '00:00', display_start_time: '23:00', display_end_time: '00:00', available: true, reason: null },
        { slot_id: '2026-10-25T22:30:00+00:00', start_time: '23:30', end_time: '00:30', display_start_time: '23:30', display_end_time: '00:30', available: true, reason: null },
      ],
    });

    renderPage();

    await screen.findByRole('button', { name: '07:00' });
    await screen.findByRole('button', { name: '23:00' });
    expect(screen.queryByRole('button', { name: '02:00 CEST' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '06:30' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '23:30' })).not.toBeInTheDocument();
  });

  it('highlights all half-hour tabs covered by the selected booking duration', async () => {
    vi.mocked(getAvailability).mockResolvedValue({
      date: '2026-05-10',
      duration_minutes: 90,
      deposit_amount: 20,
      slots: [
        { slot_id: '2026-05-10T08:00:00+00:00', start_time: '08:00', end_time: '09:30', display_start_time: '08:00', display_end_time: '09:30', available: true, reason: null },
        { slot_id: '2026-05-10T08:30:00+00:00', start_time: '08:30', end_time: '10:00', display_start_time: '08:30', display_end_time: '10:00', available: true, reason: null },
        { slot_id: '2026-05-10T09:00:00+00:00', start_time: '09:00', end_time: '10:30', display_start_time: '09:00', display_end_time: '10:30', available: true, reason: null },
        { slot_id: '2026-05-10T09:30:00+00:00', start_time: '09:30', end_time: '11:00', display_start_time: '09:30', display_end_time: '11:00', available: true, reason: null },
      ],
    });

    renderPage();

    const firstSlot = await screen.findByRole('button', { name: '08:00' });
    const secondSlot = screen.getByRole('button', { name: '08:30' });
    const thirdSlot = screen.getByRole('button', { name: '09:00' });
    const fourthSlot = screen.getByRole('button', { name: '09:30' });

    fireEvent.click(firstSlot);

    expect(firstSlot).toHaveClass('bg-cyan-500');
    expect(secondSlot).toHaveClass('bg-cyan-100');
    expect(thirdSlot).toHaveClass('bg-cyan-100');
    expect(fourthSlot).not.toHaveClass('bg-cyan-100');
  });

  it('shows a clear validation message when the user submits without selecting a slot', async () => {
    renderPage();

    await screen.findByText('15 minuti');
    await fillBookingForm();
    fireEvent.click(screen.getByRole('button', { name: 'Continua al pagamento della caparra' }));

    await waitFor(() => expect(screen.getByText('Seleziona prima un orario disponibile.')).toBeInTheDocument());
    expect(createPublicBooking).not.toHaveBeenCalled();
  });

  it('surfaces backend detail messages when booking creation fails', async () => {
    vi.mocked(createPublicBooking).mockRejectedValue({ response: { data: { detail: 'Lo slot non è più disponibile' } } });

    renderPage();

    await screen.findByRole('button', { name: '18:00' });
    await fillBookingForm();
    fireEvent.click(screen.getByRole('button', { name: '18:00' }));
    fireEvent.click(screen.getByRole('button', { name: 'Continua al pagamento della caparra' }));

    await waitFor(() => expect(screen.getByText('Lo slot non è più disponibile')).toBeInTheDocument());
    expect(createPublicCheckout).not.toHaveBeenCalled();
  });

  it('shows the unavailable payments state and keeps the checkout CTA disabled when no provider is active', async () => {
    vi.mocked(getPublicConfig).mockResolvedValue({ ...baseConfig, stripe_enabled: false, paypal_enabled: false });

    renderPage();

    await screen.findByText('Il pagamento online non è disponibile in questo momento. Contatta il campo prima di completare la prenotazione.');
    expect(screen.getByRole('button', { name: 'Continua al pagamento della caparra' })).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Stripe' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'PayPal' })).not.toBeInTheDocument();
  });

  it('blocks form submission even when triggered programmatically with no active payment provider', async () => {
    const unavailablePaymentMessage = 'Il pagamento online non è disponibile in questo momento. Contatta il campo prima di completare la prenotazione.';
    vi.mocked(getPublicConfig).mockResolvedValue({ ...baseConfig, stripe_enabled: false, paypal_enabled: false });

    renderPage();

    await screen.findByText('15 minuti');
    await fillBookingForm();
    fireEvent.click(screen.getByRole('button', { name: '18:00' }));

    const submitButton = screen.getByRole('button', { name: 'Continua al pagamento della caparra' });
    const form = submitButton.closest('form');
    if (!form) {
      throw new Error('Form prenotazione non trovata');
    }
    fireEvent.submit(form);

    await waitFor(() => expect(screen.getAllByText(unavailablePaymentMessage).length).toBeGreaterThan(0));
    expect(createPublicBooking).not.toHaveBeenCalled();
  });

  it('shows the weekday label under the selected booking date', async () => {
    renderPage();

    await screen.findByRole('button', { name: '18:00' });
    fireEvent.change(screen.getByLabelText('Data'), { target: { value: '2026-05-11' } });

    await screen.findByText('Lunedì');
    expect(getAvailability).toHaveBeenLastCalledWith('2026-05-11', 90);
  });
});