import { AxiosError } from 'axios';
import { ArrowLeft } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { LoadingBlock } from '../components/LoadingBlock';
import { PageBrandBar } from '../components/PageBrandBar';
import { CommunityMatchinnBrand } from '../components/play/CommunityMatchinnBrand';
import { MatchCard } from '../components/play/MatchCard';
import { PlayShareDialog } from '../components/play/PlayShareDialog';
import { JoinConfirmModal } from '../components/play/JoinConfirmModal';
import { getPublicConfig } from '../services/publicApi';
import { getPlaySession, getPlaySharedMatch, joinPlayMatch } from '../services/playApi';
import type { PlayMatchSummary, PlayPlayerSummary } from '../types';
import { getTenantSlugFromSearchParams, normalizeTenantSlug } from '../utils/tenantContext';
import {
  buildAbsolutePlayMatchUrl,
  buildClubPlayPath,
  buildPlayMatchPath,
  buildPlayMatchShareText,
  buildPlayMatchWhatsAppUrl,
  rememberClubPublicName,
  resolveClubDisplayName,
} from '../utils/play';

function getApiErrorMessage(error: unknown, fallback: string) {
  const requestError = error as AxiosError<{ detail?: string }>;
  return requestError?.response?.data?.detail || (error instanceof Error ? error.message : fallback);
}

