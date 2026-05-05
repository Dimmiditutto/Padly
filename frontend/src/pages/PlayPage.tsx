import { AxiosError } from 'axios';
import { ArrowLeft, BellRing, UsersRound } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { LoadingBlock } from '../components/LoadingBlock';
import { PageBrandBar } from '../components/PageBrandBar';
import { SectionCard } from '../components/SectionCard';
import { CommunityMatchinnBrand } from '../components/play/CommunityMatchinnBrand';
import { CreateMatchForm, type PlayCreateIntent } from '../components/play/CreateMatchForm';
import { JoinConfirmModal } from '../components/play/JoinConfirmModal';
import { MatchBoard } from '../components/play/MatchBoard';
import { MyMatches } from '../components/play/MyMatches';
import { PlayShareDialog } from '../components/play/PlayShareDialog';
import { getPublicConfig } from '../services/publicApi';
import {
  cancelPlayMatch,
  createPlayMatch,
  getPlayMatches,
  getPlaySession,
  joinPlayMatch,
  leavePlayMatch,
  markPlayNotificationRead,
  registerPlayPushSubscription,
  revokePlayMatchShareToken,
  revokePlayPushSubscription,
  rotatePlayMatchShareToken,
  searchPlayMatchPlayers,
  startPlayBookingCheckout,
  updatePlayMatch,
  updatePlayNotificationPreferences,
} from '../services/playApi';
import type {
  PaymentProvider,
  PlayLevel,
  PlayBookingPaymentAction,
  PlayBookingSummary,
  PlayMatchSummary,
  PlayMatchesResponse,
  PlayNotificationPreferenceSummary,
  PlayNotificationSettings,
  PlayPlayerSummary,
  PublicConfig,
} from '../types';
import { getBrowserPlayPushEndpoint, isPlayPushSupported, subscribeBrowserToPlayPush, unsubscribeBrowserFromPlayPush } from '../utils/playPush';
import { getTenantSlugFromSearchParams, normalizeTenantSlug, withTenantPath } from '../utils/tenantContext';
import {
  buildAbsolutePlayMatchUrl,
  buildClubPlayPath,
  buildPlayAccessPath,
  buildPlayMatchPath,
  buildPlayMatchShareText,
  buildPlayMatchWhatsAppUrl,
  PLAY_LEVEL_OPTIONS,
  rememberClubPublicName,
  resolveClubDisplayName,
} from '../utils/play';

type FeedbackTone = 'info' | 'success' | 'warning' | 'error';
type InlineFeedback = { tone: FeedbackTone; message: string };
type PlayMatchLevelFilter = PlayLevel | 'ALL';
type PlayMatchDateOption = { value: string; label: string };
type PlayMatchFilters = { date: string; level: PlayMatchLevelFilter };

type PendingAction =
  | { kind: 'join'; match: PlayMatchSummary }
  | { kind: 'create'; intent: PlayCreateIntent };

type PendingPlayPayment = {
  booking: PlayBookingSummary;
  paymentAction: PlayBookingPaymentAction;
};

function paymentProviderLabel(provider: PaymentProvider) {
  if (provider === 'STRIPE') {
    return 'Stripe';
  }
  if (provider === 'PAYPAL') {
    return 'PayPal';
  }
  return 'Pagamento online';
}

function getApiErrorMessage(error: unknown, fallback: string) {
  const requestError = error as AxiosError<{ detail?: string }>;
  return requestError?.response?.data?.detail || (error instanceof Error ? error.message : fallback);
}

function getDateParts(dateValue: Date | string, timeZone?: string | null) {
  const formatter = new Intl.DateTimeFormat('it-IT', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...(timeZone ? { timeZone } : {}),
  });
  const parts = formatter.formatToParts(typeof dateValue === 'string' ? new Date(dateValue) : dateValue);
  return {
    year: parts.find((part) => part.type === 'year')?.value || '0000',
    month: parts.find((part) => part.type === 'month')?.value || '01',
    day: parts.find((part) => part.type === 'day')?.value || '01',
  };
}

function getMatchDateKey(dateValue: Date | string, timeZone?: string | null) {
  const { year, month, day } = getDateParts(dateValue, timeZone);
  return `${year}-${month}-${day}`;
}

function formatMatchDateOptionLabel(dateValue: string, timeZone?: string | null) {
  const label = new Intl.DateTimeFormat('it-IT', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    ...(timeZone ? { timeZone } : {}),
  }).format(new Date(dateValue));
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function compareMatchesByStartAt(left: PlayMatchSummary, right: PlayMatchSummary) {
  return new Date(left.start_at).getTime() - new Date(right.start_at).getTime();
}

function sortOpenPlayMatches(matches: PlayMatchSummary[]) {
  return [...matches].sort((left, right) => (
    (right.participant_count - left.participant_count)
    || compareMatchesByStartAt(left, right)
    || (new Date(left.created_at).getTime() - new Date(right.created_at).getTime())
  ));
}

function sortMyPlayMatches(matches: PlayMatchSummary[]) {
  return [...matches].sort((left, right) => (
    compareMatchesByStartAt(left, right)
    || (right.participant_count - left.participant_count)
    || (new Date(left.created_at).getTime() - new Date(right.created_at).getTime())
  ));
}

