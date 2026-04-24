import { ArrowLeft, Sparkles, UsersRound } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { AppBrand } from '../components/AppBrand';
import { LoadingBlock } from '../components/LoadingBlock';
import { SectionCard } from '../components/SectionCard';
import { CreateMatchForm, type PlayCreateIntent } from '../components/play/CreateMatchForm';
import { JoinConfirmModal } from '../components/play/JoinConfirmModal';
import { MatchBoard } from '../components/play/MatchBoard';
import { MyMatches } from '../components/play/MyMatches';
import { cancelPlayMatch, createPlayMatch, getPlayMatches, getPlaySession, joinPlayMatch, leavePlayMatch, updatePlayMatch } from '../services/playApi';
import type { PlayLevel, PlayMatchSummary, PlayMatchesResponse, PlayPlayerSummary } from '../types';
import { getTenantSlugFromSearchParams, normalizeTenantSlug, withTenantPath } from '../utils/tenantContext';
import { buildClubPlayPath, buildPlayMatchPath, PLAY_LEVEL_OPTIONS } from '../utils/play';

type FeedbackTone = 'info' | 'success' | 'warning' | 'error';

type PendingAction =
  | { kind: 'join'; match: PlayMatchSummary }
  | { kind: 'create'; intent: PlayCreateIntent };

