import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminLoginPage } from './AdminLoginPage';

vi.mock('../services/adminApi', () => ({
  loginAdmin: vi.fn(),
}));

import { loginAdmin } from '../services/adminApi';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/login']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
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
    vi.mocked(loginAdmin).mockResolvedValue({ email: 'info@padelsavona.it', full_name: 'Admin' });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('starts with empty credentials and no prefilled defaults', () => {
    renderPage();

    expect(screen.getByLabelText('Email')).toHaveValue('');
    expect(screen.getByLabelText('Password')).toHaveValue('');
    expect(screen.getByRole('link', { name: 'Torna alla prenotazione' })).toHaveAttribute('href', '/');
    expect(screen.getByText('Nessun cambio password obbligatorio al primo accesso.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Password dimenticata?' })).toHaveAttribute(
      'href',
      "mailto:info@padelsavona.it?subject=Recupero%20password%20area%20admin&body=Ciao%2C%20ho%20bisogno%20di%20recuperare%20la%20password%20dell'area%20admin."
    );
  });

  it('redirects to the dashboard when login succeeds', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText('Email'), 'info@padelsavona.it');
    await user.type(screen.getByLabelText('Password'), 'P4d3ls4v0n4!');
    await user.click(screen.getByRole('button', { name: 'Entra nella dashboard' }));

    await screen.findByText('ADMIN DASHBOARD');
    expect(loginAdmin).toHaveBeenCalledWith('info@padelsavona.it', 'P4d3ls4v0n4!');
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

  it('shows loading state, disables the button and avoids double submit while the request is pending', async () => {
    const user = userEvent.setup();
    const pending = deferred<{ email: string; full_name: string }>();
    vi.mocked(loginAdmin).mockReturnValue(pending.promise);

    renderPage();

    await user.type(screen.getByLabelText('Email'), 'info@padelsavona.it');
    await user.type(screen.getByLabelText('Password'), 'P4d3ls4v0n4!');
    await user.click(screen.getByRole('button', { name: 'Entra nella dashboard' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Accesso in corso…' })).toBeDisabled());
    await user.click(screen.getByRole('button', { name: 'Accesso in corso…' }));
    expect(loginAdmin).toHaveBeenCalledTimes(1);

    pending.resolve({ email: 'info@padelsavona.it', full_name: 'Admin' });
    await screen.findByText('ADMIN DASHBOARD');
  });
});