import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import type { AvailabilityResponse, PlayMatchSummary, PlayPlayerSummary } from '../types';

vi.mock('../services/playApi', () => ({
  acceptCommunityInvite: vi.fn(),
  cancelPlayMatch: vi.fn(),
  createPlayMatch: vi.fn(),
  getPlayMatches: vi.fn(),
  getPlaySession: vi.fn(),
  getPlaySharedMatch: vi.fn(),
  identifyPlayPlayer: vi.fn(),
  joinPlayMatch: vi.fn(),
  leavePlayMatch: vi.fn(),
  updatePlayMatch: vi.fn(),
}));

vi.mock('../services/publicApi', () => ({
  getAvailability: vi.fn(),
}));

import { getAvailability } from '../services/publicApi';
import {
  acceptCommunityInvite,
  cancelPlayMatch,
  createPlayMatch,
  getPlayMatches,
  getPlaySession,
  getPlaySharedMatch,
  identifyPlayPlayer,
  joinPlayMatch,
  leavePlayMatch,
  updatePlayMatch,
} from '../services/playApi';

const basePlayer: PlayPlayerSummary = {
  id: 'player-1',
  profile_name: 'Luca Smash',
  phone: '+393331112233',
  declared_level: 'INTERMEDIATE_MEDIUM',
  effective_level: null,
  privacy_accepted_at: '2026-04-24T10:00:00Z',
  created_at: '2026-04-24T10:00:00Z',
};

const baseAvailability: AvailabilityResponse = {
  date: '2026-05-10',
  duration_minutes: 90,
  deposit_amount: 20,
  slots: [],
  courts: [
    {
      court_id: 'court-1',
      court_name: 'Campo 1',
      badge_label: 'Indoor',
      slots: [
        {
          slot_id: 'slot-1',
          court_id: 'court-1',
          court_name: 'Campo 1',
          court_badge_label: 'Indoor',
          start_time: '18:00',
          end_time: '19:30',
          display_start_time: '18:00',
          display_end_time: '19:30',
          available: true,
          reason: null,
        },
      ],
    },
  ],
};

function buildMatch(id: string, note: string, participantCount: number): PlayMatchSummary {
  const participants = Array.from({ length: participantCount }, (_, index) => ({
    player_id: `${id}-player-${index + 1}`,
    profile_name: `Player ${index + 1}`,
    declared_level: 'INTERMEDIATE_MEDIUM' as const,
    effective_level: null,
  }));

  return {
    id,
    share_token: `share-${id}`,
    court_id: 'court-1',
    court_name: 'Campo 1',
    court_badge_label: 'Indoor',
    created_by_player_id: `${id}-creator`,
    creator_profile_name: 'Club Captain',
    start_at: '2026-05-10T18:00:00Z',
    end_at: '2026-05-10T19:30:00Z',
    duration_minutes: 90,
    status: 'OPEN',
    level_requested: 'INTERMEDIATE_MEDIUM',
    note,
    participant_count: participantCount,
    available_spots: 4 - participantCount,
    joined_by_current_player: false,
    created_at: '2026-05-01T10:00:00Z',
    participants,
  };
}

function renderApp(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <App />
    </MemoryRouter>
  );
}