function filterPlayMatches(matches: PlayMatchSummary[], filters: PlayMatchFilters, timeZone?: string | null) {
  return matches.filter((match) => {
    if (filters.date && getMatchDateKey(match.start_at, timeZone) !== filters.date) {
      return false;
    }
    if (filters.level !== 'ALL' && match.level_requested !== filters.level) {
      return false;
    }
    return true;
  });
}

function buildPlayMatchDateOptions(matches: PlayMatchSummary[], timeZone?: string | null): PlayMatchDateOption[] {
  const seen = new Set<string>();
  return matches.flatMap((match) => {
    const value = getMatchDateKey(match.start_at, timeZone);
    if (seen.has(value)) {
      return [];
    }
    seen.add(value);
    return [{ value, label: formatMatchDateOptionLabel(match.start_at, timeZone) }];
  });
}

function isMatchWithinNextSevenDays(dateValue: string, timeZone?: string | null) {
  const today = new Date();
  const windowEnd = new Date(today);
  windowEnd.setDate(windowEnd.getDate() + 6);
  const matchKey = getMatchDateKey(dateValue, timeZone);
  return matchKey >= getMatchDateKey(today, timeZone) && matchKey <= getMatchDateKey(windowEnd, timeZone);
}

function formatMatchCount(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function PlayMatchFilterBar({
  sectionLabel,
  dateOptions,
  dateFilter,
  levelFilter,
  onDateChange,
  onLevelChange,
}: {
  sectionLabel: string;
  dateOptions: PlayMatchDateOption[];
  dateFilter: string;
  levelFilter: PlayMatchLevelFilter;
  onDateChange: (value: string) => void;
  onLevelChange: (value: PlayMatchLevelFilter) => void;
}) {
  return (
    <div className='surface-muted grid gap-3 lg:grid-cols-2'>
      <label className='block'>
        <span className='mb-2 block text-sm font-medium text-slate-700'>{`Data ${sectionLabel}`}</span>
        <select
          aria-label={`Data ${sectionLabel}`}
          className='text-input min-h-11 py-2'
          value={dateFilter}
          onChange={(event) => onDateChange(event.target.value)}
        >
          <option value=''>Tutte le date</option>
          {dateOptions.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>

      <label className='block'>
        <span className='mb-2 block text-sm font-medium text-slate-700'>{`Livello ${sectionLabel}`}</span>
        <select
          aria-label={`Livello ${sectionLabel}`}
          className='text-input min-h-11 py-2'
          value={levelFilter}
          onChange={(event) => onLevelChange(event.target.value as PlayMatchLevelFilter)}
        >
          <option value='ALL'>Tutti i livelli</option>
          {PLAY_LEVEL_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>
    </div>
  );
}

export function PlayPage() {
  const { clubSlug } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const tenantSlug = normalizeTenantSlug(clubSlug) || getTenantSlugFromSearchParams(searchParams) || null;
  const [playData, setPlayData] = useState<PlayMatchesResponse | null>(null);
  const [clubConfig, setClubConfig] = useState<PublicConfig | null>(null);
  const [currentPlayer, setCurrentPlayer] = useState<PlayPlayerSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ tone: FeedbackTone; message: string } | null>(null);
  const [notificationPreferenceFeedback, setNotificationPreferenceFeedback] = useState<InlineFeedback | null>(null);
  const [pushFeedback, setPushFeedback] = useState<InlineFeedback | null>(null);
  const [notificationItemFeedback, setNotificationItemFeedback] = useState<{ notificationId: string; tone: FeedbackTone; message: string } | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [pendingPlayPayment, setPendingPlayPayment] = useState<PendingPlayPayment | null>(null);
  const [startingCheckoutProvider, setStartingCheckoutProvider] = useState<PaymentProvider | null>(null);
  const [suggestedMatches, setSuggestedMatches] = useState<PlayMatchSummary[]>([]);
  const [pendingCreateIntent, setPendingCreateIntent] = useState<PlayCreateIntent | null>(null);
  const [managedMatch, setManagedMatch] = useState<PlayMatchSummary | null>(null);
  const [managedLevel, setManagedLevel] = useState<PlayLevel>('NO_PREFERENCE');
  const [managedNote, setManagedNote] = useState('');
  const [savingManageAction, setSavingManageAction] = useState(false);
  const [shareMatch, setShareMatch] = useState<PlayMatchSummary | null>(null);
  const [notificationSettings, setNotificationSettings] = useState<PlayNotificationSettings | null>(null);
  const [notificationDraft, setNotificationDraft] = useState<PlayNotificationPreferenceSummary | null>(null);
  const [savingNotificationPreferences, setSavingNotificationPreferences] = useState(false);
  const [updatingPushSubscription, setUpdatingPushSubscription] = useState(false);
  const [readingNotificationId, setReadingNotificationId] = useState<string | null>(null);
  const [searchingPlayersMatchId, setSearchingPlayersMatchId] = useState<string | null>(null);
  const [browserPushEndpoint, setBrowserPushEndpoint] = useState<string | null>(null);
  const [openMatchesExpanded, setOpenMatchesExpanded] = useState(false);
  const [myMatchesExpanded, setMyMatchesExpanded] = useState(false);
  const [openMatchDateFilter, setOpenMatchDateFilter] = useState('');
  const [openMatchLevelFilter, setOpenMatchLevelFilter] = useState<PlayMatchLevelFilter>('ALL');
  const [myMatchDateFilter, setMyMatchDateFilter] = useState('');
  const [myMatchLevelFilter, setMyMatchLevelFilter] = useState<PlayMatchLevelFilter>('ALL');
  const browserSupportsPush = useMemo(() => isPlayPushSupported(), []);

  useEffect(() => {
    if (!tenantSlug) {
      setLoading(false);
      setClubConfig(null);
      setPendingPlayPayment(null);
      setFeedback({ tone: 'error', message: 'Tenant play non valido. Apri la pagina da un club specifico.' });
      return;
    }

    setClubConfig((prev) => prev?.tenant_slug === tenantSlug ? prev : null);
    setPendingPlayPayment(null);
    void loadPlaySurface(tenantSlug);
  }, [tenantSlug]);

  useEffect(() => {
    let cancelled = false;

    if (!browserSupportsPush || !currentPlayer || !tenantSlug) {
      setBrowserPushEndpoint(null);
      return () => {
        cancelled = true;
      };
    }

    void getBrowserPlayPushEndpoint()
      .then((endpoint) => {
        if (!cancelled) {
          setBrowserPushEndpoint(endpoint);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setBrowserPushEndpoint(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [browserSupportsPush, currentPlayer, tenantSlug]);

  useEffect(() => {
    setOpenMatchesExpanded(false);
    setMyMatchesExpanded(false);
    setOpenMatchDateFilter('');
    setOpenMatchLevelFilter('ALL');
    setMyMatchDateFilter('');
    setMyMatchLevelFilter('ALL');
  }, [tenantSlug]);

  const openMatches = useMemo(() => playData?.open_matches || [], [playData]);
  const myMatches = useMemo(() => playData?.my_matches || [], [playData]);
  const playTimezone = clubConfig?.timezone || null;
  const sortedOpenMatches = useMemo(() => sortOpenPlayMatches(openMatches), [openMatches]);
  const sortedMyMatches = useMemo(() => sortMyPlayMatches(myMatches), [myMatches]);
  const openMatchDateOptions = useMemo(() => buildPlayMatchDateOptions(sortedOpenMatches, playTimezone), [sortedOpenMatches, playTimezone]);
  const myMatchDateOptions = useMemo(() => buildPlayMatchDateOptions(sortedMyMatches, playTimezone), [sortedMyMatches, playTimezone]);
  const filteredOpenMatches = useMemo(() => filterPlayMatches(sortedOpenMatches, {
    date: openMatchDateFilter,
    level: openMatchLevelFilter,
  }, playTimezone), [sortedOpenMatches, openMatchDateFilter, openMatchLevelFilter, playTimezone]);
  const filteredMyMatches = useMemo(() => filterPlayMatches(sortedMyMatches, {
    date: myMatchDateFilter,
    level: myMatchLevelFilter,
  }, playTimezone), [sortedMyMatches, myMatchDateFilter, myMatchLevelFilter, playTimezone]);
  const openMatchesReadyToComplete = useMemo(() => openMatches.filter((match) => match.participant_count === 3).length, [openMatches]);
  const myMatchesNextSevenDays = useMemo(() => myMatches.filter((match) => isMatchWithinNextSevenDays(match.start_at, playTimezone)), [myMatches, playTimezone]);
  const openMatchesSummary = openMatches.length > 0
    ? `${formatMatchCount(openMatchesReadyToComplete, 'partita', 'partite')} su ${openMatches.length} da completare`
    : 'Nessuna partita da completare';
  const myMatchesSummary = !currentPlayer
    ? 'Attiva il profilo community'
    : myMatchesNextSevenDays.length > 0
      ? `Sei dentro a ${formatMatchCount(myMatchesNextSevenDays.length, 'partita', 'partite')} nei prossimi 7 giorni`
      : 'Nessuna partita nei prossimi 7 giorni';

  useEffect(() => {
    if (openMatchDateFilter && !openMatchDateOptions.some((option) => option.value === openMatchDateFilter)) {
      setOpenMatchDateFilter('');
    }
  }, [openMatchDateFilter, openMatchDateOptions]);

  useEffect(() => {
    if (myMatchDateFilter && !myMatchDateOptions.some((option) => option.value === myMatchDateFilter)) {
      setMyMatchDateFilter('');
    }
  }, [myMatchDateFilter, myMatchDateOptions]);

  function applyNotificationSettings(nextSettings: PlayNotificationSettings | null) {
    setNotificationSettings(nextSettings);
    setNotificationDraft(nextSettings?.preferences || null);
  }

  async function loadPlaySurface(resolvedTenantSlug: string) {
    setLoading(true);
    try {
      const [session, matches, publicConfig] = await Promise.all([
        getPlaySession(resolvedTenantSlug),
        getPlayMatches(resolvedTenantSlug),
        getPublicConfig(resolvedTenantSlug).catch(() => null),
      ]);
      setCurrentPlayer(session.player || matches.player || null);
      setPlayData(matches);
      if (publicConfig) {
        rememberClubPublicName(resolvedTenantSlug, publicConfig.public_name);
        setClubConfig(publicConfig);
      }
      setPendingPlayPayment(
        matches.pending_payment
          ? {
            booking: matches.pending_payment.booking,
            paymentAction: matches.pending_payment.payment_action,
          }
          : null,
      );
      applyNotificationSettings(session.notification_settings || null);
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
      if (response.booking && response.payment_action?.required) {
        setPendingPlayPayment({ booking: response.booking, paymentAction: response.payment_action });
      } else {
        setPendingPlayPayment(null);
      }
      setFeedback({
        tone: response.payment_action?.required ? 'warning' : response.action === 'COMPLETED' ? 'success' : 'info',
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

  async function handleStartPlayCheckout(provider?: PaymentProvider) {
    if (!tenantSlug || !pendingPlayPayment) {
      return;
    }

    const selectedProvider = provider
      || pendingPlayPayment.paymentAction.selected_provider
      || (pendingPlayPayment.paymentAction.available_providers.length === 1 ? pendingPlayPayment.paymentAction.available_providers[0] : null);

    if (!selectedProvider) {
      setFeedback({ tone: 'error', message: 'Seleziona un provider per completare la caparra community.' });
      return;
    }

    setStartingCheckoutProvider(selectedProvider);
    try {
      const response = await startPlayBookingCheckout(
        pendingPlayPayment.booking.id,
        { provider: selectedProvider },
        tenantSlug,
      );
      window.location.assign(response.checkout_url);
    } catch (error) {
      setFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : 'Non riesco ad avviare il checkout della caparra community.',
      });
    } finally {
      setStartingCheckoutProvider(null);
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

  async function handleRotateShareToken(match: PlayMatchSummary) {
    if (!tenantSlug || !currentPlayer || savingManageAction) {
      return;
    }
    setSavingManageAction(true);
    try {
      const response = await rotatePlayMatchShareToken(match.id, tenantSlug);
      setFeedback({ tone: 'success', message: response.message });
      await loadPlaySurface(tenantSlug);
    } catch (error) {
      setFeedback({
        tone: 'error',
        message: getApiErrorMessage(error, 'Non riesco a rigenerare il link partita.'),
      });
    } finally {
      setSavingManageAction(false);
    }
  }

  async function handleRevokeShareToken(match: PlayMatchSummary) {
    if (!tenantSlug || !currentPlayer || savingManageAction) {
      return;
    }
    if (!window.confirm('Confermi la disattivazione del link condiviso?')) {
      return;
    }
    setSavingManageAction(true);
    try {
      const response = await revokePlayMatchShareToken(match.id, tenantSlug);
      setFeedback({ tone: 'warning', message: response.message });
      await loadPlaySurface(tenantSlug);
    } catch (error) {
      setFeedback({
        tone: 'error',
        message: getApiErrorMessage(error, 'Non riesco a disattivare il link partita.'),
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
        message: getApiErrorMessage(error, 'Non riesco a creare la partita play.'),
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
    if (!match.share_token) {
      return;
    }
    setShareMatch(match);
  }

  async function handleSearchPlayers(match: PlayMatchSummary) {
    if (!tenantSlug || searchingPlayersMatchId) {
      return;
    }

    setSearchingPlayersMatchId(match.id);
    try {
      const response = await searchPlayMatchPlayers(match.id, tenantSlug);
      setFeedback({
        tone: response.cooldown_remaining_seconds > 0 ? 'warning' : response.notifications_created > 0 ? 'success' : 'info',
        message: response.message,
      });
    } catch (error) {
      setFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : 'Non riesco ad avviare la ricerca giocatori per questo match.',
      });
    } finally {
      setSearchingPlayersMatchId(null);
    }
  }

  async function handleSaveNotificationPreferences() {
    if (!tenantSlug || !currentPlayer || !notificationDraft || savingNotificationPreferences) {
      return;
    }

    setNotificationPreferenceFeedback(null);
    setSavingNotificationPreferences(true);
    try {
      const response = await updatePlayNotificationPreferences(notificationDraft, tenantSlug);
      applyNotificationSettings(response.settings);
      setNotificationPreferenceFeedback({ tone: 'success', message: response.message });
    } catch (error) {
      setNotificationPreferenceFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : 'Non riesco a salvare le preferenze notifiche.',
      });
    } finally {
      setSavingNotificationPreferences(false);
    }
  }

  async function handleEnablePush() {
    if (!tenantSlug || !currentPlayer || !notificationSettings || updatingPushSubscription) {
      return;
    }
    setPushFeedback(null);
    if (!browserSupportsPush) {
      setPushFeedback({ tone: 'error', message: 'Questo browser non supporta le web push.' });
      return;
    }
    if (!notificationSettings.push.public_vapid_key) {
      setPushFeedback({ tone: 'warning', message: 'Web push non configurate lato server: manca la chiave pubblica VAPID.' });
      return;
    }

    setUpdatingPushSubscription(true);
    try {
      const payload = await subscribeBrowserToPlayPush(
        notificationSettings.push.public_vapid_key,
        notificationSettings.push.service_worker_path,
      );
      const response = await registerPlayPushSubscription(payload, tenantSlug);
      applyNotificationSettings(response.settings);
      setBrowserPushEndpoint(payload.endpoint);
      setPushFeedback({ tone: 'success', message: response.message });
    } catch (error) {
      setPushFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : 'Non riesco ad attivare le web push.',
      });
    } finally {
      setUpdatingPushSubscription(false);
    }
  }

  async function handleMarkNotificationRead(notificationId: string) {
    if (!tenantSlug || !currentPlayer || readingNotificationId) {
      return;
    }

    setNotificationItemFeedback(null);
    setReadingNotificationId(notificationId);
    try {
      const response = await markPlayNotificationRead(notificationId, tenantSlug);
      applyNotificationSettings(response.settings);
      setNotificationItemFeedback({ notificationId, tone: 'success', message: response.message });
    } catch (error) {
      setNotificationItemFeedback({
        notificationId,
        tone: 'error',
        message: error instanceof Error ? error.message : 'Non riesco a marcare la notifica come letta.',
      });
    } finally {
      setReadingNotificationId(null);
    }
  }

  async function handleDisablePush() {
    if (!tenantSlug || !currentPlayer || !notificationSettings || updatingPushSubscription) {
      return;
    }

    setPushFeedback(null);
    setUpdatingPushSubscription(true);
    try {
      const endpoint = await unsubscribeBrowserFromPlayPush();
      if (!endpoint) {
        setPushFeedback({
          tone: 'warning',
          message: 'Non ho trovato una subscription web push registrata in questo browser. Lo stato mostrato resta aggregato sul tuo profilo play.',
        });
        return;
      }
      setBrowserPushEndpoint(null);
      const response = await revokePlayPushSubscription({ endpoint }, tenantSlug);
      applyNotificationSettings(response.settings);
      setPushFeedback({ tone: 'info', message: response.message });
    } catch (error) {
      setPushFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : 'Non riesco a disattivare le web push.',
      });
    } finally {
      setUpdatingPushSubscription(false);
    }
  }

  function handleOpenShared(match: PlayMatchSummary) {
    if (!tenantSlug || !match.share_token) {
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

  const pushStatusTone: FeedbackTone = notificationSettings?.push.has_active_subscription
    ? (notificationSettings.push.push_supported ? 'success' : 'warning')
    : 'info';
  const pushStatusMessage = notificationSettings?.push.has_active_subscription
    ? notificationSettings.push.push_supported
      ? `Web push attiva su ${notificationSettings.push.active_subscription_count} ${notificationSettings.push.active_subscription_count === 1 ? 'dispositivo' : 'dispositivi'}.`
      : 'Web push non disponibile da questo server.'
    : 'Web push non attiva.';
  const hasBrowserPushSubscription = Boolean(browserPushEndpoint);
  const hasRemoteOnlyPushSubscription = Boolean(notificationSettings?.push.has_active_subscription && !hasBrowserPushSubscription);
  const clubDisplayName = resolveClubDisplayName(tenantSlug, clubConfig?.public_name);
  const accessPath = buildPlayAccessPath(tenantSlug);
  const unreadNotificationsCount = notificationSettings?.unread_notifications_count ?? 0;
  const shareUrl = shareMatch?.share_token ? buildAbsolutePlayMatchUrl(tenantSlug, shareMatch.share_token) : null;
  const shareText = shareMatch && shareUrl ? buildPlayMatchShareText({
    startAt: shareMatch.start_at,
    endAt: shareMatch.end_at,
    levelRequested: shareMatch.level_requested,
    participantNames: shareMatch.participants.map((participant) => participant.profile_name),
    clubName: clubDisplayName,
    shareUrl,
    timeZone: clubConfig?.timezone,
  }) : null;
  const whatsAppUrl = shareMatch && shareUrl ? buildPlayMatchWhatsAppUrl({
    startAt: shareMatch.start_at,
    endAt: shareMatch.end_at,
    levelRequested: shareMatch.level_requested,
    participantNames: shareMatch.participants.map((participant) => participant.profile_name),
    clubName: clubDisplayName,
    shareUrl,
    timeZone: clubConfig?.timezone,
  }) : null;

  function scrollToSection(sectionId: string) {
    if (typeof document === 'undefined') {
      return;
    }
    document.getElementById(sectionId)?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
  }

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='page-shell max-w-6xl'>
        <header className='product-hero-panel'>
          <PageBrandBar
            className='mb-6 play-page-brand-bar'
            actions={(
              <>
                <Link className='hero-action-secondary' to={withTenantPath('/booking', tenantSlug)}>
                  <ArrowLeft size={16} />
                  <span>Torna al booking</span>
                </Link>
                <Link className='hero-action-secondary' to='/'>
                  <span>Torna alla home</span>
                </Link>
              </>
            )}
          />
          <div className='product-hero-layout'>
            <div className='product-hero-copy'>
              <CommunityMatchinnBrand clubName={clubDisplayName} />
              <h1 className='mt-4 text-3xl font-bold tracking-tight text-white sm:text-4xl'>Partite aperte</h1>
              <p className='product-hero-description'>Trova match da completare ed organizza le tue partite!</p>
            </div>

            <div className='product-hero-actions'>
              {!currentPlayer ? (
                <Link className='hero-action-primary' to={accessPath}>
                  <UsersRound size={16} />
                  <span>Entra o rientra nella community</span>
                </Link>
              ) : null}
              {currentPlayer ? (
                <>
                  <button
                    type='button'
                    aria-label={unreadNotificationsCount > 0 ? `Notifiche utente (${unreadNotificationsCount} da visualizzare)` : 'Notifiche utente'}
                    className={`hero-icon-button ${unreadNotificationsCount > 0 ? 'hero-icon-button-alert' : ''}`}
                    onClick={() => scrollToSection('play-notifications-section')}
                  >
                    <BellRing size={18} />
                  </button>
                </>
              ) : null}
            </div>
          </div>
        </header>

        <div className='mt-6 space-y-6'>
          {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

          {pendingPlayPayment ? (
            <SectionCard
              title='Caparra community da completare'
              description='Paga ora la caparra del match appena completato. Il checkout resta riservato al quarto player che ha chiuso il 4/4.'
              elevated
            >
              <div className='space-y-4'>
                <AlertBanner tone='warning' title='Ultimo passo per bloccare il campo'>
                  Prenotazione {pendingPlayPayment.booking.public_reference}. Caparra richiesta di {pendingPlayPayment.paymentAction.deposit_amount.toFixed(2).replace('.', ',')} EUR.
                  {pendingPlayPayment.paymentAction.expires_at ? ` Completa entro le ${new Date(pendingPlayPayment.paymentAction.expires_at).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}.` : ''}
                </AlertBanner>

                <div className='surface-muted space-y-3'>
                  <p className='text-sm text-slate-700'>Il sistema ha associato il pagamento al player che ha completato il match. Dopo il checkout tornerai sul flusso standard di conferma pagamento.</p>
                  <div className='action-cluster'>
                    {pendingPlayPayment.paymentAction.available_providers.map((provider) => (
                      <button
                        key={provider}
                        type='button'
                        className='btn-primary'
                        disabled={startingCheckoutProvider !== null}
                        onClick={() => void handleStartPlayCheckout(provider)}
                      >
                        {startingCheckoutProvider === provider ? 'Apertura checkout…' : `Paga con ${paymentProviderLabel(provider)}`}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </SectionCard>
          ) : null}

          {loading ? (
            <LoadingBlock label='Carico la bacheca community del club…' labelClassName='text-base' />
          ) : (
            <>
              <div className='grid gap-6 xl:grid-cols-2 xl:items-start'>
                <div className={openMatchesExpanded ? 'xl:col-span-2' : ''}>
                  <SectionCard
                    title='Partite da completare'
                    description='Filtra per data e livello. Le partite 3/4 vengono visualizzate prima di 2/4 e 1/4.'
                    collapsedDescription='Apri per filtrare per data e livello.'
                    elevated
                    collapsible
                    defaultExpanded={false}
                    expanded={openMatchesExpanded}
                    onExpandedChange={setOpenMatchesExpanded}
                    collapsedUniform
                    collapsedClassName='section-card-collapsed-compact'
                    actions={(expanded) => (!expanded ? (
                      <div className='rounded-full bg-slate-100 px-3 py-2 text-right text-xs font-semibold text-slate-600'>
                        {openMatchesSummary}
                      </div>
                    ) : null)}
                  >
                    <div className='space-y-4'>
                      <PlayMatchFilterBar
                        sectionLabel='partite aperte'
                        dateOptions={openMatchDateOptions}
                        dateFilter={openMatchDateFilter}
                        levelFilter={openMatchLevelFilter}
                        onDateChange={setOpenMatchDateFilter}
                        onLevelChange={setOpenMatchLevelFilter}
                      />
                      <MatchBoard matches={filteredOpenMatches} onJoin={handleJoin} onShare={handleShare} />
                    </div>
                  </SectionCard>
                </div>

                <div className={myMatchesExpanded ? 'xl:col-span-2' : ''}>
                  {currentPlayer ? (
                    <SectionCard
                      sectionId='play-user-section'
                      title='Le mie partite'
                      description='Filtra per data e livello i match in cui sei gia dentro.'
                      collapsedDescription='Apri per filtrare per data e livello.'
                      collapsible
                      defaultExpanded={false}
                      expanded={myMatchesExpanded}
                      onExpandedChange={setMyMatchesExpanded}
                      collapsedUniform
                      collapsedClassName='section-card-collapsed-compact'
                      actions={(expanded) => (!expanded ? (
                        <div className='rounded-full bg-slate-100 px-3 py-2 text-right text-xs font-semibold text-slate-600'>
                          {myMatchesSummary}
                        </div>
                      ) : null)}
                    >
                      <div className='space-y-4'>
                        <PlayMatchFilterBar
                          sectionLabel='mie partite'
                          dateOptions={myMatchDateOptions}
                          dateFilter={myMatchDateFilter}
                          levelFilter={myMatchLevelFilter}
                          onDateChange={setMyMatchDateFilter}
                          onLevelChange={setMyMatchLevelFilter}
                        />
                        <MyMatches
                          matches={filteredMyMatches}
                          currentPlayerId={currentPlayer.id}
                          onOpen={handleOpenShared}
                          onShare={handleShare}
                          onSearchPlayers={(match) => void handleSearchPlayers(match)}
                          onRotateShareToken={(match) => void handleRotateShareToken(match)}
                          onRevokeShareToken={(match) => void handleRevokeShareToken(match)}
                          onLeave={(match) => void handleLeave(match)}
                          onEdit={openManagePanel}
                          onCancel={(match) => void handleCancel(match)}
                        />
                      </div>
                    </SectionCard>
                  ) : (
                    <SectionCard
                      title='Le mie partite'
                      collapsedDescription='Apri per capire come rivedere i tuoi match.'
                      collapsible
                      defaultExpanded={false}
                      expanded={myMatchesExpanded}
                      onExpandedChange={setMyMatchesExpanded}
                      collapsedUniform
                      collapsedClassName='section-card-collapsed-compact'
                      actions={(expanded) => (!expanded ? (
                        <div className='rounded-full bg-slate-100 px-3 py-2 text-right text-xs font-semibold text-slate-600'>
                          {myMatchesSummary}
                        </div>
                      ) : null)}
                    >
                      <div className='surface-muted flex items-start gap-3'>
                        <div className='flex items-center gap-3'>
                          <UsersRound size={18} className='text-cyan-700' />
                          <p className='text-sm text-slate-700'>Quando attivi il profilo community, qui ritrovi join, creazione e notifiche. Usa il pulsante in alto per entrare o rientrare senza aprire un secondo passaggio.</p>
                        </div>
                      </div>
                    </SectionCard>
                  )}
                </div>
              </div>

              <SectionCard
                title='Crea nuova partita'
                description='Scegli slot'
                collapsedDescription='Scegli lo slot e gioca!'
                collapsible
                defaultExpanded={false}
                collapsedUniform
                collapsedClassName='section-card-collapsed-compact'
              >
                <div className='space-y-6'>
                  <CreateMatchForm tenantSlug={tenantSlug} onCreateIntent={handleCreateIntent} />

                  {suggestedMatches.length > 0 ? (
                    <div className='space-y-4 rounded-2xl border border-amber-200 bg-amber-50/80 p-4'>
                      <h3 className='text-lg font-semibold text-slate-950'>Prima completa queste partite compatibili</h3>
                      <AlertBanner tone='warning'>Il club ha gia partite compatibili da completare prima di aprirne una nuova.</AlertBanner>
                      <MatchBoard matches={suggestedMatches} onJoin={handleJoin} onShare={handleShare} />
                      {pendingCreateIntent ? (
                        <button type='button' className='btn-secondary' onClick={() => void submitCreateIntent(pendingCreateIntent, true)}>
                          Crea comunque una nuova partita
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </SectionCard>

              {currentPlayer && notificationSettings && notificationDraft ? (
                <SectionCard
                  sectionId='play-notifications-section'
                  title='Preferenze notifiche'
                  collapsedDescription={<>Scegli cosa <span className='matchinn-wordmark'><span className='matchinn-wordmark-match'>match</span><span className='matchinn-wordmark-inn'>inn</span></span> ti notifica</>}
                  collapsible
                  defaultExpanded={false}
                  collapsedUniform
                  collapsedClassName='section-card-collapsed-compact'
                >
                  <div className='space-y-4'>
                    <div className='flex flex-wrap items-center gap-3 text-sm'>
                      <span className={`rounded-full px-3 py-1 font-semibold ${notificationSettings.unread_notifications_count > 0 ? 'bg-cyan-100 text-cyan-900' : 'bg-slate-200 text-slate-700'}`}>
                        Non lette: {notificationSettings.unread_notifications_count}
                      </span>
                    </div>

                    <AlertBanner tone={pushStatusTone} title='Stato attivazione'>
                      {pushStatusMessage}
                    </AlertBanner>

                    <div className='grid gap-4 lg:grid-cols-[minmax(0,1fr)_17rem] lg:items-start'>
                      <div className='surface-muted space-y-3'>
                        <p className='flex items-center gap-2 text-sm font-semibold text-slate-900'>
                          <BellRing size={16} /> Preferenze notifiche
                        </p>

                        <label className='flex items-start gap-3 text-sm text-slate-700'>
                          <input
                            type='checkbox'
                            checked={notificationDraft.in_app_enabled}
                            onChange={(event) => setNotificationDraft({ ...notificationDraft, in_app_enabled: event.target.checked })}
                          />
                          <span>Feed in-app attivo</span>
                        </label>

                        <label className='flex items-start gap-3 text-sm text-slate-700'>
                          <input
                            type='checkbox'
                            checked={notificationDraft.web_push_enabled}
                            onChange={(event) => setNotificationDraft({ ...notificationDraft, web_push_enabled: event.target.checked })}
                          />
                          <span>Abilita web push</span>
                        </label>

                        <label className='flex items-start gap-3 text-sm text-slate-700'>
                          <input
                            type='checkbox'
                            checked={notificationDraft.notify_match_three_of_four}
                            onChange={(event) => setNotificationDraft({ ...notificationDraft, notify_match_three_of_four: event.target.checked })}
                          />
                          <span>Avvisami per match 3/4</span>
                        </label>

                        <label className='flex items-start gap-3 text-sm text-slate-700'>
                          <input
                            type='checkbox'
                            checked={notificationDraft.notify_match_two_of_four}
                            onChange={(event) => setNotificationDraft({ ...notificationDraft, notify_match_two_of_four: event.target.checked })}
                          />
                          <span>Avvisami per match 2/4</span>
                        </label>

                        <label className='flex items-start gap-3 text-sm text-slate-700'>
                          <input
                            type='checkbox'
                            checked={notificationDraft.notify_match_one_of_four}
                            onChange={(event) => setNotificationDraft({ ...notificationDraft, notify_match_one_of_four: event.target.checked })}
                          />
                          <span>Avvisami per match 1/4 solo quando il sistema trova una compatibilita forte</span>
                        </label>

                        <label className='flex items-start gap-3 text-sm text-slate-700'>
                          <input
                            type='checkbox'
                            checked={notificationDraft.level_compatibility_only}
                            onChange={(event) => setNotificationDraft({ ...notificationDraft, level_compatibility_only: event.target.checked })}
                          />
                          <span>Filtra solo match compatibili col mio livello</span>
                        </label>

                        {notificationPreferenceFeedback ? <AlertBanner tone={notificationPreferenceFeedback.tone}>{notificationPreferenceFeedback.message}</AlertBanner> : null}

                        <button type='button' className='btn-primary' disabled={savingNotificationPreferences} onClick={() => void handleSaveNotificationPreferences()}>
                          {savingNotificationPreferences ? 'Salvataggio…' : 'Salva preferenze notifiche'}
                        </button>
                      </div>

                      <aside className='surface-muted w-full space-y-3 lg:max-w-[17rem] lg:justify-self-end'>
                        <div className='flex items-center justify-between gap-2'>
                          <p className='text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500'>Web push</p>
                          <span className={`rounded-full px-2 py-1 text-[11px] font-semibold ${hasBrowserPushSubscription ? 'bg-emerald-100 text-emerald-800' : hasRemoteOnlyPushSubscription ? 'bg-cyan-100 text-cyan-800' : 'bg-slate-200 text-slate-600'}`}>
                            {hasBrowserPushSubscription ? 'Questo browser' : hasRemoteOnlyPushSubscription ? 'Altri device' : 'Off'}
                          </span>
                        </div>
                        {!browserSupportsPush ? (
                          <p className='text-xs leading-5 text-amber-700'>Il browser o l ambiente di test corrente non supportano Service Worker + Push API.</p>
                        ) : null}
                        {hasRemoteOnlyPushSubscription ? (
                          <p className='text-xs leading-5 text-slate-500'>Attiva su {notificationSettings.push.active_subscription_count} {notificationSettings.push.active_subscription_count === 1 ? 'dispositivo del tuo profilo' : 'dispositivi del tuo profilo'}, ma non su questo browser.</p>
                        ) : null}
                        {pushFeedback ? <AlertBanner tone={pushFeedback.tone}>{pushFeedback.message}</AlertBanner> : null}

                        <div className='flex flex-col gap-2'>
                          {!hasBrowserPushSubscription ? (
                            <button
                              type='button'
                              className='btn-primary min-h-10 rounded-full px-3 py-2 text-xs'
                              disabled={updatingPushSubscription || !browserSupportsPush || !notificationSettings.push.push_supported}
                              onClick={() => void handleEnablePush()}
                            >
                              {updatingPushSubscription ? 'Attivazione…' : 'Attiva web push'}
                            </button>
                          ) : null}
                          {hasBrowserPushSubscription ? (
                            <button
                              type='button'
                              className='btn-secondary min-h-10 rounded-full px-3 py-2 text-xs'
                              disabled={updatingPushSubscription}
                              onClick={() => void handleDisablePush()}
                            >
                              {updatingPushSubscription ? 'Revoca…' : 'Disattiva web push'}
                            </button>
                          ) : null}
                        </div>
                      </aside>
                    </div>

                    <div>
                      <p className='field-label'>Ultime notifiche in-app</p>
                      {notificationSettings.recent_notifications.length === 0 ? (
                        <div className='surface-muted text-sm text-slate-700'>Nessuna notifica recente.</div>
                      ) : (
                        <div className='space-y-3'>
                          {notificationSettings.recent_notifications.map((item) => (
                            <div key={item.id} className={`rounded-2xl border px-4 py-3 ${item.read_at ? 'border-slate-200 bg-slate-50' : 'border-cyan-200 bg-cyan-50/70'}`}>
                              <div className='flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between'>
                                <p className='text-sm font-semibold text-slate-900'>{item.title}</p>
                                <div className='flex items-center gap-2'>
                                  <span className={`rounded-full px-2 py-1 text-[11px] font-semibold uppercase tracking-wide ${item.read_at ? 'bg-slate-200 text-slate-600' : 'bg-cyan-100 text-cyan-900'}`}>
                                    {item.read_at ? 'Letta' : 'Non letta'}
                                  </span>
                                  <span className='text-xs uppercase tracking-wide text-slate-500'>{new Date(item.created_at).toLocaleString('it-IT')}</span>
                                </div>
                              </div>
                              <p className='mt-2 text-sm text-slate-600'>{item.message}</p>
                              {notificationItemFeedback?.notificationId === item.id ? (
                                <div className='mt-3'>
                                  <AlertBanner tone={notificationItemFeedback.tone}>{notificationItemFeedback.message}</AlertBanner>
                                </div>
                              ) : null}
                              <div className='mt-3 flex flex-wrap items-center gap-3 text-sm'>
                                {item.read_at ? (
                                  <span className='text-slate-500'>Letta il {new Date(item.read_at).toLocaleString('it-IT')}</span>
                                ) : (
                                  <button
                                    type='button'
                                    className='btn-secondary'
                                    disabled={readingNotificationId === item.id}
                                    onClick={() => void handleMarkNotificationRead(item.id)}
                                  >
                                    {readingNotificationId === item.id ? 'Aggiornamento…' : 'Segna come letta'}
                                  </button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </SectionCard>
              ) : null}

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

        {shareMatch && shareUrl && shareText && whatsAppUrl ? (
          <PlayShareDialog
            open={Boolean(shareMatch)}
            title='Condividi questa partita'
            description='Puoi copiare il link oppure aprire WhatsApp con il testo gia pronto.'
            shareUrl={shareUrl}
            shareText={shareText}
            whatsAppUrl={whatsAppUrl}
            onClose={() => setShareMatch(null)}
          />
        ) : null}
      </div>
    </div>
  );
}