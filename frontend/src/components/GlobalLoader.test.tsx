import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, Link } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GlobalLoader } from './GlobalLoader';

const apiActivityHarness = vi.hoisted(() => {
  let pending = false;
  const listeners = new Set<(value: boolean) => void>();

  return {
    getHasPendingApiRequests: vi.fn(() => pending),
    subscribeToApiActivity: vi.fn((listener: (value: boolean) => void) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    }),
    emit(value: boolean) {
      pending = value;
      listeners.forEach((listener) => listener(value));
    },
    reset() {
      pending = false;
      listeners.clear();
    },
  };
});

vi.mock('../services/api', () => ({
  getHasPendingApiRequests: apiActivityHarness.getHasPendingApiRequests,
  subscribeToApiActivity: apiActivityHarness.subscribeToApiActivity,
}));

function renderLoader() {
  return render(
    <MemoryRouter initialEntries={['/pagina-uno']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <GlobalLoader />
      <Routes>
        <Route path='/pagina-uno' element={<Link to='/pagina-due'>Vai alla pagina due</Link>} />
        <Route path='/pagina-due' element={<div>Pagina due</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function getLoaderElement() {
  return screen.getByAltText('Caricamento Matchinn').parentElement as HTMLElement;
}

describe('GlobalLoader', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    apiActivityHarness.reset();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it('stays hidden for API activity that does not correspond to a page change', () => {
    renderLoader();

    expect(getLoaderElement()).toHaveClass('loader-hidden');

    act(() => {
      apiActivityHarness.emit(true);
    });

    expect(getLoaderElement()).toHaveClass('loader-hidden');
  });

  it('shows only on route changes and hides after the transition settles when no requests are pending', async () => {
    renderLoader();

    act(() => {
      fireEvent.click(screen.getByRole('link', { name: 'Vai alla pagina due' }));
    });

    expect(screen.getByText('Pagina due')).toBeInTheDocument();
    expect(getLoaderElement()).not.toHaveClass('loader-hidden');

    act(() => {
      vi.advanceTimersByTime(450);
    });

    expect(getLoaderElement()).toHaveClass('loader-hidden');
  });

  it('keeps the loader visible during requests triggered by the new page and hides it afterwards', async () => {
    renderLoader();

    act(() => {
      fireEvent.click(screen.getByRole('link', { name: 'Vai alla pagina due' }));
    });

    expect(screen.getByText('Pagina due')).toBeInTheDocument();
    expect(getLoaderElement()).not.toHaveClass('loader-hidden');

    act(() => {
      apiActivityHarness.emit(true);
      vi.advanceTimersByTime(2000);
    });

    expect(getLoaderElement()).not.toHaveClass('loader-hidden');

    act(() => {
      apiActivityHarness.emit(false);
      vi.advanceTimersByTime(300);
    });

    expect(getLoaderElement()).toHaveClass('loader-hidden');
  });
});