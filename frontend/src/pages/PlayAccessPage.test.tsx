import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PlayAccessPage } from './PlayAccessPage';
import type { PlayPlayerSummary, PublicConfig } from '../types';

vi.mock('../services/playApi', () => ({
  getPlaySession: vi.fn(),
  resendPlayAccessOtp: vi.fn(),
  startPlayAccessOtp: vi.fn(),
  verifyPlayAccessOtp: vi.fn(),
}));

vi.mock('../services/publicApi', () => ({
  getPublicConfig: vi.fn(),
}));

import { getPublicConfig } from '../services/publicApi';
import { getPlaySession, resendPlayAccessOtp, startPlayAccessOtp, verifyPlayAccessOtp } from '../services/playApi';

const originalLocation = window.location;

const baseConfig: PublicConfig = {
  app_name: 'PadelBooking',
  tenant_id: 'club-roma',
  tenant_slug: 'roma-club',
  public_name: 'Roma Club',
  timezone: 'Europe/Rome',
  currency: 'EUR',
  contact_email: 'desk@roma-club.example',
  support_email: 'support@roma-club.example',
  support_phone: '+39021234567',
  booking_hold_minutes: 15,
  cancellation_window_hours: 24,
  member_hourly_rate: 8,
  non_member_hourly_rate: 11,
  member_ninety_minute_rate: 12,
  non_member_ninety_minute_rate: 15,
  stripe_enabled: true,
  paypal_enabled: true,
};

const basePlayer: PlayPlayerSummary = {
  id: 'player-1',
  profile_name: 'Giulia Matchinn',
  phone: '+393334445566',
  email: 'giulia@example.com',
  email_verified_at: '2026-05-10T18:05:00Z',
  declared_level: 'INTERMEDIATE_LOW',
  privacy_accepted_at: '2026-05-10T18:00:00Z',
  created_at: '2026-05-10T18:00:00Z',
};

