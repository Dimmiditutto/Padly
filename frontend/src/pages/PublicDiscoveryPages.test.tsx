import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import type { PublicClubDetailResponse, PublicClubSummary, PublicClubWatchSummary, PublicDiscoveryMeResponse, PublicDiscoveryNotificationSummary, PublicDiscoverySession } from '../types';

vi.mock('../pages/PublicBookingPage', () => ({
  PublicBookingPage: () => <div>PUBLIC BOOKING ROUTE</div>,
}));

vi.mock('../pages/MatchinnHomePage', () => ({
  MatchinnHomePage: () => <div>MATCHINN HOME ROUTE</div>,
}));

vi.mock('../pages/PlayPage', () => ({
  PlayPage: () => <div>PLAY COMMUNITY ROUTE</div>,
}));

vi.mock('../services/publicApi', () => ({
  createPublicClubContactRequest: vi.fn(),
  followPublicClub: vi.fn(),
  getPublicClubDetail: vi.fn(),
  getPublicDiscoveryMe: vi.fn(),
  identifyPublicDiscovery: vi.fn(),
  listPublicClubs: vi.fn(),
  listPublicClubsNearby: vi.fn(),
  listPublicWatchlist: vi.fn(),
  markPublicDiscoveryNotificationRead: vi.fn(),
  unfollowPublicClub: vi.fn(),
  updatePublicDiscoveryPreferences: vi.fn(),
}));

import {
  createPublicClubContactRequest,
  followPublicClub,
  getPublicClubDetail,
  getPublicDiscoveryMe,
  identifyPublicDiscovery,
  listPublicClubs,
  listPublicClubsNearby,
  listPublicWatchlist,
  markPublicDiscoveryNotificationRead,
} from '../services/publicApi';

function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </MemoryRouter>
  );
}

const directoryItems: PublicClubSummary[] = [
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
    public_activity_score: 5,
    recent_open_matches_count: 2,
    public_activity_label: 'Buona disponibilita recente',
    open_matches_three_of_four_count: 1,
    open_matches_two_of_four_count: 1,
    open_matches_one_of_four_count: 0,
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
    public_activity_score: 0,
    recent_open_matches_count: 0,
    public_activity_label: 'Nessuna disponibilita recente',
    open_matches_three_of_four_count: 0,
    open_matches_two_of_four_count: 0,
    open_matches_one_of_four_count: 0,
  },
];

const emptyDiscoveryMe: PublicDiscoveryMeResponse = {
  subscriber: null,
  recent_notifications: [],
  unread_notifications_count: 0,
};

const baseClubDetail: PublicClubDetailResponse = {
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
};

const discoverySubscriber: PublicDiscoverySession = {
  subscriber_id: 'subscriber-1',
  preferred_level: 'INTERMEDIATE_HIGH',
  preferred_time_slots: ['morning', 'afternoon', 'evening'],
  latitude: 44.30941,
  longitude: 8.47715,
  has_coordinates: true,
  nearby_radius_km: 25,
  nearby_digest_enabled: true,
  last_identified_at: '2026-05-01T09:00:00Z',
  created_at: '2026-05-01T09:00:00Z',
  updated_at: '2026-05-01T09:00:00Z',
};

const discoveryNotification: PublicDiscoveryNotificationSummary = {
  id: 'notification-1',
  kind: 'WATCHLIST_MATCH_TWO_OF_FOUR',
  channel: 'IN_APP',
  status: 'SENT',
  title: 'Alert 2/4 Roma Club',
  message: 'Una partita del club Roma Club e arrivata a 2/4.',
  payload: null,
  sent_at: '2026-05-01T10:00:00Z',
  read_at: null,
  created_at: '2026-05-01T10:00:00Z',
};

const discoveryNotificationRead: PublicDiscoveryNotificationSummary = {
  ...discoveryNotification,
  read_at: '2026-05-01T10:05:00Z',
};

const watchlistItem: PublicClubWatchSummary = {
  watch_id: 'watch-1',
  club: directoryItems[0],
  alert_match_three_of_four: true,
  alert_match_two_of_four: true,
  matching_open_match_count: 1,
  created_at: '2026-05-01T09:30:00Z',
};

