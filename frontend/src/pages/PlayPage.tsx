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
import { getPlayMatches, getPlaySession } from '../services/playApi';
import type { PlayMatchSummary, PlayMatchesResponse, PlayPlayerSummary } from '../types';
import { getTenantSlugFromSearchParams, normalizeTenantSlug, withTenantPath } from '../utils/tenantContext';
import { buildClubPlayPath, buildPlayMatchPath } from '../utils/play';

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
    setFeedback(null);
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

  function handleJoin(match: PlayMatchSummary) {
    if (!currentPlayer) {
      requireIdentity({ kind: 'join', match });
      return;
    }

    setFeedback({
      tone: 'info',
      message: `Profilo attivo per ${currentPlayer.profile_name}. Il join definitivo della partita sara collegato agli endpoint write del prossimo step backend.`,
    });
  }

  function handleCreateIntent(intent: PlayCreateIntent) {
    if (!currentPlayer) {
      requireIdentity({ kind: 'create', intent });
      return;
    }

    setFeedback({
      tone: 'info',
      message: `Hai preparato la partita su ${intent.courtName} alle ${intent.startTime}. La creazione definitiva verra attivata quando il modulo write play sara disponibile.`,
    });
  }

  async function handleIdentifySuccess(player: PlayPlayerSummary) {
    if (!tenantSlug) {
      return;
    }

    const action = pendingAction;
    setPendingAction(null);
    setCurrentPlayer(player);
    await loadPlaySurface(tenantSlug);

    if (!action) {
      setFeedback({ tone: 'success', message: `Profilo play attivo. Bentornato ${player.profile_name}.` });
      return;
    }

    if (action.kind === 'join') {
      setFeedback({
        tone: 'success',
        message: `Profilo play attivo. Ora puoi completare il join della partita su ${action.match.court_name || 'questo campo'} quando il backend join sara attivo.`,
      });
      return;
    }

    setFeedback({
      tone: 'success',
      message: `Profilo play attivo. Hai gia preparato la partita delle ${action.intent.startTime} su ${action.intent.courtName}.`,
    });
  }

  async function handleShare(match: PlayMatchSummary) {
    if (!tenantSlug) {
      return;
    }

    const sharePath = buildPlayMatchPath(tenantSlug, match.id);
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
    navigate(buildPlayMatchPath(tenantSlug, match.id));
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

              <SectionCard
                title='Crea nuova partita'
                description='Scegli giorno, slot libero reale, campo e livello. Il motore slot e gia tenant-aware e riusa la disponibilita esistente del club.'
              >
                <CreateMatchForm tenantSlug={tenantSlug} onCreateIntent={handleCreateIntent} />
              </SectionCard>

              {currentPlayer ? (
                <SectionCard
                  title='Le mie partite'
                  description='Partite future create da te o a cui partecipi nel tenant corrente.'
                >
                  <MyMatches matches={myMatches} onOpen={handleOpenShared} onShare={handleShare} />
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