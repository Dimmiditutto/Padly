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
    vi.mocked(loginAdmin).mockResolvedValue({ email: 'admin@padelbooking.app', full_name: 'Admin' });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('starts with empty credentials and no prefilled defaults', () => {
    renderPage();

    expect(screen.getByLabelText('Email')).toHaveValue('');
    expect(screen.getByLabelText('Password')).toHaveValue('');
  });

  it('redirects to the dashboard when login succeeds', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText('Email'), 'admin@padelbooking.app');
    await user.type(screen.getByLabelText('Password'), 'ChangeMe123!');
    await user.click(screen.getByRole('button', { name: 'Entra nella dashboard' }));

    await screen.findByText('ADMIN DASHBOARD');
    expect(loginAdmin).toHaveBeenCalledWith('admin@padelbooking.app', 'ChangeMe123!');
  });

  it('shows the backend error detail on login failure', async () => {
    const user = userEvent.setup();
    vi.mocked(loginAdmin).mockRejectedValue({ response: { data: { detail: 'Credenziali admin non valide' } } });

    renderPage();

    await user.type(screen.getByLabelText('Email'), 'admin@padelbooking.app');
    await user.type(screen.getByLabelText('Password'), 'wrong-password');
    await user.click(screen.getByRole('button', { name: 'Entra nella dashboard' }));

    await waitFor(() => expect(screen.getByText('Credenziali admin non valide')).toBeInTheDocument());
  });

  it('shows loading state, disables the button and avoids double submit while the request is pending', async () => {
    const user = userEvent.setup();
    const pending = deferred<{ email: string; full_name: string }>();
    vi.mocked(loginAdmin).mockReturnValue(pending.promise);

    renderPage();

    await user.type(screen.getByLabelText('Email'), 'admin@padelbooking.app');
    await user.type(screen.getByLabelText('Password'), 'ChangeMe123!');
    await user.click(screen.getByRole('button', { name: 'Entra nella dashboard' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Accesso in corso…' })).toBeDisabled());
    await user.click(screen.getByRole('button', { name: 'Accesso in corso…' }));
    expect(loginAdmin).toHaveBeenCalledTimes(1);

    pending.resolve({ email: 'admin@padelbooking.app', full_name: 'Admin' });
    await screen.findByText('ADMIN DASHBOARD');
  });
});