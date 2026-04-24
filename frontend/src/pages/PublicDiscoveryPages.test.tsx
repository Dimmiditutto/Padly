import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';

vi.mock('../pages/PublicBookingPage', () => ({
  PublicBookingPage: () => <div>PUBLIC BOOKING ROUTE</div>,
}));

vi.mock('../pages/PlayPage', () => ({
  PlayPage: () => <div>PLAY COMMUNITY ROUTE</div>,
}));

vi.mock('../services/publicApi', () => ({
  getPublicClubDetail: vi.fn(),
  listPublicClubs: vi.fn(),
  listPublicClubsNearby: vi.fn(),
}));

import { getPublicClubDetail, listPublicClubs, listPublicClubsNearby } from '../services/publicApi';

function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </MemoryRouter>
  );
}

const directoryItems = [
  {
    club_id: 'club-1',
    club_slug: 'roma-club',
    public_name: 'Roma Club',
    public_address: 'Via dei Campi 1',
    public_postal_code: '00100',
    public_city: 'Roma',
    public_province: 'RM',
    public_latitude: 41.9,
    public_longitude: 12.5,
    has_coordinates: true,
    distance_km: 1.2,
    courts_count: 3,
    contact_email: 'desk@roma-club.example',
    support_phone: '+39061234567',
    is_community_open: true,
  },
  {
    club_id: 'club-2',
    club_slug: 'savona-club',
    public_name: 'Savona Club',
    public_address: 'Piazza Sport 2',
    public_postal_code: '17100',
    public_city: 'Savona',
    public_province: 'SV',
    public_latitude: null,
    public_longitude: null,
    has_coordinates: false,
    distance_km: null,
    courts_count: 2,
    contact_email: 'desk@savona-club.example',
    support_phone: '+39019999999',
    is_community_open: false,
  },
];

describe('Public discovery routes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listPublicClubs).mockResolvedValue({ query: null, items: directoryItems });
    vi.mocked(listPublicClubsNearby).mockResolvedValue({ query: null, items: [directoryItems[0]] });
    vi.mocked(getPublicClubDetail).mockResolvedValue({
      club: directoryItems[0],
      timezone: 'Europe/Rome',
      support_email: 'desk@roma-club.example',
      support_phone: '+39061234567',
      public_match_window_days: 7,
      open_matches: [
        {
          id: 'match-1',
          court_name: 'Campo 1',
          court_badge_label: 'Indoor',
          start_at: '2026-05-10T18:00:00Z',
          end_at: '2026-05-10T19:30:00Z',
          level_requested: 'INTERMEDIATE_HIGH',
          participant_count: 3,
          available_spots: 1,
          occupancy_label: '3/4',
          missing_players_message: 'Manca 1 giocatore',
        },
      ],
    });
  });

  afterEach(() => {
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: undefined,
    });
  });

  it('keeps existing public booking and private play routes intact in App', async () => {
    renderApp('/');
    expect(await screen.findByText('PUBLIC BOOKING ROUTE')).toBeInTheDocument();

    renderApp('/c/roma-club/play');
    expect(await screen.findByText('PLAY COMMUNITY ROUTE')).toBeInTheDocument();
  });

  it('loads /clubs and supports manual search by city CAP or province', async () => {
    const user = userEvent.setup();
    vi.mocked(listPublicClubs)
      .mockResolvedValueOnce({ query: null, items: directoryItems })
      .mockResolvedValueOnce({ query: 'savona', items: [directoryItems[1]] });

    renderApp('/clubs');

    expect(await screen.findByText('Roma Club')).toBeInTheDocument();
    await user.clear(screen.getByLabelText('Citta, CAP o provincia'));
    await user.type(screen.getByLabelText('Citta, CAP o provincia'), 'savona');
    await user.click(screen.getByRole('button', { name: 'Cerca club' }));

    await waitFor(() => expect(listPublicClubs).toHaveBeenLastCalledWith('savona'));
    expect(await screen.findByText('Savona Club')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Apri pagina club' })).toHaveAttribute('href', '/c/savona-club');
  });

  it('shows fallback feedback when geolocation is denied on /clubs/nearby', async () => {
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: {
        getCurrentPosition: (_success: PositionCallback, error: PositionErrorCallback) => error({ code: 1 } as GeolocationPositionError),
      },
    });

    renderApp('/clubs/nearby');

    expect(await screen.findByText('Permesso geolocalizzazione negato. Usa la ricerca manuale per citta, CAP o provincia.')).toBeInTheDocument();
    await waitFor(() => expect(listPublicClubs).toHaveBeenCalled());
    expect(listPublicClubsNearby).not.toHaveBeenCalled();
  });

  it('renders /c/:clubSlug with public open matches and level filter without player details', async () => {
    const user = userEvent.setup();
    vi.mocked(getPublicClubDetail)
      .mockResolvedValueOnce({
        club: directoryItems[0],
        timezone: 'Europe/Rome',
        support_email: 'desk@roma-club.example',
        support_phone: '+39061234567',
        public_match_window_days: 7,
        open_matches: [
          {
            id: 'match-1',
            court_name: 'Campo 1',
            court_badge_label: 'Indoor',
            start_at: '2026-05-10T18:00:00Z',
            end_at: '2026-05-10T19:30:00Z',
            level_requested: 'INTERMEDIATE_HIGH',
            participant_count: 3,
            available_spots: 1,
            occupancy_label: '3/4',
            missing_players_message: 'Manca 1 giocatore',
          },
        ],
      })
      .mockResolvedValueOnce({
        club: directoryItems[0],
        timezone: 'Europe/Rome',
        support_email: 'desk@roma-club.example',
        support_phone: '+39061234567',
        public_match_window_days: 7,
        open_matches: [
          {
            id: 'match-2',
            court_name: 'Campo 1',
            court_badge_label: 'Indoor',
            start_at: '2026-05-11T18:00:00Z',
            end_at: '2026-05-11T19:30:00Z',
            level_requested: 'ADVANCED',
            participant_count: 2,
            available_spots: 2,
            occupancy_label: '2/4',
            missing_players_message: 'Mancano 2 giocatori',
          },
        ],
      });

    renderApp('/c/roma-club');

    expect(await screen.findByRole('heading', { name: 'Roma Club' })).toBeInTheDocument();
    expect(screen.getByText('Manca 1 giocatore')).toBeInTheDocument();
    expect(screen.queryByText('Mario Rossi')).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Livello'), 'ADVANCED');

    await waitFor(() => expect(getPublicClubDetail).toHaveBeenLastCalledWith('roma-club', 'ADVANCED'));
    expect(await screen.findByText('Mancano 2 giocatori')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Entra nella community' })).toHaveAttribute('href', '/c/roma-club/play');
  });
});