describe('Play phase 2 pages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    vi.mocked(getAvailability).mockResolvedValue({ ...baseAvailability });
    vi.mocked(getPlaySession).mockResolvedValue({ player: null });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: null,
      open_matches: [
        buildMatch('match-3of4', '3 su 4', 3),
        buildMatch('match-2of4', '2 su 4', 2),
        buildMatch('match-1of4', '1 su 4', 1),
      ],
      my_matches: [],
    });
    vi.mocked(identifyPlayPlayer).mockResolvedValue({
      message: 'Profilo play identificato',
      player: { ...basePlayer },
    });
    vi.mocked(acceptCommunityInvite).mockResolvedValue({
      message: 'Ingresso community completato',
      player: { ...basePlayer },
    });
    vi.mocked(createPlayMatch).mockResolvedValue({
      created: true,
      message: 'Partita play creata correttamente.',
      match: buildMatch('match-created', 'created', 1),
      suggested_matches: [],
    });
    vi.mocked(joinPlayMatch).mockResolvedValue({
      action: 'JOINED',
      message: 'Ti sei unito alla partita.',
      match: buildMatch('match-shared', 'shared 4 su 4', 4),
      booking: null,
    });
    vi.mocked(leavePlayMatch).mockResolvedValue({
      action: 'LEFT',
      message: 'Hai lasciato la partita.',
      match: buildMatch('match-left', 'left', 2),
    });
    vi.mocked(updatePlayMatch).mockResolvedValue({
      action: 'UPDATED',
      message: 'Partita aggiornata.',
      match: buildMatch('match-updated', 'updated', 2),
    });
    vi.mocked(cancelPlayMatch).mockResolvedValue({
      action: 'CANCELLED',
      message: 'Partita annullata.',
      match: { ...buildMatch('match-cancelled', 'cancelled', 1), status: 'CANCELLED' },
    });
    vi.mocked(getPlaySharedMatch).mockResolvedValue({
      player: null,
      match: buildMatch('match-shared', 'shared 3 su 4', 3),
    });
  });

  it('renders the canonical /c/:clubSlug/play route, preserves tenant slug and keeps the visual order of open matches', async () => {
    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Completa prima le partite aperte del club' });

    expect(getPlaySession).toHaveBeenCalledWith('roma-club');
    expect(getPlayMatches).toHaveBeenCalledWith('roma-club');
    await waitFor(() => expect(getAvailability).toHaveBeenCalledWith(expect.any(String), 90, 'roma-club'));

    const cards = await screen.findAllByTestId('play-open-match-card');
    expect(within(cards[0]).getByText('3 su 4')).toBeInTheDocument();
    expect(within(cards[1]).getByText('2 su 4')).toBeInTheDocument();
    expect(within(cards[2]).getByText('1 su 4')).toBeInTheDocument();
  });

  it('redirects the /play alias to the canonical tenant route and keeps tenant propagation', async () => {
    renderApp('/play?tenant=roma-club');

    await screen.findByRole('heading', { name: 'Completa prima le partite aperte del club' });
    expect(getPlayMatches).toHaveBeenCalledWith('roma-club');
  });

  it('asks for identification when an anonymous user tries to join a match', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play');

    await waitFor(() => expect(screen.getAllByRole('button', { name: 'Unisciti' }).length).toBeGreaterThan(0));
    await user.click(screen.getAllByRole('button', { name: 'Unisciti' })[0]);

    await screen.findByRole('heading', { name: 'Identificati per unirti alla partita' });
    await user.type(screen.getByLabelText('Nome profilo'), 'Luca Smash');
    await user.type(screen.getByLabelText('Telefono'), '+39 333 1112233');
    await user.click(screen.getByText('Accetto la privacy per essere riconosciuto nel club e usare il modulo play.'));
    await user.click(screen.getByRole('button', { name: 'Conferma profilo' }));

    await waitFor(() => expect(identifyPlayPlayer).toHaveBeenCalledWith(expect.objectContaining({
      profile_name: 'Luca Smash',
      phone: '+39 333 1112233',
      privacy_accepted: true,
    }), 'roma-club'));
    await waitFor(() => expect(joinPlayMatch).toHaveBeenCalledWith('match-3of4', 'roma-club'));
    expect(await screen.findByText('Ti sei unito alla partita.')).toBeInTheDocument();
  });

  it('continues the create flow immediately after identification', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Completa prima le partite aperte del club' });
    await user.type(screen.getByLabelText('Nota opzionale'), 'cerco ultimo giocatore');
    await user.click(screen.getByRole('button', { name: 'Crea nuova partita' }));

    await screen.findByRole('heading', { name: 'Identificati per creare una nuova partita' });
    await user.type(screen.getByLabelText('Nome profilo'), 'Luca Smash');
    await user.type(screen.getByLabelText('Telefono'), '+39 333 1112233');
    await user.click(screen.getByText('Accetto la privacy per essere riconosciuto nel club e usare il modulo play.'));
    await user.click(screen.getByRole('button', { name: 'Conferma profilo' }));

    await waitFor(() => expect(createPlayMatch).toHaveBeenCalledWith(expect.objectContaining({
      court_id: 'court-1',
      start_time: '18:00',
      slot_id: 'slot-1',
      duration_minutes: 90,
      level_requested: 'NO_PREFERENCE',
      note: 'cerco ultimo giocatore',
      force_create: false,
    }), 'roma-club'));
    expect(await screen.findByText('Partita play creata correttamente.')).toBeInTheDocument();
  });

  it('requires privacy before accepting a community invite', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play/invite/invite-123');

    await screen.findByRole('heading', { name: 'Ingresso community del club' });
    await user.click(screen.getByRole('button', { name: 'Entra nella community' }));

    expect(acceptCommunityInvite).not.toHaveBeenCalled();
    expect(await screen.findByText('Per entrare nella community devi accettare la privacy.')).toBeInTheDocument();
  });

  it('shows a clear error when the invite alias is opened without a tenant context', async () => {
    renderApp('/play/invite/invite-123');

    await screen.findByRole('heading', { name: 'Link invito incompleto' });
    expect(screen.getByText(/Questo invito play richiede il club corretto/)).toBeInTheDocument();
    expect(acceptCommunityInvite).not.toHaveBeenCalled();
  });

  it('shows a clear error when the match alias is opened without a tenant context', async () => {
    renderApp('/play/matches/share-match-shared');

    await screen.findByRole('heading', { name: 'Link partita incompleto' });
    expect(screen.getByText(/Questo link partita richiede il club corretto/)).toBeInTheDocument();
    expect(getPlaySharedMatch).not.toHaveBeenCalled();
  });

  it('shows the shared match page for an anonymous visitor and requests identification before join', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play/matches/share-match-shared');

    await screen.findByRole('heading', { name: 'Partita condivisa' });
    expect(getPlaySharedMatch).toHaveBeenCalledWith('share-match-shared', 'roma-club');
    expect(await screen.findByText('Per unirti da questa pagina devi prima identificarti sul tenant corrente del club.')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Identificati per unirti' }));
    expect(await screen.findByRole('heading', { name: 'Identificati per proseguire dal link condiviso' })).toBeInTheDocument();
  });

  it('shows the shared match page for a recognized player', async () => {
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer } });
    vi.mocked(getPlaySharedMatch).mockResolvedValue({
      player: { ...basePlayer },
      match: buildMatch('match-shared', 'shared 3 su 4', 3),
    });

    renderApp('/c/roma-club/play/matches/share-match-shared');

    await screen.findByRole('heading', { name: 'Partita condivisa' });
    expect(await screen.findByText(/Profilo attivo:/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Unisciti' })).toBeInTheDocument();
  });

  it('shows compatible matches before forcing a new create flow', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [buildMatch('match-3of4', '3 su 4', 3)],
      my_matches: [],
    });
    vi.mocked(createPlayMatch)
      .mockResolvedValueOnce({
        created: false,
        message: 'Esistono gia partite compatibili da completare prima di aprirne una nuova.',
        match: null,
        suggested_matches: [buildMatch('match-suggested', '3 su 4 compatibile', 3)],
      })
      .mockResolvedValueOnce({
        created: true,
        message: 'Partita play creata correttamente.',
        match: buildMatch('match-created', 'created', 1),
        suggested_matches: [],
      });

    renderApp('/c/roma-club/play');

    await screen.findByRole('heading', { name: 'Completa prima le partite aperte del club' });
    await user.click(screen.getByRole('button', { name: 'Crea nuova partita' }));

    expect(await screen.findByRole('heading', { name: 'Prima completa queste partite compatibili' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Crea comunque una nuova partita' }));

    await waitFor(() => expect(createPlayMatch).toHaveBeenNthCalledWith(2, expect.objectContaining({ force_create: true }), 'roma-club'));
    expect(await screen.findByText('Partita play creata correttamente.')).toBeInTheDocument();
  });

  it('continues shared onboarding and joins after identification', async () => {
    const user = userEvent.setup();

    renderApp('/c/roma-club/play/matches/share-match-shared');

    await screen.findByRole('heading', { name: 'Partita condivisa' });
    await user.click(screen.getByRole('button', { name: 'Identificati per unirti' }));
    await user.type(screen.getByLabelText('Nome profilo'), 'Luca Smash');
    await user.type(screen.getByLabelText('Telefono'), '+39 333 1112233');
    await user.click(screen.getByText('Accetto la privacy per essere riconosciuto nel club e usare il modulo play.'));
    await user.click(screen.getByRole('button', { name: 'Conferma profilo' }));

    await waitFor(() => expect(joinPlayMatch).toHaveBeenCalledWith('match-shared', 'roma-club'));
    expect(await screen.findByText('Ti sei unito alla partita.')).toBeInTheDocument();
  });

  it('shows leave action for joined personal matches and calls the leave endpoint', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [
        {
          ...buildMatch('match-my-open', 'mia partita', 3),
          joined_by_current_player: true,
          participants: [
            {
              player_id: basePlayer.id,
              profile_name: basePlayer.profile_name,
              declared_level: basePlayer.declared_level,
              effective_level: null,
            },
          ],
        },
      ],
    });

    renderApp('/c/roma-club/play');

    const card = (await screen.findAllByTestId('play-my-match-card'))[0];
    expect(within(card).getByRole('button', { name: 'Lascia' })).toBeInTheDocument();
    expect(within(card).queryByRole('button', { name: 'Modifica' })).not.toBeInTheDocument();

    await user.click(within(card).getByRole('button', { name: 'Lascia' }));

    await waitFor(() => expect(leavePlayMatch).toHaveBeenCalledWith('match-my-open', 'roma-club'));
    expect(await screen.findByText('Hai lasciato la partita.')).toBeInTheDocument();
  });

  it('lets the creator update level and note from the manage panel', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [
        {
          ...buildMatch('match-my-edit', 'nota iniziale', 2),
          created_by_player_id: basePlayer.id,
          creator_profile_name: basePlayer.profile_name,
          joined_by_current_player: true,
        },
      ],
    });

    renderApp('/c/roma-club/play');

    const card = (await screen.findAllByTestId('play-my-match-card'))[0];
    await user.click(within(card).getByRole('button', { name: 'Modifica' }));

    await screen.findByRole('heading', { name: 'Gestisci il tuo match' });
    await user.selectOptions(screen.getByLabelText('Livello match'), 'ADVANCED');
    await user.clear(screen.getByLabelText('Nota'));
    await user.type(screen.getByLabelText('Nota'), 'solo ritmo alto');
    await user.click(screen.getByRole('button', { name: 'Salva modifiche' }));

    await waitFor(() => expect(updatePlayMatch).toHaveBeenCalledWith('match-my-edit', {
      level_requested: 'ADVANCED',
      note: 'solo ritmo alto',
    }, 'roma-club'));
    expect(await screen.findByText('Partita aggiornata.')).toBeInTheDocument();
  });

  it('lets the creator cancel an open match from personal actions', async () => {
    const user = userEvent.setup();
    vi.mocked(getPlaySession).mockResolvedValue({ player: { ...basePlayer } });
    vi.mocked(getPlayMatches).mockResolvedValue({
      player: { ...basePlayer },
      open_matches: [],
      my_matches: [
        {
          ...buildMatch('match-my-cancel', 'da annullare', 2),
          created_by_player_id: basePlayer.id,
          creator_profile_name: basePlayer.profile_name,
          joined_by_current_player: true,
        },
      ],
    });

    renderApp('/c/roma-club/play');

    const card = (await screen.findAllByTestId('play-my-match-card'))[0];
    await user.click(within(card).getByRole('button', { name: 'Annulla match' }));

    await waitFor(() => expect(window.confirm).toHaveBeenCalled());
    await waitFor(() => expect(cancelPlayMatch).toHaveBeenCalledWith('match-my-cancel', 'roma-club'));
    expect(await screen.findByText('Partita annullata.')).toBeInTheDocument();
  });
});