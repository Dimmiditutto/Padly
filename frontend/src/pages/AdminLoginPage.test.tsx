import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminLoginPage } from './AdminLoginPage';

vi.mock('../services/adminApi', () => ({
  loginAdmin: vi.fn(),
  requestAdminPasswordReset: vi.fn(),
}));

import { loginAdmin, requestAdminPasswordReset } from '../services/adminApi';

const adminSession = {
  email: 'info@padelsavona.it',
  full_name: 'Admin',
  role: 'SUPERADMIN',
  club_id: 'club-default',
  club_slug: 'default-club',
  club_public_name: 'PadelBooking',
} as const;

function renderPage(path = '/admin/login') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/admin/login' element={<AdminLoginPage />} />
        <Route path='/admin' element={<div>ADMIN DASHBOARD</div>} />
      </Routes>
    </MemoryRouter>
  );
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

describe('AdminLoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(loginAdmin).mockResolvedValue({ ...adminSession });
    vi.mocked(requestAdminPasswordReset).mockResolvedValue({ message: "Se l'account esiste, ti ho inviato un link per reimpostare la password." });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('starts with empty credentials and no prefilled defaults', () => {
    renderPage();

    expect(screen.getByLabelText('Email')).toHaveValue('');
    expect(screen.getByLabelText('Password')).toHaveValue('');
    expect(screen.getByRole('link', { name: 'Torna alla prenotazione' })).toHaveAttribute('href', '/');
    expect(screen.getByText("Usa l'email admin per ricevere un link di reset.")).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Password dimenticata?' })).toBeInTheDocument();
  });

  it('requests a password reset link for the admin email', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText('Email'), '  INFO@PadelSavona.IT  ');
    await user.click(screen.getByRole('button', { name: 'Password dimenticata?' }));

    await waitFor(() => expect(requestAdminPasswordReset).toHaveBeenCalledWith('info@padelsavona.it', null));
    expect(screen.getByText("Se l'account esiste, ti ho inviato un link per reimpostare la password.")).toBeInTheDocument();
  });

  it('requires the admin email before requesting the password reset link', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: 'Password dimenticata?' }));

    await waitFor(() => expect(screen.getByText("Inserisci l'email admin per ricevere il link di reset.")).toBeInTheDocument());
    expect(requestAdminPasswordReset).not.toHaveBeenCalled();
  });

  it('redirects to the dashboard when login succeeds', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText('Email'), 'INFO@PadelSavona.IT');
    await user.type(screen.getByLabelText('Password'), 'P4d3ls4v0n4!');
    await user.click(screen.getByRole('button', { name: 'Entra nella dashboard' }));

    await screen.findByText('ADMIN DASHBOARD');
    expect(loginAdmin).toHaveBeenCalledWith('info@padelsavona.it', 'P4d3ls4v0n4!', null);
  });

  it('preserves tenant context in links, login and reset request', async () => {
    const user = userEvent.setup();
    renderPage('/admin/login?tenant=roma-club');

    expect(screen.getByRole('link', { name: 'Torna alla prenotazione' })).toHaveAttribute('href', '/?tenant=roma-club');

    await user.type(screen.getByLabelText('Email'), 'ADMIN@ROMA.EXAMPLE');
    await user.type(screen.getByLabelText('Password'), 'RomaTenant123!');
    await user.click(screen.getByRole('button', { name: 'Entra nella dashboard' }));

    await screen.findByText('ADMIN DASHBOARD');
    expect(loginAdmin).toHaveBeenCalledWith('admin@roma.example', 'RomaTenant123!', 'roma-club');

    renderPage('/admin/login?tenant=roma-club');
    await user.type(screen.getByLabelText('Email'), 'ADMIN@ROMA.EXAMPLE');
    await user.click(screen.getByRole('button', { name: 'Password dimenticata?' }));

    await waitFor(() => expect(requestAdminPasswordReset).toHaveBeenCalledWith('admin@roma.example', 'roma-club'));
  });

  it('shows the backend error detail on login failure', async () => {
    const user = userEvent.setup();
    vi.mocked(loginAdmin).mockRejectedValue({ response: { data: { detail: 'Credenziali admin non valide' } } });

    renderPage();

    await user.type(screen.getByLabelText('Email'), 'info@padelsavona.it');
    await user.type(screen.getByLabelText('Password'), 'wrong-password');
    await user.click(screen.getByRole('button', { name: 'Entra nella dashboard' }));

    await waitFor(() => expect(screen.getByText('Credenziali admin non valide')).toBeInTheDocument());
  });

  it('shows a backend unreachable message when the request fails before receiving a response', async () => {
    const user = userEvent.setup();
    vi.mocked(loginAdmin).mockRejectedValue(new Error('Network Error'));

    renderPage();

    await user.type(screen.getByLabelText('Email'), 'info@padelsavona.it');
    await user.type(screen.getByLabelText('Password'), 'P4d3ls4v0n4!');
    await user.click(screen.getByRole('button', { name: 'Entra nella dashboard' }));

    await waitFor(() => expect(screen.getByText('Backend non raggiungibile. Avvia il server e riprova.')).toBeInTheDocument());
  });

  it('shows loading state, disables the button and avoids double submit while the request is pending', async () => {
    const user = userEvent.setup();
    const pending = deferred<typeof adminSession>();
    vi.mocked(loginAdmin).mockReturnValue(pending.promise);

    renderPage();

    await user.type(screen.getByLabelText('Email'), 'info@padelsavona.it');
    await user.type(screen.getByLabelText('Password'), 'P4d3ls4v0n4!');
    await user.click(screen.getByRole('button', { name: 'Entra nella dashboard' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Accesso in corso…' })).toBeDisabled());
    await user.click(screen.getByRole('button', { name: 'Accesso in corso…' }));
    expect(loginAdmin).toHaveBeenCalledTimes(1);

    pending.resolve({ ...adminSession });
    await screen.findByText('ADMIN DASHBOARD');
  });
});