describe('Public discovery routes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listPublicClubs).mockResolvedValue({ query: null, items: directoryItems });
    vi.mocked(listPublicClubsNearby).mockResolvedValue({ query: null, items: [directoryItems[0]] });
    vi.mocked(getPublicDiscoveryMe).mockResolvedValue(emptyDiscoveryMe);
    vi.mocked(listPublicWatchlist).mockResolvedValue({ items: [] });
    vi.mocked(identifyPublicDiscovery).mockResolvedValue({ subscriber: discoverySubscriber, recent_notifications: [discoveryNotification], unread_notifications_count: 1 });
    vi.mocked(followPublicClub).mockResolvedValue({ item: watchlistItem });
    vi.mocked(markPublicDiscoveryNotificationRead).mockResolvedValue({ subscriber: discoverySubscriber, recent_notifications: [discoveryNotificationRead], unread_notifications_count: 0 });
    vi.mocked(createPublicClubContactRequest).mockResolvedValue({ request_id: 'request-1', message: 'Richiesta inviata al circolo' });
    vi.mocked(getPublicClubDetail).mockResolvedValue(baseClubDetail);
  });

  afterEach(() => {
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: undefined,
    });
  });

  it('keeps matchinn home, explicit booking and private play routes intact in App', async () => {
    renderApp('/');
    expect(await screen.findByText('MATCHINN HOME ROUTE')).toBeInTheDocument();

    renderApp('/booking');
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
    expect(screen.getByText('Nessuna disponibilita recente')).toBeInTheDocument();
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
      .mockResolvedValueOnce(baseClubDetail)
      .mockResolvedValueOnce({
        ...baseClubDetail,
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
    expect(screen.getByText('Buona disponibilita recente')).toBeInTheDocument();
    expect(screen.getByText('Score pubblico 5 calcolato su 2 match open visibili nei prossimi 7 giorni.')).toBeInTheDocument();
    expect(screen.queryByText('Mario Rossi')).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Livello'), 'ADVANCED');

    await waitFor(() => expect(getPublicClubDetail).toHaveBeenLastCalledWith('roma-club', 'ADVANCED'));
    expect(await screen.findByText('Mancano 2 giocatori')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Entra nella community' })).toHaveAttribute('href', '/c/roma-club/play');
  });

  it('activates discovery and follows a club from /clubs', async () => {
    const user = userEvent.setup();
    vi.mocked(getPublicDiscoveryMe)
      .mockResolvedValueOnce({ subscriber: null, recent_notifications: [], unread_notifications_count: 0 })
      .mockResolvedValueOnce({ subscriber: discoverySubscriber, recent_notifications: [discoveryNotificationRead], unread_notifications_count: 0 });
    vi.mocked(listPublicWatchlist)
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ items: [watchlistItem] });

    renderApp('/clubs');

    expect(await screen.findByText('Roma Club')).toBeInTheDocument();
    await user.click(screen.getByRole('checkbox', { name: /Accetto il trattamento dei dati per salvare la sessione discovery/i }));
    await user.click(screen.getByRole('button', { name: 'Attiva discovery pubblico' }));

    await waitFor(() => expect(identifyPublicDiscovery).toHaveBeenCalled());
    expect(await screen.findByText('Alert 2/4 Roma Club')).toBeInTheDocument();
    expect(screen.getByText('Non lette: 1')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Segna come letta' }));

    await waitFor(() => expect(markPublicDiscoveryNotificationRead).toHaveBeenCalledWith('notification-1'));
    expect(await screen.findByText('Non lette: 0')).toBeInTheDocument();
    expect(screen.getByText('Letta')).toBeInTheDocument();

    await user.click(screen.getAllByRole('button', { name: 'Segui questo club' })[0]);

    await waitFor(() => expect(followPublicClub).toHaveBeenCalledWith('roma-club'));
    expect(await screen.findByText('Club seguito. Match compatibili in watchlist: 1.')).toBeInTheDocument();
  });

  it('submits the guided club contact request from /c/:clubSlug', async () => {
    const user = userEvent.setup();
    vi.mocked(getPublicDiscoveryMe).mockResolvedValue({ subscriber: discoverySubscriber, recent_notifications: [], unread_notifications_count: 0 });
    vi.mocked(listPublicWatchlist).mockResolvedValue({ items: [] });

    renderApp('/c/roma-club');

    expect(await screen.findByRole('heading', { name: 'Roma Club' })).toBeInTheDocument();

    await user.type(screen.getByLabelText('Nome'), 'Martina Smash');
    await user.type(screen.getByLabelText('Email'), 'martina@example.com');
    await user.type(screen.getByLabelText('Telefono'), '+39 333 765 4321');
    await user.type(screen.getByLabelText('Messaggio'), 'Vorrei parlare con il club prima di entrare nella community.');
    await user.click(screen.getByRole('checkbox', { name: /Accetto il trattamento dei dati per l invio della richiesta di contatto/i }));
    await user.click(screen.getByRole('button', { name: 'Invia richiesta contatto' }));

    await waitFor(() =>
      expect(createPublicClubContactRequest).toHaveBeenCalledWith(
        'roma-club',
        expect.objectContaining({
          name: 'Martina Smash',
          email: 'martina@example.com',
          phone: '+39 333 765 4321',
          preferred_level: 'INTERMEDIATE_HIGH',
        })
      )
    );
    expect(await screen.findByText('Richiesta inviata al circolo')).toBeInTheDocument();
  });
});