export function PlayPage() {
  const { clubSlug } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const tenantSlug = normalizeTenantSlug(clubSlug) || getTenantSlugFromSearchParams(searchParams) || null;
  const [playData, setPlayData] = useState<PlayMatchesResponse | null>(null);
  const [currentPlayer, setCurrentPlayer] = useState<PlayPlayerSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ tone: FeedbackTone; message: string } | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [suggestedMatches, setSuggestedMatches] = useState<PlayMatchSummary[]>([]);
  const [pendingCreateIntent, setPendingCreateIntent] = useState<PlayCreateIntent | null>(null);
  const [managedMatch, setManagedMatch] = useState<PlayMatchSummary | null>(null);
  const [managedLevel, setManagedLevel] = useState<PlayLevel>('NO_PREFERENCE');
  const [managedNote, setManagedNote] = useState('');
  const [savingManageAction, setSavingManageAction] = useState(false);

  useEffect(() => {
    if (!tenantSlug) {
      setLoading(false);
      setFeedback({ tone: 'error', message: 'Tenant play non valido. Apri la pagina da un club specifico.' });
      return;
    }

    void loadPlaySurface(tenantSlug);
  }, [tenantSlug]);

  const openMatches = useMemo(() => playData?.open_matches || [], [playData]);
  const myMatches = useMemo(() => playData?.my_matches || [], [playData]);

  async function loadPlaySurface(resolvedTenantSlug: string) {
    setLoading(true);
    try {
      const [session, matches] = await Promise.all([
        getPlaySession(resolvedTenantSlug),
        getPlayMatches(resolvedTenantSlug),
      ]);
      setCurrentPlayer(session.player || matches.player || null);
      setPlayData(matches);
    } catch {
      setFeedback({ tone: 'error', message: 'Non riesco a caricare la bacheca play del club.' });
    } finally {
      setLoading(false);
    }
  }

  function requireIdentity(action: PendingAction) {
    setPendingAction(action);
  }

  async function performJoin(match: PlayMatchSummary, player = currentPlayer) {
    if (!tenantSlug || !player) {
      return;
    }

    try {
      const response = await joinPlayMatch(match.id, tenantSlug);
      setFeedback({
        tone: response.action === 'COMPLETED' ? 'success' : 'info',
        message: response.booking
          ? `${response.message} Riferimento prenotazione ${response.booking.public_reference}.`
          : response.message,
      });
      setSuggestedMatches([]);
      setPendingCreateIntent(null);
      await loadPlaySurface(tenantSlug);
    } catch (error) {
      setFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : 'Non riesco a completare il join della partita.',
      });
    }
  }

  function openManagePanel(match: PlayMatchSummary) {
    setManagedMatch(match);
    setManagedLevel(match.level_requested);
    setManagedNote(match.note || '');
  }

  function closeManagePanel() {
    setManagedMatch(null);
    setManagedLevel('NO_PREFERENCE');
    setManagedNote('');
  }

  function handleJoin(match: PlayMatchSummary) {
    if (!currentPlayer) {
      requireIdentity({ kind: 'join', match });
      return;
    }

    void performJoin(match, currentPlayer);
  }

  async function handleLeave(match: PlayMatchSummary) {
    if (!tenantSlug || !currentPlayer || savingManageAction) {
      return;
    }
    setSavingManageAction(true);
    try {
      const response = await leavePlayMatch(match.id, tenantSlug);
      setFeedback({ tone: response.action === 'CANCELLED' ? 'warning' : 'success', message: response.message });
      if (managedMatch?.id === match.id) {
        closeManagePanel();
      }
      await loadPlaySurface(tenantSlug);
    } catch (error) {
      setFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : 'Non riesco a lasciare la partita.',
      });
    } finally {
      setSavingManageAction(false);
    }
  }

  async function handleCancel(match: PlayMatchSummary) {
    if (!tenantSlug || !currentPlayer || savingManageAction) {
      return;
    }
    if (!window.confirm('Confermi l\'annullamento del match aperto?')) {
      return;
    }
    setSavingManageAction(true);
    try {
      const response = await cancelPlayMatch(match.id, tenantSlug);
      setFeedback({ tone: 'warning', message: response.message });
      if (managedMatch?.id === match.id) {
        closeManagePanel();
      }
      await loadPlaySurface(tenantSlug);
    } catch (error) {
      setFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : 'Non riesco ad annullare il match.',
      });
    } finally {
      setSavingManageAction(false);
    }
  }

  async function handleSaveManagedMatch() {
    if (!tenantSlug || !managedMatch || savingManageAction) {
      return;
    }
    setSavingManageAction(true);
    try {
      const response = await updatePlayMatch(managedMatch.id, {
        level_requested: managedLevel,
        note: managedNote.trim() || null,
      }, tenantSlug);
      setFeedback({ tone: 'success', message: response.message });
      closeManagePanel();
      await loadPlaySurface(tenantSlug);
    } catch (error) {
      setFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : 'Non riesco a salvare le modifiche del match.',
      });
    } finally {
      setSavingManageAction(false);
    }
  }

  async function submitCreateIntent(intent: PlayCreateIntent, forceCreate = false, player = currentPlayer) {
    if (!tenantSlug || !player) {
      return;
    }

    try {
      const response = await createPlayMatch({
        booking_date: intent.bookingDate,
        court_id: intent.courtId,
        start_time: intent.startTime,
        slot_id: intent.slotId,
        duration_minutes: intent.durationMinutes,
        level_requested: intent.levelRequested,
        note: intent.note,
        force_create: forceCreate,
      }, tenantSlug);

      if (!response.created) {
        setPendingCreateIntent(intent);
        setSuggestedMatches(response.suggested_matches);
        setFeedback({ tone: 'warning', message: response.message });
        return;
      }

      setPendingCreateIntent(null);
      setSuggestedMatches([]);
      setFeedback({ tone: 'success', message: response.message });
      await loadPlaySurface(tenantSlug);
    } catch (error) {
      setFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : 'Non riesco a creare la partita play.',
      });
    }
  }

  function handleCreateIntent(intent: PlayCreateIntent) {
    if (!currentPlayer) {
      requireIdentity({ kind: 'create', intent });
      return;
    }

    void submitCreateIntent(intent, false);
  }

  async function handleIdentifySuccess(player: PlayPlayerSummary) {
    if (!tenantSlug) {
      return;
    }

    const action = pendingAction;
    setPendingAction(null);
    setCurrentPlayer(player);

    if (!action) {
      await loadPlaySurface(tenantSlug);
      setFeedback({ tone: 'success', message: `Profilo play attivo. Bentornato ${player.profile_name}.` });
      return;
    }

    if (action.kind === 'join') {
      await performJoin(action.match, player);
      return;
    }

    await submitCreateIntent(action.intent, false, player);
  }

  async function handleShare(match: PlayMatchSummary) {
    if (!tenantSlug) {
      return;
    }

    const sharePath = buildPlayMatchPath(tenantSlug, match.share_token);
    const absoluteUrl = typeof window !== 'undefined' ? `${window.location.origin}${sharePath}` : sharePath;

    try {
      await navigator.clipboard.writeText(absoluteUrl);
      setFeedback({ tone: 'success', message: 'Link partita copiato negli appunti.' });
    } catch {
      setFeedback({ tone: 'info', message: `Link pronto per la condivisione: ${absoluteUrl}` });
    }
  }

  function handleOpenShared(match: PlayMatchSummary) {
    if (!tenantSlug) {
      return;
    }
    navigate(buildPlayMatchPath(tenantSlug, match.share_token));
  }

  if (!tenantSlug) {
    return (
      <div className='page-shell max-w-5xl'>
        <AlertBanner tone='error'>Tenant play non risolto. Usa una route del tipo `/c/&lt;club-slug&gt;/play`.</AlertBanner>
      </div>
    );
  }

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='page-shell max-w-6xl'>
        <header className='rounded-[28px] border border-cyan-400/20 bg-slate-950/80 p-6 text-white shadow-soft'>
          <div className='flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between'>
            <div className='max-w-3xl'>
              <AppBrand light label='Play community' />
              <h1 className='mt-4 text-3xl font-bold tracking-tight text-white sm:text-4xl'>Completa prima le partite aperte del club</h1>
              <p className='mt-3 text-sm leading-6 text-slate-300 sm:text-base'>La bacheca /play ordina le partite gia quasi piene, ti fa riconoscere con un profilo leggero e prepara il flusso community senza toccare la homepage booking su `/`.</p>
            </div>

            <div className='flex flex-col gap-3 sm:flex-row'>
              <Link className='btn-secondary' to={buildClubPlayPath(tenantSlug)}>
                <Sparkles size={16} />
                <span>Ricarica la bacheca</span>
              </Link>
              <Link className='btn-secondary' to={withTenantPath('/', tenantSlug)}>
                <ArrowLeft size={16} />
                <span>Torna al booking</span>
              </Link>
            </div>
          </div>

          <div className='mt-5 rounded-[24px] border border-white/10 bg-white/5 p-4'>
            {currentPlayer ? (
              <AlertBanner tone='success' title='Profilo play attivo'>
                Sei riconosciuto come <strong>{currentPlayer.profile_name}</strong>. Le tue partite e i CTA join/create ora possono usare il tenant corretto del club.
              </AlertBanner>
            ) : (
              <AlertBanner tone='info' title='Ingresso leggero nella community'>
                Per unirti o preparare una nuova partita ti basta nome profilo, telefono, livello dichiarato e consenso privacy.
              </AlertBanner>
            )}
          </div>
        </header>

        <div className='mt-6 space-y-6'>
          {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

          {loading ? (
            <LoadingBlock label='Carico la bacheca community del club…' labelClassName='text-base' />
          ) : (
            <>
              <SectionCard
                title='Partite da completare'
                description='Ordinate 3/4, poi 2/4, poi 1/4. Il focus della pagina resta completare i match gia avviati.'
                elevated
              >
                <MatchBoard matches={openMatches} onJoin={handleJoin} onShare={handleShare} />
              </SectionCard>

              {suggestedMatches.length > 0 ? (
                <SectionCard
                  title='Prima completa queste partite compatibili'
                  description='Il backend ha trovato partite gia aperte nello stesso orario. Il force create e esplicito e separato.'
                >
                  <div className='space-y-4'>
                    <AlertBanner tone='warning'>Il club ha gia partite compatibili da completare prima di aprirne una nuova.</AlertBanner>
                    <MatchBoard matches={suggestedMatches} onJoin={handleJoin} onShare={handleShare} />
                    {pendingCreateIntent ? (
                      <button type='button' className='btn-secondary' onClick={() => void submitCreateIntent(pendingCreateIntent, true)}>
                        Crea comunque una nuova partita
                      </button>
                    ) : null}
                  </div>
                </SectionCard>
              ) : null}

              <SectionCard
                title='Crea nuova partita'
                description='Scegli giorno, slot libero reale, campo e livello. Il motore slot e gia tenant-aware e riusa la disponibilita esistente del club.'
              >
                <CreateMatchForm tenantSlug={tenantSlug} onCreateIntent={handleCreateIntent} />
              </SectionCard>

              {managedMatch ? (
                <SectionCard
                  title='Gestisci il tuo match'
                  description='Puoi aggiornare solo livello e nota del match aperto di cui sei creator. Leave e cancel restano azioni separate e coerenti con le regole backend.'
                >
                  <div className='space-y-4'>
                    <div className='grid gap-4 lg:grid-cols-2'>
                      <div>
                        <label className='field-label' htmlFor='play-manage-level'>Livello match</label>
                        <select
                          id='play-manage-level'
                          className='text-input'
                          value={managedLevel}
                          onChange={(event) => setManagedLevel(event.target.value as PlayLevel)}
                        >
                          {PLAY_LEVEL_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </div>
                      <div className='rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600'>
                        <p><strong className='text-slate-900'>Match:</strong> {managedMatch.court_name || 'Campo del club'} • {managedMatch.participant_count}/4</p>
                        <p className='mt-2'><strong className='text-slate-900'>Creator:</strong> {managedMatch.creator_profile_name || 'Community del club'}</p>
                      </div>
                    </div>

                    <div>
                      <label className='field-label' htmlFor='play-manage-note'>Nota</label>
                      <textarea
                        id='play-manage-note'
                        className='text-input min-h-[112px] resize-y'
                        value={managedNote}
                        onChange={(event) => setManagedNote(event.target.value)}
                        placeholder='Aggiorna il tono della partita, il livello richiesto o informazioni utili per chi si unisce.'
                      />
                    </div>

                    <div className='flex flex-wrap gap-3'>
                      <button type='button' className='btn-primary' disabled={savingManageAction} onClick={() => void handleSaveManagedMatch()}>
                        {savingManageAction ? 'Salvataggio…' : 'Salva modifiche'}
                      </button>
                      <button type='button' className='btn-secondary' disabled={savingManageAction} onClick={closeManagePanel}>
                        Chiudi pannello
                      </button>
                    </div>
                  </div>
                </SectionCard>
              ) : null}

              {currentPlayer ? (
                <SectionCard
                  title='Le mie partite'
                  description='Partite future create da te o a cui partecipi nel tenant corrente.'
                >
                  <MyMatches
                    matches={myMatches}
                    currentPlayerId={currentPlayer.id}
                    onOpen={handleOpenShared}
                    onShare={handleShare}
                    onLeave={(match) => void handleLeave(match)}
                    onEdit={openManagePanel}
                    onCancel={(match) => void handleCancel(match)}
                  />
                </SectionCard>
              ) : (
                <SectionCard title='Le mie partite' description='Questa sezione appare appena ti riconosci con il profilo play.'>
                  <div className='surface-muted flex items-center gap-3'>
                    <UsersRound size={18} className='text-cyan-700' />
                    <p className='text-sm text-slate-700'>Identificati dal pulsante `Unisciti` o `Crea nuova partita` per vedere il tuo spazio personale.</p>
                  </div>
                </SectionCard>
              )}
            </>
          )}
        </div>

        <JoinConfirmModal
          open={Boolean(pendingAction)}
          tenantSlug={tenantSlug}
          title={pendingAction?.kind === 'create' ? 'Identificati per creare una nuova partita' : 'Identificati per unirti alla partita'}
          description={pendingAction?.kind === 'create'
            ? 'Salvo il tuo profilo play sul club corrente e tengo pronta la selezione di giorno, campo, orario e livello.'
            : 'Ti riconosco sul tenant corrente del club prima di collegarti alla partita condivisa o aperta in bacheca.'}
          onClose={() => setPendingAction(null)}
          onSuccess={handleIdentifySuccess}
        />
      </div>
    </div>
  );
}