function renderPage(path = '/c/roma-club/play/access') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/c/:clubSlug/play/access' element={<PlayAccessPage />} />
        <Route path='/c/:clubSlug/play/access/:groupToken' element={<PlayAccessPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('PlayAccessPage', () => {
  beforeEach(() => {
    const assignMock = vi.fn();
    vi.clearAllMocks();
    vi.stubGlobal('location', { ...originalLocation, assign: assignMock });
    vi.mocked(getPublicConfig).mockResolvedValue({ ...baseConfig });
    vi.mocked(getPlaySession).mockResolvedValue({ player: null, notification_settings: null });
    vi.mocked(startPlayAccessOtp).mockResolvedValue({
      message: 'Ti abbiamo inviato un codice via email. Inseriscilo per completare l’accesso.',
      challenge_id: 'challenge-1',
      email_hint: 'gi***@example.com',
      expires_at: '2026-05-10T18:10:00Z',
      resend_available_at: '2026-05-10T18:00:00Z',
    });
    vi.mocked(verifyPlayAccessOtp).mockResolvedValue({
      message: 'Accesso community completato.',
      player: { ...basePlayer },
    });
    vi.mocked(resendPlayAccessOtp).mockResolvedValue({
      message: 'Ti abbiamo inviato un nuovo codice via email.',
      challenge_id: 'challenge-1',
      email_hint: 'gi***@example.com',
      expires_at: '2026-05-10T18:12:00Z',
      resend_available_at: '2026-05-10T18:02:00Z',
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('starts recovery OTP and redirects after verify', async () => {
    const user = userEvent.setup();

    renderPage('/c/roma-club/play/access?redirect=/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Entra o rientra nella community' });
    expect(getPlaySession).toHaveBeenCalledWith('roma-club');
    expect(getPublicConfig).toHaveBeenCalledWith('roma-club');

    await user.type(screen.getByLabelText('Email'), 'giulia@example.com');
    await user.click(screen.getByRole('button', { name: 'Invia codice OTP' }));

    await waitFor(() =>
      expect(startPlayAccessOtp).toHaveBeenCalledWith(
        {
          purpose: 'RECOVERY',
          email: 'giulia@example.com',
          declared_level: 'NO_PREFERENCE',
          privacy_accepted: false,
        },
        'roma-club'
      )
    );

    expect(await screen.findByRole('heading', { name: 'Verifica il codice OTP' })).toBeInTheDocument();

    await user.type(screen.getByLabelText('Codice OTP'), '112233');
    await user.click(screen.getByRole('button', { name: 'Verifica e accedi' }));

    await waitFor(() => expect(verifyPlayAccessOtp).toHaveBeenCalledWith({ challenge_id: 'challenge-1', otp_code: '112233' }, 'roma-club'));
    expect(window.location.assign).toHaveBeenCalledWith('/c/roma-club/play');
  });

  it('validates the direct first-access form before submitting the OTP request', async () => {
    const user = userEvent.setup();

    renderPage();

    await screen.findByRole('heading', { name: 'Entra o rientra nella community' });
    await user.click(screen.getByRole('button', { name: 'Primo accesso' }));
    await user.click(screen.getByRole('button', { name: 'Invia codice OTP' }));

    expect(await screen.findByText('Inserisci una email valida per ricevere il codice di accesso.')).toBeInTheDocument();
    expect(startPlayAccessOtp).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText('Nome profilo'), 'Giulia Matchinn');
    await user.type(screen.getByLabelText('Telefono'), '+39 333 444 5566');
    await user.type(screen.getByLabelText('Email'), 'giulia@example.com');
    await user.selectOptions(screen.getByLabelText('Livello dichiarato'), 'INTERMEDIATE_HIGH');
    await user.click(screen.getByRole('checkbox', { name: /Accetto la privacy/i }));
    await user.click(screen.getByRole('button', { name: 'Invia codice OTP' }));

    await waitFor(() =>
      expect(startPlayAccessOtp).toHaveBeenCalledWith(
        {
          purpose: 'DIRECT',
          profile_name: 'Giulia Matchinn',
          phone: '+39 333 444 5566',
          email: 'giulia@example.com',
          declared_level: 'INTERMEDIATE_HIGH',
          privacy_accepted: true,
        },
        'roma-club'
      )
    );

    expect(screen.getByText(/Ti abbiamo inviato un codice via email/i)).toBeInTheDocument();
  });

  it('collects individual data in group mode and starts the OTP flow with the shared token', async () => {
    const user = userEvent.setup();

    renderPage('/c/roma-club/play/access/group-open-day');

    await screen.findByRole('heading', { name: 'Entra dal link condiviso' });
    expect(screen.queryByRole('button', { name: 'Primo accesso' })).not.toBeInTheDocument();

    await user.type(screen.getByLabelText('Nome profilo'), 'Marco Group');
    await user.type(screen.getByLabelText('Telefono'), '+39 333 888 7777');
    await user.type(screen.getByLabelText('Email'), 'marco.group@example.com');
    await user.selectOptions(screen.getByLabelText('Livello dichiarato'), 'ADVANCED');
    await user.click(screen.getByRole('checkbox', { name: /Accetto la privacy/i }));
    await user.click(screen.getByRole('button', { name: 'Invia codice OTP' }));

    await waitFor(() =>
      expect(startPlayAccessOtp).toHaveBeenCalledWith(
        {
          purpose: 'GROUP',
          group_token: 'group-open-day',
          profile_name: 'Marco Group',
          phone: '+39 333 888 7777',
          email: 'marco.group@example.com',
          declared_level: 'ADVANCED',
          privacy_accepted: true,
        },
        'roma-club'
      )
    );

    expect(screen.getByText(/Ti abbiamo inviato un codice via email/i)).toBeInTheDocument();
  });

  it('shows the lockout message and lets the user request a new OTP', async () => {
    const user = userEvent.setup();

    vi.mocked(verifyPlayAccessOtp).mockRejectedValue({
      response: {
        data: {
          detail: 'Troppi tentativi. Richiedi un nuovo codice',
        },
      },
    });

    renderPage();

    await screen.findByRole('heading', { name: 'Entra o rientra nella community' });
    await user.type(screen.getByLabelText('Email'), 'giulia@example.com');
    await user.click(screen.getByRole('button', { name: 'Invia codice OTP' }));
    await screen.findByRole('heading', { name: 'Verifica il codice OTP' });

    const otpInput = screen.getByLabelText('Codice OTP');
    await user.type(otpInput, '112233');
    await user.click(screen.getByRole('button', { name: 'Verifica e accedi' }));

    expect(await screen.findByText('Hai esaurito i tentativi per questo codice. Richiedine uno nuovo e usa solo l’ultimo OTP ricevuto via email.')).toBeInTheDocument();
    expect(screen.getByText('Questo codice non e piu valido. Richiedine uno nuovo e inserisci solo l’ultimo OTP ricevuto via email.')).toBeInTheDocument();
    expect(otpInput).toHaveValue('');

    await user.click(screen.getByRole('button', { name: 'Invia un nuovo codice' }));

    await waitFor(() => expect(resendPlayAccessOtp).toHaveBeenCalledWith('challenge-1', 'roma-club'));
    expect(otpInput).toHaveValue('');
    expect(await screen.findByText(/nuovo codice via email/i)).toBeInTheDocument();
  });

  it('shows the explicit provider error when OTP emails cannot be delivered in this environment', async () => {
    const user = userEvent.setup();

    vi.mocked(startPlayAccessOtp).mockRejectedValue({
      response: {
        data: {
          detail: 'Provider email non configurato in questo ambiente. Configura Resend o SMTP per inviare il codice OTP.',
        },
      },
    });

    renderPage();

    await screen.findByRole('heading', { name: 'Entra o rientra nella community' });
    await user.click(screen.getByRole('button', { name: 'Primo accesso' }));
    await user.type(screen.getByLabelText('Nome profilo'), 'Giulia Matchinn');
    await user.type(screen.getByLabelText('Telefono'), '+39 333 444 5566');
    await user.type(screen.getByLabelText('Email'), 'giulia@example.com');
    await user.click(screen.getByRole('checkbox', { name: /Accetto la privacy/i }));
    await user.click(screen.getByRole('button', { name: 'Invia codice OTP' }));

    expect(await screen.findByText('Provider email non configurato in questo ambiente. Configura Resend o SMTP per inviare il codice OTP.')).toBeInTheDocument();
  });
});