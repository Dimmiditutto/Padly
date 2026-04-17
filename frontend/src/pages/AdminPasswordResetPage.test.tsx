import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminPasswordResetPage } from './AdminPasswordResetPage';

vi.mock('../services/adminApi', () => ({
  confirmAdminPasswordReset: vi.fn(),
}));

import { confirmAdminPasswordReset } from '../services/adminApi';

function renderPage(path = '/admin/reset-password?token=test-reset-token') {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/admin/reset-password' element={<AdminPasswordResetPage />} />
        <Route path='/admin/login' element={<div>ADMIN LOGIN</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('AdminPasswordResetPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(confirmAdminPasswordReset).mockResolvedValue({ message: 'Password aggiornata. Ora puoi accedere con la nuova password.' });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows an immediate error and disables submit when the token is missing', () => {
    renderPage('/admin/reset-password');

    expect(screen.getByText('Link di reset non valido o mancante.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Salva nuova password' })).toBeDisabled();
  });

  it('prevents submission when the two passwords do not match', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText('Nuova password'), 'ResetPass123!');
    await user.type(screen.getByLabelText('Conferma nuova password'), 'Diversa123!');
    await user.click(screen.getByRole('button', { name: 'Salva nuova password' }));

    await waitFor(() => expect(screen.getByText('Le password non coincidono.')).toBeInTheDocument());
    expect(confirmAdminPasswordReset).not.toHaveBeenCalled();
  });

  it('submits the new password and shows the success message', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText('Nuova password'), 'ResetPass123!');
    await user.type(screen.getByLabelText('Conferma nuova password'), 'ResetPass123!');
    await user.click(screen.getByRole('button', { name: 'Salva nuova password' }));

    await waitFor(() => expect(confirmAdminPasswordReset).toHaveBeenCalledWith('test-reset-token', 'ResetPass123!'));
    expect(screen.getByText('Password aggiornata. Ora puoi accedere con la nuova password.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Torna al login' })).toHaveAttribute('href', '/admin/login');
  });

  it('shows the backend detail when the reset token is invalid or already used', async () => {
    const user = userEvent.setup();
    vi.mocked(confirmAdminPasswordReset).mockRejectedValue({ response: { data: { detail: 'Link di reset non valido o già utilizzato' } } });
    renderPage();

    await user.type(screen.getByLabelText('Nuova password'), 'ResetPass123!');
    await user.type(screen.getByLabelText('Conferma nuova password'), 'ResetPass123!');
    await user.click(screen.getByRole('button', { name: 'Salva nuova password' }));

    await waitFor(() => expect(screen.getByText('Link di reset non valido o già utilizzato')).toBeInTheDocument());
  });
});