export function SharedMatchPage() {
  const { clubSlug, shareToken } = useParams();
  const [searchParams] = useSearchParams();
  const tenantSlug = normalizeTenantSlug(clubSlug) || getTenantSlugFromSearchParams(searchParams) || null;
  const [currentPlayer, setCurrentPlayer] = useState<PlayPlayerSummary | null>(null);
  const [match, setMatch] = useState<PlayMatchSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'success' | 'error'; message: string } | null>(null);
  const [identifyOpen, setIdentifyOpen] = useState(false);
  const [clubPublicName, setClubPublicName] = useState<string | null>(null);
  const [clubTimezone, setClubTimezone] = useState<string | null>(null);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const clubDisplayName = tenantSlug ? resolveClubDisplayName(tenantSlug, clubPublicName) : null;

  useEffect(() => {
    setClubPublicName(null);
    setClubTimezone(null);
    setShareDialogOpen(false);

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
      const [session, detail, publicConfig] = await Promise.all([
        getPlaySession(resolvedTenantSlug),
        getPlaySharedMatch(resolvedShareToken, resolvedTenantSlug),
        getPublicConfig(resolvedTenantSlug).catch(() => null),
      ]);
      setCurrentPlayer(session.player || detail.player || null);
      setMatch(detail.match);
      if (publicConfig) {
        rememberClubPublicName(resolvedTenantSlug, publicConfig.public_name);
        setClubPublicName(publicConfig.public_name);
        setClubTimezone(publicConfig.timezone);
      }
    } catch (error) {
      setFeedback({ tone: 'error', message: getApiErrorMessage(error, 'Non riesco a caricare la partita condivisa.') });
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
      const resolvedShareToken = match.share_token || shareToken;
      if (!resolvedShareToken) {
        throw new Error('Link partita non disponibile');
      }
      setFeedback({
        tone: response.action === 'COMPLETED' ? 'success' : 'info',
        message: response.booking
          ? `${response.message} Riferimento prenotazione ${response.booking.public_reference}.`
          : response.message,
      });
      await loadSharedSurface(tenantSlug, resolvedShareToken);
    } catch (error) {
      setFeedback({
        tone: 'error',
        message: getApiErrorMessage(error, 'Non riesco a completare il join della partita condivisa.'),
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
    if (!tenantSlug || !match?.share_token) {
      return;
    }
    setShareDialogOpen(true);
  }

  async function handleIdentifySuccess(player: PlayPlayerSummary) {
    setCurrentPlayer(player);
    setIdentifyOpen(false);
    if (tenantSlug && shareToken) {
      const resolvedShareToken = match?.share_token || shareToken;
      await loadSharedSurface(tenantSlug, resolvedShareToken);
    }
    if (match) {
      await performJoin(player);
      return;
    }
    setFeedback({ tone: 'success', message: `Profilo play attivo. Ora il flusso shared match ti riconosce come ${player.profile_name}.` });
  }

  const shareUrl = useMemo(() => {
    if (!tenantSlug || !match?.share_token) {
      return null;
    }
    return buildAbsolutePlayMatchUrl(tenantSlug, match.share_token);
  }, [match?.share_token, tenantSlug]);

  const shareText = useMemo(() => {
    if (!match || !shareUrl) {
      return null;
    }
    return buildPlayMatchShareText({
      startAt: match.start_at,
      endAt: match.end_at,
      levelRequested: match.level_requested,
      participantNames: match.participants.map((participant) => participant.profile_name),
      clubName: clubDisplayName,
      shareUrl,
      timeZone: clubTimezone,
    });
  }, [clubDisplayName, clubTimezone, match, shareUrl]);

  const whatsAppUrl = useMemo(() => {
    if (!match || !shareUrl) {
      return null;
    }
    return buildPlayMatchWhatsAppUrl({
      startAt: match.start_at,
      endAt: match.end_at,
      levelRequested: match.level_requested,
      participantNames: match.participants.map((participant) => participant.profile_name),
      clubName: clubDisplayName,
      shareUrl,
      timeZone: clubTimezone,
    });
  }, [clubDisplayName, clubTimezone, match, shareUrl]);

  const canJoinMatch = Boolean(match && match.status === 'OPEN' && !match.joined_by_current_player);

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='page-shell max-w-4xl'>
        <div className='rounded-[28px] border border-cyan-400/20 bg-slate-950/80 p-6 text-white shadow-soft'>
          <PageBrandBar
            className='mb-6'
            actions={tenantSlug ? (
              <>
                <Link className='hero-action-secondary' to={buildClubPlayPath(tenantSlug)}>
                  <ArrowLeft size={16} />
                  <span>Torna a Partite aperte</span>
                </Link>
                <Link className='hero-action-secondary' to='/'>
                  <span>Torna alla home</span>
                </Link>
              </>
            ) : (
              <Link className='hero-action-secondary' to='/'>
                <span>Torna alla home</span>
              </Link>
            )}
          />
          <CommunityMatchinnBrand clubName={clubDisplayName} />
          <h1 className='mt-4 text-3xl font-bold tracking-tight text-white'>Partita condivisa</h1>
          <p className='mt-3 text-sm leading-6 text-slate-300'>Questo link apre una partita gia condivisa del club. Se sei gia riconosciuto puoi unirti subito, altrimenti attivi il profilo e torni qui senza perdere il contesto.</p>
        </div>

        <div className='mt-6 space-y-6'>
          {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

          {currentPlayer ? (
            <AlertBanner tone='success'>Profilo attivo: <strong>{currentPlayer.profile_name}</strong>.</AlertBanner>
          ) : (
            <AlertBanner tone='info'>Per unirti da questa pagina devi prima attivare il tuo profilo sul club corrente.</AlertBanner>
          )}

          {!loading && match?.status === 'FULL' && !match.joined_by_current_player ? (
            <AlertBanner tone='info'>Questa partita e gia completa. Puoi ancora condividerla su WhatsApp, ma non e piu disponibile per il join.</AlertBanner>
          ) : null}

          {loading ? <LoadingBlock label='Carico la partita condivisa…' /> : null}

          {!loading && match ? (
            <MatchCard
              match={match}
              onPrimaryAction={canJoinMatch ? handleJoinAttempt : undefined}
              primaryActionLabel={currentPlayer ? 'Unisciti' : 'Identificati per unirti'}
              onShare={handleShare}
              testId='play-shared-match-card'
            />
          ) : null}

        </div>

        {tenantSlug ? (
          <JoinConfirmModal
            open={identifyOpen}
            tenantSlug={tenantSlug}
            title='Identificati per proseguire dal link condiviso'
            description='Salvo il tuo profilo sul club corrente prima di completare il join della partita condivisa.'
            onClose={() => setIdentifyOpen(false)}
            onSuccess={handleIdentifySuccess}
          />
        ) : null}

        {shareDialogOpen && shareUrl && shareText && whatsAppUrl ? (
          <PlayShareDialog
            open={shareDialogOpen}
            title='Condividi questa partita'
            description='Puoi copiare il link oppure aprire WhatsApp con il testo gia pronto.'
            shareUrl={shareUrl}
            shareText={shareText}
            whatsAppUrl={whatsAppUrl}
            onClose={() => setShareDialogOpen(false)}
          />
        ) : null}
      </div>
    </div>
  );
}