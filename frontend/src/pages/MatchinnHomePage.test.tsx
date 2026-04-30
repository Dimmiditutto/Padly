import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MatchinnHomePage } from './MatchinnHomePage';
import type {
  MatchinnHomeOpenMatchesResponse,
  PublicClubDirectoryResponse,
  PublicClubSummary,
  PublicDiscoveryMeResponse,
} from '../types';

vi.mock('../services/publicApi', () => ({
  getMatchinnHomeCommunities: vi.fn(),
  getMatchinnHomeOpenMatches: vi.fn(),
  getPublicDiscoveryMe: vi.fn(),
  listPublicClubsNearby: vi.fn(),
}));

import {
  getMatchinnHomeCommunities,
  getMatchinnHomeOpenMatches,
  getPublicDiscoveryMe,
  listPublicClubsNearby,
} from '../services/publicApi';

const romaClub: PublicClubSummary = {
  club_id: 'club-roma',
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
  courts_count: 4,
  contact_email: 'desk@roma-club.example',
  support_phone: '+39061234567',
  is_community_open: true,
  public_activity_score: 5,
  recent_open_matches_count: 2,
  public_activity_label: 'Buona disponibilita recente',
  open_matches_three_of_four_count: 1,
  open_matches_two_of_four_count: 1,
  open_matches_one_of_four_count: 0,
};

const savonaClub: PublicClubSummary = {
  club_id: 'club-savona',
  club_slug: 'savona-club',
  public_name: 'Savona Club',
  public_address: 'Piazza Sport 2',
  public_postal_code: '17100',
  public_city: 'Savona',
  public_province: 'SV',
  public_latitude: 44.3,
  public_longitude: 8.48,
  has_coordinates: true,
  distance_km: 2.4,
  courts_count: 3,
  contact_email: 'desk@savona-club.example',
  support_phone: '+39019999999',
  is_community_open: false,
  public_activity_score: 3,
  recent_open_matches_count: 1,
  public_activity_label: 'Buona disponibilita recente',
  open_matches_three_of_four_count: 0,
  open_matches_two_of_four_count: 1,
  open_matches_one_of_four_count: 0,
};

const discoveryContext: PublicDiscoveryMeResponse = {
  subscriber: {
    subscriber_id: 'subscriber-1',
    preferred_level: 'INTERMEDIATE_HIGH',
    preferred_time_slots: ['morning', 'evening'],
    latitude: 44.30941,
    longitude: 8.47715,
    has_coordinates: true,
    nearby_radius_km: 25,
    nearby_digest_enabled: true,
    last_identified_at: '2026-05-01T09:00:00Z',
    created_at: '2026-05-01T09:00:00Z',
    updated_at: '2026-05-01T09:00:00Z',
  },
  recent_notifications: [],
  unread_notifications_count: 1,
};

function renderPage() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <MatchinnHomePage />
    </MemoryRouter>
  );
}

describe('MatchinnHomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getMatchinnHomeCommunities).mockResolvedValue({ items: [romaClub] });
    vi.mocked(getPublicDiscoveryMe).mockResolvedValue(discoveryContext);
    vi.mocked(listPublicClubsNearby).mockResolvedValue({ query: null, items: [savonaClub] } satisfies PublicClubDirectoryResponse);
    vi.mocked(getMatchinnHomeOpenMatches).mockResolvedValue({
      items: [
        {
          club: romaClub,
          match: {
            id: 'match-roma',
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
        },
        {
          club: savonaClub,
          match: {
            id: 'match-savona',
            court_name: 'Campo 2',
            court_badge_label: null,
            start_at: '2026-05-11T19:00:00Z',
            end_at: '2026-05-11T20:30:00Z',
            level_requested: 'INTERMEDIATE_HIGH',
            participant_count: 2,
            available_spots: 2,
            occupancy_label: '2/4',
            missing_players_message: 'Mancano 2 giocatori',
          },
        },
      ],
      location_source: 'discovery',
      preferred_level: 'INTERMEDIATE_HIGH',
    } satisfies MatchinnHomeOpenMatchesResponse);
  });

  it('renders recognized communities, nearby clubs and contextual match CTAs', async () => {
    renderPage();

    expect(await screen.findByRole('heading', { name: /Matchinn ti trova il club e la partita giusta/i })).toBeInTheDocument();
    expect(getMatchinnHomeCommunities).toHaveBeenCalled();
    expect(getPublicDiscoveryMe).toHaveBeenCalled();
    expect(getMatchinnHomeOpenMatches).toHaveBeenCalledWith({ limit: 6 });
    await waitFor(() => expect(listPublicClubsNearby).toHaveBeenCalledWith(44.30941, 8.47715));

    expect(screen.getByRole('link', { name: 'Entra nella community Roma Club' })).toHaveAttribute('href', '/c/roma-club/play');
    expect(screen.getByRole('link', { name: 'Entra e gioca Roma Club' })).toHaveAttribute('href', '/c/roma-club/play');
    expect(screen.getByRole('link', { name: 'Apri club Savona Club' })).toHaveAttribute('href', '/c/savona-club');
    expect(screen.getByText(/Discovery salvata: livello Intermedio alto/i)).toBeInTheDocument();
  });

  it('shows anonymous community state and routes booking through club selection when no session is available', async () => {
    vi.mocked(getMatchinnHomeCommunities).mockResolvedValue({ items: [] });
    vi.mocked(getPublicDiscoveryMe).mockResolvedValue({ subscriber: null, recent_notifications: [], unread_notifications_count: 0 });
    vi.mocked(getMatchinnHomeOpenMatches).mockResolvedValue({ items: [], location_source: 'none', preferred_level: null });

    renderPage();

    expect(await screen.findByText(/Nessuna community attiva trovata in questo browser/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ottieni codice OTP dal tuo club' })).toHaveAttribute('href', '/clubs');
    expect(screen.getByRole('link', { name: 'Scegli il club per prenotare' })).toHaveAttribute('href', '/clubs');
    expect(screen.getByText(/Aggiungi la posizione o attiva discovery/i)).toBeInTheDocument();
  });
});