import { ArrowLeft, Share2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { AppBrand } from '../components/AppBrand';
import { LoadingBlock } from '../components/LoadingBlock';
import { MatchCard } from '../components/play/MatchCard';
import { JoinConfirmModal } from '../components/play/JoinConfirmModal';
import { getPlaySession, getPlaySharedMatch, joinPlayMatch } from '../services/playApi';
import type { PlayMatchSummary, PlayPlayerSummary } from '../types';
import { getTenantSlugFromSearchParams, normalizeTenantSlug } from '../utils/tenantContext';
import { buildClubPlayPath, buildPlayMatchPath } from '../utils/play';

export function SharedMatchPage() {
  const { clubSlug, shareToken } = useParams();
  const [searchParams] = useSearchParams();
  const tenantSlug = normalizeTenantSlug(clubSlug) || getTenantSlugFromSearchParams(searchParams) || null;
  const [currentPlayer, setCurrentPlayer] = useState<PlayPlayerSummary | null>(null);
  const [match, setMatch] = useState<PlayMatchSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'success' | 'error'; message: string } | null>(null);
  const [identifyOpen, setIdentifyOpen] = useState(false);

  useEffect(() => {
    if (!tenantSlug || !shareToken) {
      setLoading(false);
      setFeedback({ tone: 'error', message: 'Link partita non valido per il club corrente.' });
      return;
    }

    void loadSharedSurface(tenantSlug, shareToken);
  }, [shareToken, tenantSlug]);

  async function loadSharedSurface(resolvedTenantSlug: string, resolvedShareToken: string) {
    setLoading(true);
    try {
      const [session, detail] = await Promise.all([
        getPlaySession(resolvedTenantSlug),
        getPlaySharedMatch(resolvedShareToken, resolvedTenantSlug),
      ]);
      setCurrentPlayer(session.player || detail.player || null);
      setMatch(detail.match);
    } catch {
      setFeedback({ tone: 'error', message: 'Non riesco a caricare la partita condivisa.' });
    } finally {
      setLoading(false);
    }
  }

  async function performJoin(player = currentPlayer) {
    if (!tenantSlug || !match || !player) {
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
      await loadSharedSurface(tenantSlug, match.share_token);
    } catch (error) {
      setFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : 'Non riesco a completare il join della partita condivisa.',
      });
    }
  }

  function handleJoinAttempt() {
    if (!currentPlayer) {
      setIdentifyOpen(true);
      return;
    }

    void performJoin(currentPlayer);
  }

  async function handleShare() {
    if (!tenantSlug || !match) {
      return;
    }

    const absoluteUrl = typeof window !== 'undefined'
      ? `${window.location.origin}${buildPlayMatchPath(tenantSlug, match.share_token)}`
      : buildPlayMatchPath(tenantSlug, match.share_token);

    try {
      await navigator.clipboard.writeText(absoluteUrl);
      setFeedback({ tone: 'success', message: 'Link partita copiato negli appunti.' });
    } catch {
      setFeedback({ tone: 'info', message: `Link pronto per la condivisione: ${absoluteUrl}` });
    }
  }

  async function handleIdentifySuccess(player: PlayPlayerSummary) {
    setCurrentPlayer(player);
    setIdentifyOpen(false);
    if (tenantSlug && shareToken) {
      await loadSharedSurface(tenantSlug, shareToken);
    }
    if (match) {
      await performJoin(player);
      return;
    }
    setFeedback({ tone: 'success', message: `Profilo play attivo. Ora il flusso shared match ti riconosce come ${player.profile_name}.` });
  }

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='page-shell max-w-4xl'>
        <div className='rounded-[28px] border border-cyan-400/20 bg-slate-950/80 p-6 text-white shadow-soft'>
          <AppBrand light label='Shared match' />
          <h1 className='mt-4 text-3xl font-bold tracking-tight text-white'>Partita condivisa</h1>
          <p className='mt-3 text-sm leading-6 text-slate-300'>Questa pagina nasce dal link di condivisione di una partita aperta del club. Il player riconosciuto puo proseguire subito, quello anonimo entra con onboarding leggero.</p>
        </div>

        <div className='mt-6 space-y-6'>
          {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

          {currentPlayer ? (
            <AlertBanner tone='success'>Profilo attivo: <strong>{currentPlayer.profile_name}</strong>.</AlertBanner>
          ) : (
            <AlertBanner tone='info'>Per unirti da questa pagina devi prima identificarti sul tenant corrente del club.</AlertBanner>
          )}

          {loading ? <LoadingBlock label='Carico la partita condivisa…' /> : null}

          {!loading && match ? (
            <MatchCard
              match={match}
              onPrimaryAction={match.joined_by_current_player ? undefined : handleJoinAttempt}
              primaryActionLabel={currentPlayer ? 'Unisciti' : 'Identificati per unirti'}
              onShare={handleShare}
              testId='play-shared-match-card'
            />
          ) : null}

          {tenantSlug ? (
            <div className='flex flex-col gap-3 sm:flex-row'>
              <Link className='btn-secondary' to={buildClubPlayPath(tenantSlug)}>
                <ArrowLeft size={16} />
                <span>Torna alla bacheca play</span>
              </Link>
              {match ? (
                <button type='button' className='btn-secondary' onClick={handleShare}>
                  <Share2 size={16} />
                  <span>Condividi ancora</span>
                </button>
              ) : null}
            </div>
          ) : null}
        </div>

        {tenantSlug ? (
          <JoinConfirmModal
            open={identifyOpen}
            tenantSlug={tenantSlug}
            title='Identificati per proseguire dal link condiviso'
            description='Salvo il tuo profilo play sul club corrente prima di completare il flusso community della partita condivisa.'
            onClose={() => setIdentifyOpen(false)}
            onSuccess={handleIdentifySuccess}
          />
        ) : null}
      </div>
    </div>
  );
}