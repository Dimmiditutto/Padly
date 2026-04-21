import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AdminLogsPage } from './AdminLogsPage';

vi.mock('../services/adminApi', () => ({
  getAdminSession: vi.fn(),
  listAdminEvents: vi.fn(),
}));

import { getAdminSession, listAdminEvents } from '../services/adminApi';

const adminSession = {
  email: 'admin@padelbooking.app',
  full_name: 'Admin',
  role: 'SUPERADMIN',
  club_id: 'club-default',
  club_slug: 'default-club',
  club_public_name: 'PadelBooking',
} as const;

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/log']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/admin/log' element={<AdminLogsPage />} />
        <Route path='/admin/login' element={<div>LOGIN PAGE</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('AdminLogsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getAdminSession).mockResolvedValue({ ...adminSession });
    vi.mocked(listAdminEvents).mockResolvedValue([
      {
        id: 'event-1',
        event_type: 'RECURRING_SERIES_CREATED',
        actor: 'admin@padelbooking.app',
        message: 'Serie ricorrente creata: Corso serale',
        created_at: '2024-04-10T08:00:00Z',
      },
    ]);
  });

  it('renders the recent admin event list', async () => {
    renderPage();

    await screen.findByText('Traccia operativa recente');
    expect(screen.getByText('RECURRING_SERIES_CREATED')).toBeInTheDocument();
    expect(screen.getByText('Serie ricorrente creata: Corso serale')).toBeInTheDocument();
  });

  it('redirects to login when session validation returns 401', async () => {
    vi.mocked(getAdminSession).mockRejectedValue({ response: { status: 401, data: { detail: 'Unauthorized' } } });

    renderPage();

    await screen.findByText('LOGIN PAGE');
  });
});
