import { render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PublicClubPage } from './PublicClubPage';
import type { PublicClubDetailResponse, PublicDiscoveryMeResponse } from '../types';

vi.mock('../services/publicApi', () => ({
  createPublicClubContactRequest: vi.fn(),
  followPublicClub: vi.fn(),
  getPublicClubDetail: vi.fn(),
  getPublicDiscoveryMe: vi.fn(),
  listPublicWatchlist: vi.fn(),
  unfollowPublicClub: vi.fn(),
}));

import {
  createPublicClubContactRequest,
  followPublicClub,
  getPublicClubDetail,
  getPublicDiscoveryMe,
  listPublicWatchlist,
  unfollowPublicClub,
} from '../services/publicApi';

const discoveryResponse: PublicDiscoveryMeResponse = {
  subscriber: null,
  recent_notifications: [],
  unread_notifications_count: 0,
};

function buildClubDetail(isCommunityOpen: boolean): PublicClubDetailResponse {
  return {
    club: {
      club_id: 'club-1',
      club_slug: 'test-club',
      public_name: 'Test Club',
      public_address: 'Via Padel 1',
      public_postal_code: '17100',
      public_city: 'Savona',
      public_province: 'SV',
      public_latitude: 44.3,
      public_longitude: 8.48,
      has_coordinates: true,
      distance_km: 1.2,
      courts_count: 3,
      contact_email: 'info@testclub.example',
      support_phone: '+390101010101',
      is_community_open: isCommunityOpen,
      public_activity_score: 6,
      recent_open_matches_count: 3,
      public_activity_label: 'Alta disponibilita recente',
      open_matches_three_of_four_count: 1,
      open_matches_two_of_four_count: 1,
      open_matches_one_of_four_count: 1,
    },
    timezone: 'Europe/Rome',
    support_email: 'info@testclub.example',
    support_phone: '+390101010101',
    public_match_window_days: 7,
    open_matches: [
      {
        id: 'match-one',
        court_name: 'Campo 1',
        court_badge_label: 'Indoor',
        start_at: '2026-05-10T18:00:00Z',
        end_at: '2026-05-10T19:30:00Z',
        level_requested: 'INTERMEDIATE_HIGH',
        participant_count: 1,
        available_spots: 3,
        occupancy_label: '1/4',
        missing_players_message: 'Mancano 3 giocatori',
      },
      {
        id: 'match-three',
        court_name: 'Campo 2',
        court_badge_label: 'Outdoor',
        start_at: '2026-05-09T18:00:00Z',
        end_at: '2026-05-09T19:30:00Z',
        level_requested: 'INTERMEDIATE_HIGH',
        participant_count: 3,
        available_spots: 1,
        occupancy_label: '3/4',
        missing_players_message: 'Manca 1 giocatore',
      },
      {
        id: 'match-two',
        court_name: 'Campo 3',
        court_badge_label: null,
        start_at: '2026-05-11T18:00:00Z',
        end_at: '2026-05-11T19:30:00Z',
        level_requested: 'INTERMEDIATE_HIGH',
        participant_count: 2,
        available_spots: 2,
        occupancy_label: '2/4',
        missing_players_message: 'Mancano 2 giocatori',
      },
    ],
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/c/test-club']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path='/c/:clubSlug' element={<PublicClubPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('PublicClubPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getPublicDiscoveryMe).mockResolvedValue({ ...discoveryResponse });
    vi.mocked(listPublicWatchlist).mockResolvedValue({ items: [] });
    vi.mocked(createPublicClubContactRequest).mockResolvedValue({ request_id: 'request-1', message: 'ok' });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('groups public matches by priority and keeps the community CTA for open clubs', async () => {
    vi.mocked(getPublicClubDetail).mockResolvedValue(buildClubDetail(true));

    renderPage();

    await screen.findByText('Partite da chiudere');
    expect(screen.getByText('Da chiudere subito')).toBeInTheDocument();
    expect(screen.getByText('Buone occasioni')).toBeInTheDocument();
    expect(screen.getByText('Da monitorare')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Entra nella community' })).toHaveAttribute('href', '/c/test-club/play');

    const cards = screen.getAllByTestId('public-open-match-card');
    expect(within(cards[0]).getByText('Manca 1 giocatore')).toBeInTheDocument();
    expect(within(cards[1]).getByText('Mancano 2 giocatori')).toBeInTheDocument();
    expect(within(cards[2]).getByText('Mancano 3 giocatori')).toBeInTheDocument();
  });

  it('uses request-access CTA and dedicated copy for private clubs', async () => {
    vi.mocked(getPublicClubDetail).mockResolvedValue(buildClubDetail(false));

    renderPage();

    await screen.findByText('Richiedi accesso alla community');
    expect(screen.getByRole('link', { name: 'Richiedi accesso' })).toHaveAttribute('href', '#club-contact-request');
    expect(screen.queryByRole('link', { name: 'Entra nella community' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Invia richiesta accesso' })).toBeInTheDocument();
    expect(screen.getByText('La community del club e su richiesta: usa il form qui sopra per chiedere accesso senza uscire dal perimetro pubblico.')).toBeInTheDocument();
  });
});