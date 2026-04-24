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
  tenant_id: 'club-default',
  tenant_slug: 'default-club',
  public_name: 'PadelBooking',
  timezone: 'Europe/Rome',
  currency: 'EUR',
  contact_email: 'help@padelbooking.app',
  support_email: 'help@padelbooking.app',
  support_phone: '+390101010101',
  booking_hold_minutes: 15,
  cancellation_window_hours: 24,
  member_hourly_rate: 7,
  non_member_hourly_rate: 9,
  member_ninety_minute_rate: 10,
  non_member_ninety_minute_rate: 13,
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

function renderPage(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <PublicBookingPage />
    </MemoryRouter>
  );
}

function buildHalfHourSlots(count: number) {
  return Array.from({ length: count }, (_, index) => {
    const startTotalMinutes = (7 * 60) + (index * 30);
    const endTotalMinutes = startTotalMinutes + 60;
    const startHours = String(Math.floor(startTotalMinutes / 60)).padStart(2, '0');
    const startMinutes = String(startTotalMinutes % 60).padStart(2, '0');
    const endHours = String(Math.floor(endTotalMinutes / 60)).padStart(2, '0');
    const endMinutes = String(endTotalMinutes % 60).padStart(2, '0');
    const displayStart = `${startHours}:${startMinutes}`;
    const displayEnd = `${endHours}:${endMinutes}`;

    return {
      slot_id: `2026-05-10T${displayStart}:00+00:00`,
      start_time: displayStart,
      end_time: displayEnd,
      display_start_time: displayStart,
      display_end_time: displayEnd,
      available: true,
      reason: null,
    };
  });
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
    expect(screen.getByRole('img', { name: 'Logo BG' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Accesso admin' })).toHaveAttribute('href', '/admin/login');
    expect(screen.getByText('Campo aperto da Lunedì a Domenica dalle 7 alle 24. La disponibilità cambia in tempo reale.')).toBeInTheDocument();
    expect(screen.getByText("Self-service fino all'inizio della prenotazione")).toBeInTheDocument();
    expect(screen.getByText('Rimborso automatico solo se annulli prima di 24 ore. Nelle ultime 24 ore la caparra non e rimborsabile.')).toBeInTheDocument();
    expect(screen.getByText('Tempo massimo per completare il checkout.')).toBeInTheDocument();
    expect(screen.getByText('Tariffe informative per giocatore')).toBeInTheDocument();
    expect(screen.getByText(/Tesserati: .*ora per giocatore/)).toBeInTheDocument();
    expect(screen.getByText(/Non tesserati: .*ora per giocatore/)).toBeInTheDocument();
    expect(screen.getByText(/90 minuti: .*giocatore tesserato/)).toBeInTheDocument();
    expect(screen.getByText(/90 minuti: .*giocatore non tesserato/)).toBeInTheDocument();
    expect(screen.getByText('Tariffe informative: non sostituiscono la caparra online.')).toBeInTheDocument();
    expect(screen.getByText('Giorno')).toBeInTheDocument();
    expect(screen.getByText('Tenant attivo')).toBeInTheDocument();
    expect(screen.getByText('Slug: default-club • Fuso: Europe/Rome')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'help@padelbooking.app' })).toHaveAttribute('href', 'mailto:help@padelbooking.app');
    expect(screen.getByRole('link', { name: '+390101010101' })).toHaveAttribute('href', 'tel:+390101010101');

    expect(getPublicConfig).toHaveBeenCalledWith(null);
    expect(getAvailability).toHaveBeenCalledWith(expect.any(String), 90, null);
    expect(screen.getByRole('button', { name: 'Stripe' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'PayPal' })).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Data'), { target: { value: '2026-05-10' } });
    await waitFor(() => expect(getAvailability).toHaveBeenLastCalledWith('2026-05-10', 90, null));

    await fillBookingForm();
    fireEvent.click(screen.getByRole('button', { name: '18:00' }));
    expect(screen.getByText('10/05/2026')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Continua al pagamento della caparra' }));

    await waitFor(() => expect(createPublicBooking).toHaveBeenCalledWith(expect.objectContaining({
      start_time: '18:00',
      slot_id: '2026-05-10T18:00:00+00:00',
      duration_minutes: 90,
      payment_provider: 'STRIPE',
    }), null));
    expect(createPublicCheckout).toHaveBeenCalledWith(createdBooking.id, null);
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

    await waitFor(() => expect(createPublicBooking).toHaveBeenCalledWith(expect.objectContaining({ payment_provider: 'PAYPAL', slot_id: '2026-05-10T18:00:00+00:00' }), null));
    expect(window.location.assign).toHaveBeenCalledWith('/checkout/paypal');
  });

  it('renders tenant-aware branding and preserves tenant query for admin access', async () => {
    vi.mocked(getPublicConfig).mockResolvedValue({
      ...baseConfig,
      tenant_id: 'club-roma',
      tenant_slug: 'roma-club',
      public_name: 'Roma Elite Club',
      contact_email: 'desk@roma-club.example',
      support_email: 'support@roma-club.example',
      support_phone: '+39021234567',
      member_hourly_rate: 8,
      non_member_hourly_rate: 11,
      member_ninety_minute_rate: 12,
      non_member_ninety_minute_rate: 15,
    });

    renderPage('/?tenant=roma-club');

    await screen.findByText('Roma Elite Club: prenota il tuo match in pochi minuti');
    expect(getPublicConfig).toHaveBeenCalledWith('roma-club');
    expect(getAvailability).toHaveBeenCalledWith(expect.any(String), 90, 'roma-club');
    expect(screen.getByRole('link', { name: 'desk@roma-club.example' })).toHaveAttribute('href', 'mailto:desk@roma-club.example');
    expect(screen.getByRole('link', { name: '+39021234567' })).toHaveAttribute('href', 'tel:+39021234567');
    expect(screen.getByText(/Tesserati: .*ora per giocatore/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Accesso admin' })).toHaveAttribute('href', '/admin/login?tenant=roma-club');
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

  it('starts each court card collapsed with 8 slots and expands it with the arrow control', async () => {
    vi.mocked(getAvailability).mockResolvedValue({
      date: '2026-05-10',
      duration_minutes: 60,
      deposit_amount: 20,
      slots: [],
      courts: [
        {
          court_id: 'court-1',
          court_name: 'Campo 1',
          badge_label: 'Indoor',
          slots: buildHalfHourSlots(10),
        },
      ],
    });

    renderPage();

    const expandButton = await screen.findByRole('button', { name: 'Espandi orari di Campo 1' });
    expect(expandButton).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByText('Indoor')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '07:00' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '10:30' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '11:00' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '11:30' })).not.toBeInTheDocument();

    fireEvent.click(expandButton);

    await screen.findByRole('button', { name: 'Comprimi orari di Campo 1' });
    expect(screen.getByRole('button', { name: '11:00' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '11:30' })).toBeInTheDocument();
  });

  it('shows a see-all button instead of the unavailable-state message when more slots are hidden', async () => {
    vi.mocked(getAvailability).mockResolvedValue({
      date: '2026-05-10',
      duration_minutes: 60,
      deposit_amount: 20,
      slots: [],
      courts: [
        {
          court_id: 'court-1',
          court_name: 'Campo 1',
          slots: [
            ...buildHalfHourSlots(8).map((slot) => ({ ...slot, available: false, reason: 'Occupato' })),
            ...buildHalfHourSlots(2).map((slot, index) => ({
              ...slot,
              slot_id: `2026-05-10T1${index + 1}:00:00+00:00`,
              start_time: index === 0 ? '11:00' : '11:30',
              end_time: index === 0 ? '12:00' : '12:30',
              display_start_time: index === 0 ? '11:00' : '11:30',
              display_end_time: index === 0 ? '12:00' : '12:30',
              available: true,
              reason: null,
            })),
          ],
        },
      ],
    });

    renderPage();

    const seeAllButton = await screen.findByRole('button', { name: 'Vedi tutti gli orari' });
    expect(screen.queryByText('Fasce piene per questa selezione')).not.toBeInTheDocument();

    fireEvent.click(seeAllButton);

    await screen.findByRole('button', { name: '11:00' });
    expect(screen.getByRole('button', { name: '11:30' })).toBeInTheDocument();
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
    expect(getAvailability).toHaveBeenLastCalledWith('2026-05-11', 90, null);
  });
});