import { CalendarClock, ChevronDown, ChevronUp } from 'lucide-react';
import { FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { AdminNav } from '../components/AdminNav';
import { AdminTimeSlotPicker } from '../components/AdminTimeSlotPicker';
import { AlertBanner } from '../components/AlertBanner';
import { DateFieldWithDay } from '../components/DateFieldWithDay';
import { EmptyState } from '../components/EmptyState';
import { LoadingBlock } from '../components/LoadingBlock';
import { PageBrandBar } from '../components/PageBrandBar';
import { SectionCard } from '../components/SectionCard';
import {
  createAdminCourt,
  createAdminBooking,
  createBlackout,
  createAdminCommunityAccessLink,
  createAdminCommunityInvite,
  createRecurring,
  getAdminReport,
  getAdminSession,
  getAdminSettings,
  getSubscriptionStatus,
  listAdminCommunityAccessLinks,
  listAdminCommunityInvites,
  listAdminCourts,
  listBlackouts,
  logoutAdmin,
  previewRecurring,
  revokeAdminCommunityAccessLink,
  revokeAdminCommunityInvite,
  updateAdminCourt,
  updateAdminSettings,
} from '../services/adminApi';
import type {
  AdminCommunityAccessLinkPayload,
  AdminCommunityAccessLinkResponse,
  AdminCommunityAccessLinkStatus,
  AdminCommunityAccessLinkSummary,
  AdminCommunityInvitePayload,
  AdminCommunityInviteResponse,
  AdminCommunityInviteStatus,
  AdminCommunityInviteSummary,
  AdminManualBookingPayload,
  AdminSession,
  AdminSettings,
  BlackoutItem,
  CourtSummary,
  RecurringOccurrence,
  RecurringSeriesPayload,
  ReportResponse,
  SubscriptionStatusBanner,
} from '../types';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';
import { formatCurrency, formatDate, formatDateTime, formatWeekdayLabel, toDateInputValue } from '../utils/format';
import { PLAY_LEVEL_OPTIONS, formatPlayLevel } from '../utils/play';

const today = toDateInputValue(new Date());
const DURATIONS = [60, 90, 120, 150, 180, 210, 240, 270, 300];
const COMMUNITY_INVITES_PAGE_SIZE = 10;
type FeedbackState = { tone: 'error' | 'success'; message: string } | null;
type CourtDraftState = { name: string; badge_label: string };
type CommunityAccessLinkFormState = { label: string; max_uses: string; expires_at: string };
type CommunityInviteStatusFilter = 'ALL' | 'ACTIVE' | 'EXPIRED' | 'REVOKED';

const COMMUNITY_INVITE_FILTER_LABELS: Record<CommunityInviteStatusFilter, string> = {
  ALL: 'Tutti',
  ACTIVE: 'Attivo',
  EXPIRED: 'Scaduto',
  REVOKED: 'Revocato',
};

const COMMUNITY_INVITE_STATUS_LABELS: Record<AdminCommunityInviteStatus, string> = {
  ACTIVE: 'Attivo',
  USED: 'Usato',
  EXPIRED: 'Scaduto',
  REVOKED: 'Revocato',
};

const COMMUNITY_INVITE_STATUS_STYLES: Record<AdminCommunityInviteStatus, string> = {
  ACTIVE: 'bg-emerald-100 text-emerald-700',
  USED: 'bg-sky-100 text-sky-700',
  EXPIRED: 'bg-amber-100 text-amber-700',
  REVOKED: 'bg-slate-200 text-slate-700',
};

const COMMUNITY_ACCESS_LINK_STATUS_LABELS: Record<AdminCommunityAccessLinkStatus, string> = {
  ACTIVE: 'Attivo',
  SATURATED: 'Esaurito',
  EXPIRED: 'Scaduto',
  REVOKED: 'Revocato',
};

const COMMUNITY_ACCESS_LINK_STATUS_STYLES: Record<AdminCommunityAccessLinkStatus, string> = {
  ACTIVE: 'bg-emerald-100 text-emerald-700',
  SATURATED: 'bg-sky-100 text-sky-700',
  EXPIRED: 'bg-amber-100 text-amber-700',
  REVOKED: 'bg-slate-200 text-slate-700',
};

function getRequestStatus(error: any) {
  return error?.response?.status;
}

function getRequestMessage(error: any, fallback: string) {
  return error?.response?.data?.detail || fallback;
}

function getRecurringWeekday(dateValue: string) {
  const [year, month, day] = dateValue.split('-').map(Number);
  if (!year || !month || !day) {
    return 0;
  }

  const normalizedDate = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
  return (normalizedDate.getUTCDay() + 6) % 7;
}

function addWeeksToDateInput(dateValue: string, weeksToAdd: number) {
  const [year, month, day] = dateValue.split('-').map(Number);
  if (!year || !month || !day) {
    return dateValue;
  }

  const normalizedDate = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
  normalizedDate.setUTCDate(normalizedDate.getUTCDate() + (weeksToAdd * 7));
  return normalizedDate.toISOString().slice(0, 10);
}

export function AdminDashboardPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const tenantSlug = getTenantSlugFromSearchParams(searchParams);
  const [session, setSession] = useState<AdminSession | null>(null);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [blackouts, setBlackouts] = useState<BlackoutItem[]>([]);
  const [courts, setCourts] = useState<CourtSummary[]>([]);
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionStatusBanner | null>(null);
  const [loading, setLoading] = useState(true);
  const [pageFeedback, setPageFeedback] = useState<FeedbackState>(null);
  const [manualFeedback, setManualFeedback] = useState<FeedbackState>(null);
  const [recurringFeedback, setRecurringFeedback] = useState<FeedbackState>(null);
  const [blackoutFeedback, setBlackoutFeedback] = useState<FeedbackState>(null);
  const [settingsFeedback, setSettingsFeedback] = useState<FeedbackState>(null);
  const [courtsFeedback, setCourtsFeedback] = useState<FeedbackState>(null);
  const [communityInviteFeedback, setCommunityInviteFeedback] = useState<FeedbackState>(null);
  const [communityAccessLinkFeedback, setCommunityAccessLinkFeedback] = useState<FeedbackState>(null);
  const [communityInvites, setCommunityInvites] = useState<AdminCommunityInviteSummary[]>([]);
  const [communityAccessLinks, setCommunityAccessLinks] = useState<AdminCommunityAccessLinkSummary[]>([]);
  const [communityInviteStatusFilter, setCommunityInviteStatusFilter] = useState<CommunityInviteStatusFilter>('ALL');
  const [communityInviteSearchQuery, setCommunityInviteSearchQuery] = useState('');
  const [communityInvitePage, setCommunityInvitePage] = useState(1);
  const [latestCommunityInvite, setLatestCommunityInvite] = useState<AdminCommunityInviteResponse | null>(null);
  const [latestCommunityAccessLink, setLatestCommunityAccessLink] = useState<AdminCommunityAccessLinkResponse | null>(null);
  const [courtDrafts, setCourtDrafts] = useState<Record<string, CourtDraftState>>({});
  const [newCourtName, setNewCourtName] = useState('Campo 2');
  const [newCourtBadgeLabel, setNewCourtBadgeLabel] = useState('');
  const [communityInviteForm, setCommunityInviteForm] = useState<AdminCommunityInvitePayload>({
    profile_name: '',
    phone: '',
    invited_level: 'NO_PREFERENCE',
  });
  const [communityAccessLinkForm, setCommunityAccessLinkForm] = useState<CommunityAccessLinkFormState>({
    label: '',
    max_uses: '200',
    expires_at: '',
  });
  const [manualForm, setManualForm] = useState<AdminManualBookingPayload>({
    first_name: 'Mario',
    last_name: 'Rossi',
    phone: '3331234567',
    email: 'mario@example.com',
    note: '',
    booking_date: today,
    court_id: null,
    start_time: '',
    slot_id: null,
    duration_minutes: 90,
    payment_provider: 'NONE',
  });
  const [blackoutForm, setBlackoutForm] = useState({
    court_id: null as string | null,
    title: 'Manutenzione ordinaria',
    reason: 'Pulizia e controllo rete',
    start_at: `${today}T12:00`,
    end_at: `${today}T13:30`,
  });
  const [recurringForm, setRecurringForm] = useState<RecurringSeriesPayload>({
    label: 'Allenamento fisso',
    court_id: null,
    weekday: getRecurringWeekday(today),
    start_date: today,
    end_date: addWeeksToDateInput(today, 5),
    start_time: '',
    slot_id: null,
    duration_minutes: 90,
  });
  const [recurringPreview, setRecurringPreview] = useState<RecurringOccurrence[]>([]);
  const adminTimezone = settings?.timezone || session?.timezone || null;
  const normalizedCommunityInviteSearch = communityInviteSearchQuery.trim().toLowerCase();
  const normalizedCommunityInviteDigitsSearch = communityInviteSearchQuery.replace(/\D/g, '');
  const filteredCommunityInvites = communityInvites.filter((invite) => {
    if (communityInviteStatusFilter !== 'ALL' && invite.status !== communityInviteStatusFilter) {
      return false;
    }
    if (!normalizedCommunityInviteSearch) {
      return true;
    }

    const matchesName = invite.profile_name.toLowerCase().includes(normalizedCommunityInviteSearch);
    const invitePhoneDigits = invite.phone.replace(/\D/g, '');
    const matchesPhone = normalizedCommunityInviteDigitsSearch
      ? invitePhoneDigits.includes(normalizedCommunityInviteDigitsSearch)
      : invite.phone.toLowerCase().includes(normalizedCommunityInviteSearch);
    return matchesName || matchesPhone;
  });
  const communityInviteTotalPages = Math.max(1, Math.ceil(filteredCommunityInvites.length / COMMUNITY_INVITES_PAGE_SIZE));
  const currentCommunityInvitePage = Math.min(communityInvitePage, communityInviteTotalPages);
  const communityInvitePageStartIndex = (currentCommunityInvitePage - 1) * COMMUNITY_INVITES_PAGE_SIZE;
  const paginatedCommunityInvites = filteredCommunityInvites.slice(
    communityInvitePageStartIndex,
    communityInvitePageStartIndex + COMMUNITY_INVITES_PAGE_SIZE,
  );
  const hasCommunityInviteFilters = communityInviteStatusFilter !== 'ALL' || normalizedCommunityInviteSearch.length > 0;
  const communityInviteRangeStart = filteredCommunityInvites.length === 0 ? 0 : communityInvitePageStartIndex + 1;
  const communityInviteRangeEnd = filteredCommunityInvites.length === 0
    ? 0
    : Math.min(communityInvitePageStartIndex + COMMUNITY_INVITES_PAGE_SIZE, filteredCommunityInvites.length);

  useEffect(() => {
    void bootstrap();
  }, [tenantSlug]);

  useEffect(() => {
    if (communityInvitePage > communityInviteTotalPages) {
      setCommunityInvitePage(communityInviteTotalPages);
    }
  }, [communityInvitePage, communityInviteTotalPages]);

  useEffect(() => {
    const defaultCourtId = courts[0]?.id;
    if (!defaultCourtId) {
      return;
    }

    setManualForm((prev) => (prev.court_id ? prev : { ...prev, court_id: defaultCourtId }));
    setBlackoutForm((prev) => (prev.court_id ? prev : { ...prev, court_id: defaultCourtId }));
    setRecurringForm((prev) => (prev.court_id ? prev : { ...prev, court_id: defaultCourtId }));
  }, [courts]);

  function redirectToLogin() {
    navigate(withTenantPath('/admin/login', tenantSlug));
  }

  async function bootstrap() {
    setLoading(true);
    setPageFeedback(null);
    try {
      const sessionResponse = await getAdminSession(tenantSlug);
      setSession(sessionResponse);
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        redirectToLogin();
        return;
      }
      setPageFeedback({ tone: 'error', message: getRequestMessage(error, 'Non riesco a verificare la sessione admin in questo momento.') });
      setLoading(false);
      return;
    }

    try {
      const results = await Promise.allSettled([loadReport(), loadBlackouts(), loadCourts(), loadSettings(), loadSubscription(), loadCommunityInvites(), loadCommunityAccessLinks()]);
      const unauthorized = results.find((result) => result.status === 'rejected' && getRequestStatus(result.reason) === 401);
      if (unauthorized) {
        redirectToLogin();
        return;
      }

      const failures = results.filter((result) => result.status === 'rejected');
      if (failures.length > 0) {
        setPageFeedback({ tone: 'error', message: 'Dashboard caricata solo parzialmente. Alcuni pannelli non sono disponibili al momento.' });
      }
    } finally {
      setLoading(false);
    }
  }

  async function loadReport() {
    const response = await getAdminReport();
    setReport(response);
  }

  async function loadBlackouts() {
    const response = await listBlackouts();
    setBlackouts(response);
  }

  async function loadCourts() {
    try {
      const response = await listAdminCourts();
      setCourts(response.items);
      setCourtDrafts(Object.fromEntries(response.items.map((court) => [court.id, { name: court.name, badge_label: court.badge_label || '' }])));
    } catch {
      setCourts([]);
      setCourtDrafts({});
    }
  }

  async function loadSettings() {
    const response = await getAdminSettings();
    setSettings(response);
  }

  async function loadSubscription() {
    try {
      const response = await getSubscriptionStatus(tenantSlug);
      setSubscription(response);
    } catch {
      // Subscription non critica: non blocca la dashboard
    }
  }

  async function loadCommunityInvites() {
    const response = await listAdminCommunityInvites();
    setCommunityInvites(response.items);
  }

  async function loadCommunityAccessLinks() {
    const response = await listAdminCommunityAccessLinks();
    setCommunityAccessLinks(response.items);
  }

  async function refreshDashboard() {
    setPageFeedback(null);
    try {
      await Promise.all([loadReport(), loadBlackouts(), loadSettings(), loadCommunityInvites(), loadCommunityAccessLinks()]);
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        redirectToLogin();
        return;
      }
      setPageFeedback({ tone: 'error', message: getRequestMessage(error, 'Aggiornamento dashboard non riuscito.') });
    }
  }

  async function createManualBooking(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!manualForm.slot_id || !manualForm.start_time) {
      setManualFeedback({ tone: 'error', message: 'Seleziona un orario disponibile per la prenotazione manuale.' });
      return;
    }

    setManualFeedback(null);
    try {
      await createAdminBooking(manualForm);
      setManualFeedback({ tone: 'success', message: 'Prenotazione manuale creata con successo.' });
      void loadReport().catch(() => {
        setPageFeedback({ tone: 'error', message: 'Prenotazione creata, ma il riepilogo non è stato aggiornato.' });
      });
    } catch (error: any) {
      setManualFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Creazione prenotazione non riuscita.' });
    }
  }

  async function submitBlackout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBlackoutFeedback(null);
    try {
      await createBlackout(blackoutForm);
      setBlackoutFeedback({ tone: 'success', message: 'Blackout creato correttamente.' });
      void loadBlackouts().catch(() => {
        setPageFeedback({ tone: 'error', message: 'Blackout creato, ma la lista non è stata aggiornata.' });
      });
    } catch (error: any) {
      setBlackoutFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Creazione blackout non riuscita.' });
    }
  }

  async function submitRecurringPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!recurringForm.start_time || !recurringForm.slot_id) {
      setRecurringFeedback({ tone: 'error', message: 'Seleziona un orario disponibile per la serie ricorrente.' });
      return;
    }

    if (recurringForm.end_date < recurringForm.start_date) {
      setRecurringFeedback({ tone: 'error', message: 'La data fine serie deve essere uguale o successiva alla data di partenza.' });
      return;
    }

    try {
      const response = await previewRecurring(recurringForm);
      setRecurringPreview(response.occurrences);
      setRecurringFeedback(null);
    } catch (error: any) {
      setRecurringFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Preview ricorrenza non disponibile.' });
    }
  }

  async function createRecurringSeries() {
    if (!recurringForm.start_time || !recurringForm.slot_id) {
      setRecurringFeedback({ tone: 'error', message: 'Seleziona un orario disponibile per la serie ricorrente.' });
      return;
    }

    if (recurringForm.end_date < recurringForm.start_date) {
      setRecurringFeedback({ tone: 'error', message: 'La data fine serie deve essere uguale o successiva alla data di partenza.' });
      return;
    }

    setRecurringFeedback(null);
    try {
      const response = await createRecurring(recurringForm);
      setRecurringFeedback({ tone: 'success', message: `Serie creata. Occorrenze create: ${response.created_count}. Saltate: ${response.skipped_count}.` });
      void loadReport().catch(() => {
        setPageFeedback({ tone: 'error', message: 'Serie creata, ma il riepilogo non è stato aggiornato.' });
      });
    } catch (error: any) {
      setRecurringFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Creazione serie ricorrente non riuscita.' });
    }
  }

  async function saveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!settings) return;
    setSettingsFeedback(null);
    try {
      const response = await updateAdminSettings({
        public_name: settings.public_name,
        notification_email: settings.notification_email,
        support_email: settings.support_email || null,
        support_phone: settings.support_phone || null,
        public_address: settings.public_address || null,
        public_postal_code: settings.public_postal_code || null,
        public_city: settings.public_city || null,
        public_province: settings.public_province || null,
        public_latitude: settings.public_latitude ?? null,
        public_longitude: settings.public_longitude ?? null,
        is_community_open: settings.is_community_open,
        booking_hold_minutes: settings.booking_hold_minutes,
        cancellation_window_hours: settings.cancellation_window_hours,
        reminder_window_hours: settings.reminder_window_hours,
        member_hourly_rate: settings.member_hourly_rate,
        non_member_hourly_rate: settings.non_member_hourly_rate,
        member_ninety_minute_rate: settings.member_ninety_minute_rate,
        non_member_ninety_minute_rate: settings.non_member_ninety_minute_rate,
        public_booking_deposit_enabled: settings.public_booking_deposit_enabled ?? true,
        public_booking_base_amount: settings.public_booking_base_amount ?? 20,
        public_booking_included_minutes: settings.public_booking_included_minutes ?? 90,
        public_booking_extra_amount: settings.public_booking_extra_amount ?? 10,
        public_booking_extra_step_minutes: settings.public_booking_extra_step_minutes ?? 30,
        public_booking_extras: settings.public_booking_extras || [],
        play_community_deposit_enabled: settings.play_community_deposit_enabled,
        play_community_deposit_amount: settings.play_community_deposit_amount,
        play_community_payment_timeout_minutes: settings.play_community_payment_timeout_minutes,
        play_community_use_public_deposit: settings.play_community_use_public_deposit ?? false,
      });
      setSettings(response);
      setSettingsFeedback({ tone: 'success', message: 'Regole operative aggiornate.' });
    } catch (error: any) {
      setSettingsFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Aggiornamento settings non riuscito.' });
    }
  }

  async function createCourt() {
    setCourtsFeedback(null);

    try {
      await createAdminCourt({ name: newCourtName, badge_label: newCourtBadgeLabel.trim() || null });
      await loadCourts();
      setNewCourtName(`Campo ${courts.length + 2}`);
      setNewCourtBadgeLabel('');
      setCourtsFeedback({ tone: 'success', message: 'Campo creato correttamente.' });
    } catch (error: any) {
      setCourtsFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Creazione campo non riuscita.' });
    }
  }

  async function renameCourt(courtId: string) {
    const nextDraft = courtDrafts[courtId] || { name: '', badge_label: '' };
    const nextName = nextDraft.name.trim();
    if (!nextName) {
      setCourtsFeedback({ tone: 'error', message: 'Inserisci un nome campo valido.' });
      return;
    }

    setCourtsFeedback(null);
    try {
      await updateAdminCourt(courtId, { name: nextName, badge_label: nextDraft.badge_label.trim() || null });
      await loadCourts();
      setCourtsFeedback({ tone: 'success', message: 'Nome campo aggiornato.' });
    } catch (error: any) {
      setCourtsFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Aggiornamento campo non riuscito.' });
    }
  }

  function buildAbsoluteAppUrl(path: string) {
    return typeof window !== 'undefined' ? `${window.location.origin}${path}` : path;
  }

  function buildAbsoluteCommunityInviteUrl(invite: AdminCommunityInviteResponse) {
    return buildAbsoluteAppUrl(invite.invite_path);
  }

  async function copyCommunityInviteLink(invite: AdminCommunityInviteResponse) {
    const absoluteUrl = buildAbsoluteCommunityInviteUrl(invite);
    try {
      await navigator.clipboard.writeText(absoluteUrl);
      setCommunityInviteFeedback({ tone: 'success', message: 'Link accesso community copiato negli appunti.' });
    } catch {
      setCommunityInviteFeedback({ tone: 'success', message: 'Invito creato. Copia manualmente il link qui sotto.' });
    }
  }

  function buildAbsoluteCommunityAccessLinkUrl(item: AdminCommunityAccessLinkResponse) {
    return buildAbsoluteAppUrl(item.access_path);
  }

  async function copyCommunityAccessLink(item: AdminCommunityAccessLinkResponse) {
    const absoluteUrl = buildAbsoluteCommunityAccessLinkUrl(item);
    try {
      await navigator.clipboard.writeText(absoluteUrl);
      setCommunityAccessLinkFeedback({ tone: 'success', message: 'Link gruppo community copiato negli appunti.' });
    } catch {
      setCommunityAccessLinkFeedback({ tone: 'success', message: 'Link gruppo creato. Copia manualmente il link qui sotto.' });
    }
  }

  async function createCommunityInvite() {
    setCommunityInviteFeedback(null);
    try {
      const response = await createAdminCommunityInvite(communityInviteForm);
      setLatestCommunityInvite(response);
      setCommunityInviteForm({ profile_name: '', phone: '', invited_level: 'NO_PREFERENCE' });
      void loadCommunityInvites().catch(() => {
        setPageFeedback({ tone: 'error', message: 'Invito creato, ma l elenco inviti non e stato aggiornato.' });
      });
      await copyCommunityInviteLink(response);
    } catch (error: any) {
      setCommunityInviteFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Creazione invito community non riuscita.' });
    }
  }

  async function createCommunityAccessLink() {
    setCommunityAccessLinkFeedback(null);
    const payload: AdminCommunityAccessLinkPayload = {
      label: communityAccessLinkForm.label.trim() || null,
      max_uses: communityAccessLinkForm.max_uses.trim() ? Number(communityAccessLinkForm.max_uses) : null,
      expires_at: communityAccessLinkForm.expires_at ? `${communityAccessLinkForm.expires_at}T23:59:00` : null,
    };
    try {
      const response = await createAdminCommunityAccessLink(payload);
      setLatestCommunityAccessLink(response);
      setCommunityAccessLinkForm({ label: '', max_uses: '200', expires_at: '' });
      void loadCommunityAccessLinks().catch(() => {
        setPageFeedback({ tone: 'error', message: 'Link gruppo creato, ma l elenco non e stato aggiornato.' });
      });
      await copyCommunityAccessLink(response);
    } catch (error: any) {
      setCommunityAccessLinkFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Creazione link gruppo community non riuscita.' });
    }
  }

  async function revokeCommunityInvite(inviteId: string) {
    setCommunityInviteFeedback(null);
    try {
      const response = await revokeAdminCommunityInvite(inviteId);
      setCommunityInvites((prev) => prev.map((invite) => invite.id == inviteId ? response.item : invite));
      if (latestCommunityInvite?.invite_id == inviteId) {
        setLatestCommunityInvite(null);
      }
      setCommunityInviteFeedback({ tone: 'success', message: response.message });
    } catch (error: any) {
      setCommunityInviteFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Revoca invito community non riuscita.' });
    }
  }

  async function revokeCommunityAccessLink(linkId: string) {
    setCommunityAccessLinkFeedback(null);
    try {
      const response = await revokeAdminCommunityAccessLink(linkId);
      setCommunityAccessLinks((prev) => prev.map((item) => item.id == linkId ? response.item : item));
      if (latestCommunityAccessLink?.link_id == linkId) {
        setLatestCommunityAccessLink(null);
      }
      setCommunityAccessLinkFeedback({ tone: 'success', message: response.message });
    } catch (error: any) {
      setCommunityAccessLinkFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Revoca link gruppo community non riuscita.' });
    }
  }

  function updateCommunityInviteStatusFilter(value: CommunityInviteStatusFilter) {
    setCommunityInviteStatusFilter(value);
    setCommunityInvitePage(1);
  }

  function updateCommunityInviteSearchQuery(value: string) {
    setCommunityInviteSearchQuery(value);
    setCommunityInvitePage(1);
  }

  async function logout() {
    await logoutAdmin(tenantSlug);
    redirectToLogin();
  }

  return (
    <div className='min-h-screen px-4 py-6 sm:px-6 lg:px-8'>
      <div className='page-shell space-y-6'>
        <div className='admin-hero-panel space-y-4'>
          <PageBrandBar
            className='mb-2'
            actions={<Link className='admin-hero-button-secondary' to='/'>Torna alla home</Link>}
          />
          <div className='admin-hero-layout'>
            <div className='admin-hero-copy'>
              <p className='admin-hero-kicker'>Dashboard admin</p>
              <h1 className='admin-hero-heading'>Prenotazioni e operatività</h1>
              <p className='admin-hero-description'>
                La dashboard resta focalizzata su creazione rapida, serie ricorrenti, blackout e regole operative.
                <span aria-hidden='true' className='block'>&nbsp;</span>
              </p>
            </div>
            <div className='admin-hero-actions'>
              <button onClick={() => void refreshDashboard()} className='admin-hero-button-primary'>Aggiorna pagina</button>
              <button onClick={logout} className='admin-hero-button-secondary'>Esci</button>
            </div>
          </div>
          <AdminNav session={session} notificationEmail={settings?.notification_email || null} />
        </div>

        {pageFeedback ? <AlertBanner tone={pageFeedback.tone}>{pageFeedback.message}</AlertBanner> : null}

        {subscription ? <SubscriptionBanner subscription={subscription} /> : null}

        {loading ? <LoadingBlock label='Sto sincronizzando dashboard, blackout e regole operative…' /> : null}

        <div className='grid gap-6 xl:grid-cols-[1.05fr_0.95fr]'>
          <div className='space-y-6'>
            <SectionCard title='Prenotazione manuale' description='Inserisci rapidamente una prenotazione confermata dal pannello admin.' collapsible defaultExpanded={false} collapsedUniform>
              <form className='mt-4 space-y-4' onSubmit={createManualBooking}>
                <div className='grid gap-3 sm:grid-cols-2'>
                  <div>
                    <label className='field-label' htmlFor='admin-manual-first-name'>Nome</label>
                    <input id='admin-manual-first-name' className='text-input' value={manualForm.first_name} onChange={(event) => setManualForm((prev) => ({ ...prev, first_name: event.target.value }))} />
                  </div>
                  <div>
                    <label className='field-label' htmlFor='admin-manual-last-name'>Cognome</label>
                    <input id='admin-manual-last-name' className='text-input' value={manualForm.last_name} onChange={(event) => setManualForm((prev) => ({ ...prev, last_name: event.target.value }))} />
                  </div>
                  <div>
                    <label className='field-label' htmlFor='admin-manual-phone'>Telefono</label>
                    <input id='admin-manual-phone' className='text-input' value={manualForm.phone} onChange={(event) => setManualForm((prev) => ({ ...prev, phone: event.target.value }))} />
                  </div>
                  <div>
                    <label className='field-label' htmlFor='admin-manual-email'>Email</label>
                    <input id='admin-manual-email' className='text-input' type='email' value={manualForm.email} onChange={(event) => setManualForm((prev) => ({ ...prev, email: event.target.value }))} />
                  </div>
                </div>

                <div className='grid gap-4 sm:grid-cols-[1fr_220px]'>
                  {courts.length > 0 ? (
                    <div>
                      <label className='field-label' htmlFor='admin-manual-court'>Campo</label>
                      <select
                        id='admin-manual-court'
                        className='text-input'
                        value={manualForm.court_id || ''}
                        onChange={(event) => setManualForm((prev) => ({ ...prev, court_id: event.target.value || null, start_time: '', slot_id: null }))}
                      >
                        {courts.map((court) => (
                          <option key={court.id} value={court.id}>{court.name}</option>
                        ))}
                      </select>
                    </div>
                  ) : null}
                </div>

                <div className='grid gap-4 sm:grid-cols-[1fr_220px]'>
                  <DateFieldWithDay
                    id='admin-manual-date'
                    label='Data prenotazione'
                    value={manualForm.booking_date}
                    min={today}
                    onChange={(value) => setManualForm((prev) => ({ ...prev, booking_date: value, start_time: '', slot_id: null }))}
                  />
                  <div>
                    <label className='field-label' htmlFor='admin-manual-duration'>Durata</label>
                    <select
                      id='admin-manual-duration'
                      className='text-input'
                      value={manualForm.duration_minutes}
                      onChange={(event) => setManualForm((prev) => ({ ...prev, duration_minutes: Number(event.target.value), start_time: '', slot_id: null }))}
                    >
                      {DURATIONS.map((value) => <option key={value} value={value}>{value} minuti</option>)}
                    </select>
                  </div>
                </div>

                <div>
                  <p className='field-label'>Orario</p>
                  <AdminTimeSlotPicker
                    bookingDate={manualForm.booking_date}
                    courtId={manualForm.court_id}
                    durationMinutes={manualForm.duration_minutes}
                    selectedSlotId={manualForm.slot_id || ''}
                    tenantSlug={tenantSlug}
                    onSelect={(slot) => setManualForm((prev) => ({ ...prev, start_time: slot.start_time, slot_id: slot.slot_id }))}
                  />
                </div>

                <div>
                  <label className='field-label' htmlFor='admin-manual-note'>Nota interna</label>
                  <textarea id='admin-manual-note' className='text-input min-h-24' value={manualForm.note} onChange={(event) => setManualForm((prev) => ({ ...prev, note: event.target.value }))} />
                </div>

                <button className='btn-primary w-full' type='submit'>Crea prenotazione</button>
                {manualFeedback ? <AlertBanner tone={manualFeedback.tone}>{manualFeedback.message}</AlertBanner> : null}
              </form>
            </SectionCard>

            <SectionCard title='Serie ricorrente' description='Crea una ricorrenza fino a una data finale e controlla subito eventuali conflitti.' collapsible defaultExpanded={false} collapsedUniform>
              <form className='mt-4 space-y-4' onSubmit={submitRecurringPreview}>
                <div>
                  <label className='field-label' htmlFor='admin-recurring-label'>Nome serie ricorrente</label>
                  <input id='admin-recurring-label' className='text-input' value={recurringForm.label} onChange={(event) => setRecurringForm((prev) => ({ ...prev, label: event.target.value }))} />
                </div>

                <div className='grid gap-4 sm:grid-cols-2'>
                  {courts.length > 0 ? (
                    <div>
                      <label className='field-label' htmlFor='admin-recurring-court'>Campo</label>
                      <select
                        id='admin-recurring-court'
                        className='text-input'
                        value={recurringForm.court_id || ''}
                        onChange={(event) => setRecurringForm((prev) => ({ ...prev, court_id: event.target.value || null, start_time: '', slot_id: null }))}
                      >
                        {courts.map((court) => (
                          <option key={court.id} value={court.id}>{court.name}</option>
                        ))}
                      </select>
                    </div>
                  ) : null}
                  <DateFieldWithDay
                    id='admin-recurring-date'
                    label='Data di partenza'
                    value={recurringForm.start_date}
                    min={today}
                    showDayPreview={false}
                    onChange={(value) => {
                      setRecurringForm((prev) => ({
                        ...prev,
                        start_date: value,
                        end_date: prev.end_date < value ? value : prev.end_date,
                        weekday: getRecurringWeekday(value),
                        start_time: '',
                        slot_id: null,
                      }));
                    }}
                  />
                  <DateFieldWithDay
                    id='admin-recurring-end-date'
                    label='Fino al'
                    value={recurringForm.end_date}
                    min={recurringForm.start_date}
                    showDayPreview={false}
                    onChange={(value) => setRecurringForm((prev) => ({ ...prev, end_date: value }))}
                  />
                </div>

                <div className='grid gap-4 sm:grid-cols-[1fr_220px]'>
                  <div className='surface-muted self-start'>
                    <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Giorno serie</p>
                    <p className='mt-2 text-base font-medium text-slate-900'>{formatWeekdayLabel(recurringForm.start_date)}</p>
                  </div>
                  <div className='surface-muted self-start'>
                    <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Ultima ricorrenza</p>
                    <p className='mt-2 text-base font-medium text-slate-900'>{formatWeekdayLabel(recurringForm.end_date)} {formatDate(recurringForm.end_date)}</p>
                  </div>
                </div>

                <div className='grid gap-3 sm:grid-cols-1'>
                  <div>
                    <label className='field-label' htmlFor='admin-recurring-duration'>Durata</label>
                    <select
                      id='admin-recurring-duration'
                      className='text-input'
                      value={recurringForm.duration_minutes}
                      onChange={(event) => {
                        setRecurringForm((prev) => ({ ...prev, duration_minutes: Number(event.target.value), start_time: '', slot_id: null }));
                      }}
                    >
                      {DURATIONS.map((value) => <option key={value} value={value}>{value} minuti</option>)}
                    </select>
                  </div>
                </div>

                <div>
                  <p className='field-label'>Orario della serie</p>
                  <AdminTimeSlotPicker
                    bookingDate={recurringForm.start_date}
                    courtId={recurringForm.court_id}
                    durationMinutes={recurringForm.duration_minutes}
                    selectedSlotId={recurringForm.slot_id || ''}
                    tenantSlug={tenantSlug}
                    onSelect={(slot) => {
                      setRecurringForm((prev) => ({ ...prev, start_time: slot.start_time, slot_id: slot.slot_id }));
                    }}
                  />
                </div>

                <div className='grid gap-2 sm:grid-cols-2'>
                  <button className='btn-secondary' type='submit'>Preview conflitti</button>
                  <button className='btn-primary' type='button' onClick={() => void createRecurringSeries()}>Crea serie</button>
                </div>
                {recurringFeedback ? <AlertBanner tone={recurringFeedback.tone}>{recurringFeedback.message}</AlertBanner> : null}
              </form>

              {recurringPreview.length > 0 ? (
                <div className='mt-4 space-y-2'>
                  {recurringPreview.map((item) => (
                    <div key={`${item.booking_date}-${item.start_time}`} className={item.available ? 'alert-success' : 'alert-warning'}>
                      {item.booking_date} • {item.display_start_time} → {item.display_end_time} • {item.available ? 'ok' : item.reason}
                    </div>
                  ))}
                </div>
              ) : null}
            </SectionCard>
          </div>

          <div className='space-y-6'>
            <SectionCard title='Blocca fascia oraria' description='Usa i blackout per manutenzioni, tornei o indisponibilità tecniche.' collapsible defaultExpanded={false} collapsedUniform>
              <form className='mt-4 space-y-3' onSubmit={submitBlackout}>
                {courts.length > 0 ? (
                  <div>
                    <label className='field-label' htmlFor='admin-blackout-court'>Campo</label>
                    <select
                      id='admin-blackout-court'
                      className='text-input'
                      value={blackoutForm.court_id || ''}
                      onChange={(event) => setBlackoutForm((prev) => ({ ...prev, court_id: event.target.value || null }))}
                    >
                      {courts.map((court) => (
                        <option key={court.id} value={court.id}>{court.name}</option>
                      ))}
                    </select>
                  </div>
                ) : null}
                <div>
                  <label className='field-label' htmlFor='admin-blackout-title'>Titolo blackout</label>
                  <input id='admin-blackout-title' className='text-input' value={blackoutForm.title} onChange={(event) => setBlackoutForm((prev) => ({ ...prev, title: event.target.value }))} />
                </div>
                <div>
                  <label className='field-label' htmlFor='admin-blackout-reason'>Descrizione</label>
                  <input id='admin-blackout-reason' className='text-input' value={blackoutForm.reason} onChange={(event) => setBlackoutForm((prev) => ({ ...prev, reason: event.target.value }))} />
                </div>
                <div className='grid gap-3 sm:grid-cols-2'>
                  <DateFieldWithDay
                    id='admin-blackout-start-date'
                    label='Data inizio'
                    value={getLocalDatePart(blackoutForm.start_at)}
                    min={today}
                    onChange={(value) => setBlackoutForm((prev) => ({ ...prev, start_at: updateLocalDateTimePart(prev.start_at, 'date', value, today, '12:00') }))}
                  />
                  <div>
                    <label className='field-label' htmlFor='admin-blackout-start-time'>Ora inizio</label>
                    <input id='admin-blackout-start-time' className='text-input' type='time' value={getLocalTimePart(blackoutForm.start_at)} onChange={(event) => setBlackoutForm((prev) => ({ ...prev, start_at: updateLocalDateTimePart(prev.start_at, 'time', event.target.value, today, '12:00') }))} />
                  </div>
                </div>
                <div className='grid gap-3 sm:grid-cols-2'>
                  <DateFieldWithDay
                    id='admin-blackout-end-date'
                    label='Data fine'
                    value={getLocalDatePart(blackoutForm.end_at)}
                    min={getLocalDatePart(blackoutForm.start_at) || today}
                    onChange={(value) => setBlackoutForm((prev) => ({ ...prev, end_at: updateLocalDateTimePart(prev.end_at, 'date', value, getLocalDatePart(prev.start_at) || today, '13:30') }))}
                  />
                  <div>
                    <label className='field-label' htmlFor='admin-blackout-end-time'>Ora fine</label>
                    <input id='admin-blackout-end-time' className='text-input' type='time' value={getLocalTimePart(blackoutForm.end_at)} onChange={(event) => setBlackoutForm((prev) => ({ ...prev, end_at: updateLocalDateTimePart(prev.end_at, 'time', event.target.value, getLocalDatePart(prev.start_at) || today, '13:30') }))} />
                  </div>
                </div>
                <p className='text-xs text-slate-500'>Il blackout usa il fuso configurato{adminTimezone ? ` (${adminTimezone})` : ''}. Durante il ritorno all&apos;ora solare gli orari ambigui vengono rifiutati con un errore esplicito.</p>
                <button className='btn-primary w-full' type='submit'>Crea blackout</button>
                {blackoutFeedback ? <AlertBanner tone={blackoutFeedback.tone}>{blackoutFeedback.message}</AlertBanner> : null}
              </form>
              <div className='mt-4 space-y-2'>
                {blackouts.length === 0 ? (
                  <EmptyState icon={CalendarClock} title='Nessun blackout attivo' description='Le chiusure compariranno qui appena create.' />
                ) : (
                  blackouts.slice(0, 3).map((blackout) => (
                    <div key={blackout.id} className='rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700'>
                      <p className='font-semibold text-slate-900'>{blackout.title}</p>
                      {blackout.court_name ? <p className='mt-1 text-xs font-medium text-slate-500'>{blackout.court_name}</p> : null}
                      <p className='mt-1'>{formatDateTime(blackout.start_at, adminTimezone)} → {formatDateTime(blackout.end_at, adminTimezone)}</p>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>

            <SectionCard title='Profilo tenant e regole operative' description='Aggiorna il nome visibile ai giocatori, i contatti pubblici, le tariffe informative e le regole operative del tenant attivo.' collapsible defaultExpanded={false} collapsedUniform>
              {!settings ? (
                <LoadingBlock label='Sto caricando le impostazioni admin…' />
              ) : (
                <form className='space-y-3' onSubmit={saveSettings}>
                  <div className='grid gap-3 sm:grid-cols-2'>
                    <div>
                      <label className='field-label' htmlFor='admin-settings-public-name'>Nome club</label>
                      <input id='admin-settings-public-name' className='text-input' value={settings.public_name} onChange={(event) => setSettings((prev) => prev ? { ...prev, public_name: event.target.value } : prev)} />
                      <p className='mt-2 text-sm text-slate-500'>Questo nome compare nella directory pubblica, nella pagina pubblica del club e nella home booking del tenant.</p>
                    </div>
                    <div>
                      <label className='field-label' htmlFor='admin-settings-notification-email'>Email notifiche operative</label>
                      <input id='admin-settings-notification-email' className='text-input' type='email' value={settings.notification_email} onChange={(event) => setSettings((prev) => prev ? { ...prev, notification_email: event.target.value } : prev)} />
                    </div>
                    <div>
                      <label className='field-label' htmlFor='admin-settings-support-email'>Email supporto pubblico</label>
                      <input id='admin-settings-support-email' className='text-input' type='email' value={settings.support_email || ''} onChange={(event) => setSettings((prev) => prev ? { ...prev, support_email: event.target.value || null } : prev)} />
                    </div>
                    <div>
                      <label className='field-label' htmlFor='admin-settings-support-phone'>Telefono supporto pubblico</label>
                      <input id='admin-settings-support-phone' className='text-input' value={settings.support_phone || ''} onChange={(event) => setSettings((prev) => prev ? { ...prev, support_phone: event.target.value || null } : prev)} />
                    </div>
                  </div>
                  <div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
                    <p className='text-sm font-semibold text-slate-900'>Identita pubblica del club</p>
                    <p className='mt-1 text-sm leading-6 text-slate-600'>Questi campi alimentano la directory pubblica, la ricerca manuale per citta/CAP/provincia e la pagina pubblica del club.</p>
                    <div className='mt-4 grid gap-3 sm:grid-cols-2'>
                      <div className='sm:col-span-2'>
                        <label className='field-label' htmlFor='admin-settings-public-address'>Indirizzo (via, piazza, ecc.)</label>
                        <input id='admin-settings-public-address' className='text-input' value={settings.public_address || ''} onChange={(event) => setSettings((prev) => prev ? { ...prev, public_address: event.target.value || null } : prev)} />
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-public-postal-code'>CAP</label>
                        <input id='admin-settings-public-postal-code' className='text-input' value={settings.public_postal_code || ''} onChange={(event) => setSettings((prev) => prev ? { ...prev, public_postal_code: event.target.value || null } : prev)} />
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-public-city'>Citta</label>
                        <input id='admin-settings-public-city' className='text-input' value={settings.public_city || ''} onChange={(event) => setSettings((prev) => prev ? { ...prev, public_city: event.target.value || null } : prev)} />
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-public-province'>Provincia</label>
                        <input id='admin-settings-public-province' className='text-input' value={settings.public_province || ''} onChange={(event) => setSettings((prev) => prev ? { ...prev, public_province: event.target.value || null } : prev)} />
                      </div>
                      <label className='flex items-start gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 sm:items-center'>
                        <input
                          type='checkbox'
                          checked={settings.is_community_open}
                          onChange={(event) => setSettings((prev) => prev ? { ...prev, is_community_open: event.target.checked } : prev)}
                        />
                        <span>Community aperta a nuovi ingressi</span>
                      </label>
                    </div>
                    <div className='mt-4 grid gap-3 sm:grid-cols-2'>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-public-latitude'>Latitudine (opzionale)</label>
                        <input id='admin-settings-public-latitude' className='text-input' type='number' step='0.000001' min={-90} max={90} value={settings.public_latitude ?? ''} onChange={(event) => setSettings((prev) => prev ? { ...prev, public_latitude: event.target.value === '' ? null : Number(event.target.value) } : prev)} />
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-public-longitude'>Longitudine (opzionale)</label>
                        <input id='admin-settings-public-longitude' className='text-input' type='number' step='0.000001' min={-180} max={180} value={settings.public_longitude ?? ''} onChange={(event) => setSettings((prev) => prev ? { ...prev, public_longitude: event.target.value === '' ? null : Number(event.target.value) } : prev)} />
                      </div>
                    </div>
                    <p className='mt-3 text-sm text-slate-600'>Se inserisci latitudine e longitudine, il club puo comparire anche nell ordinamento “vicino a me” senza usare servizi esterni di geocoding.</p>
                  </div>
                  <div className='grid gap-3 sm:grid-cols-3'>
                    <div>
                      <label className='field-label'>Hold pagamento</label>
                      <input className='text-input' type='number' min={5} max={120} value={settings.booking_hold_minutes} onChange={(event) => setSettings((prev) => prev ? { ...prev, booking_hold_minutes: Number(event.target.value) } : prev)} />
                    </div>
                    <div>
                      <label className='field-label'>Soglia rimborso annullamento</label>
                      <input className='text-input' type='number' min={1} max={168} value={settings.cancellation_window_hours} onChange={(event) => setSettings((prev) => prev ? { ...prev, cancellation_window_hours: Number(event.target.value) } : prev)} />
                    </div>
                    <div>
                      <label className='field-label'>Reminder</label>
                      <input className='text-input' type='number' min={1} max={168} value={settings.reminder_window_hours} onChange={(event) => setSettings((prev) => prev ? { ...prev, reminder_window_hours: Number(event.target.value) } : prev)} />
                    </div>
                  </div>
                  <div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
                    <p className='text-sm font-semibold text-slate-900'>Tariffe informative mostrate nella home pubblica</p>
                    <p className='mt-1 text-sm leading-6 text-slate-600'>Questi importi sono solo informativi per i giocatori e non sostituiscono la caparra online.</p>
                    <div className='mt-4 grid gap-3 sm:grid-cols-2'>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-member-hourly-rate'>Tesserati, tariffa oraria per giocatore</label>
                        <input id='admin-settings-member-hourly-rate' className='text-input' type='number' min={0} max={999} step='0.5' value={settings.member_hourly_rate} onChange={(event) => setSettings((prev) => prev ? { ...prev, member_hourly_rate: Number(event.target.value) } : prev)} />
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-non-member-hourly-rate'>Non tesserati, tariffa oraria per giocatore</label>
                        <input id='admin-settings-non-member-hourly-rate' className='text-input' type='number' min={0} max={999} step='0.5' value={settings.non_member_hourly_rate} onChange={(event) => setSettings((prev) => prev ? { ...prev, non_member_hourly_rate: Number(event.target.value) } : prev)} />
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-member-ninety-rate'>Tesserati, tariffa 90 minuti per giocatore</label>
                        <input id='admin-settings-member-ninety-rate' className='text-input' type='number' min={0} max={999} step='0.5' value={settings.member_ninety_minute_rate} onChange={(event) => setSettings((prev) => prev ? { ...prev, member_ninety_minute_rate: Number(event.target.value) } : prev)} />
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-non-member-ninety-rate'>Non tesserati, tariffa 90 minuti per giocatore</label>
                        <input id='admin-settings-non-member-ninety-rate' className='text-input' type='number' min={0} max={999} step='0.5' value={settings.non_member_ninety_minute_rate} onChange={(event) => setSettings((prev) => prev ? { ...prev, non_member_ninety_minute_rate: Number(event.target.value) } : prev)} />
                      </div>
                    </div>
                  </div>
                  <div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
                    <p className='text-sm font-semibold text-slate-900'>Caparra booking pubblico</p>
                    <p className='mt-1 text-sm leading-6 text-slate-600'>Configura la caparra solo per questo club. Se la disattivi o lasci importo base/minuti inclusi a zero, il booking non mostra alcuna scheda caparra e la prenotazione viene confermata senza checkout.</p>
                    <label className='mt-4 flex items-start gap-3 text-sm text-slate-700'>
                      <input
                        type='checkbox'
                        checked={settings.public_booking_deposit_enabled ?? true}
                        onChange={(event) => setSettings((prev) => prev ? { ...prev, public_booking_deposit_enabled: event.target.checked } : prev)}
                      />
                      <span>Attiva caparra booking pubblico</span>
                    </label>
                    <div className='mt-4 grid gap-3 sm:grid-cols-2'>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-public-booking-base-amount'>Importo base</label>
                        <input id='admin-settings-public-booking-base-amount' className='text-input' type='number' min={0} max={999} step='0.5' value={settings.public_booking_base_amount ?? 20} onChange={(event) => setSettings((prev) => prev ? { ...prev, public_booking_base_amount: Number(event.target.value) } : prev)} />
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-public-booking-included-minutes'>Minuti inclusi</label>
                        <input id='admin-settings-public-booking-included-minutes' className='text-input' type='number' min={0} max={600} step='30' value={settings.public_booking_included_minutes ?? 90} onChange={(event) => setSettings((prev) => prev ? { ...prev, public_booking_included_minutes: Number(event.target.value) } : prev)} />
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-public-booking-extra-amount'>Importo extra</label>
                        <input id='admin-settings-public-booking-extra-amount' className='text-input' type='number' min={0} max={999} step='0.5' value={settings.public_booking_extra_amount ?? 10} onChange={(event) => setSettings((prev) => prev ? { ...prev, public_booking_extra_amount: Number(event.target.value) } : prev)} />
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-public-booking-extra-step'>Step extra minuti</label>
                        <input id='admin-settings-public-booking-extra-step' className='text-input' type='number' min={0} max={300} step='30' value={settings.public_booking_extra_step_minutes ?? 30} onChange={(event) => setSettings((prev) => prev ? { ...prev, public_booking_extra_step_minutes: Number(event.target.value) } : prev)} />
                      </div>
                    </div>
                    <div className='mt-4'>
                      <label className='field-label' htmlFor='admin-settings-public-booking-extras'>Extra del club</label>
                      <textarea
                        id='admin-settings-public-booking-extras'
                        className='text-input min-h-24'
                        value={(settings.public_booking_extras || []).join('\n')}
                        onChange={(event) => setSettings((prev) => prev ? { ...prev, public_booking_extras: event.target.value.split('\n').map((item) => item.trim()).filter(Boolean) } : prev)}
                        placeholder={'Noleggio racchette\nLuci serali\nOrario premium'}
                      />
                    </div>
                  </div>
                  <div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
                    <p className='text-sm font-semibold text-slate-900'>Caparra community /play</p>
                    <p className='mt-1 text-sm leading-6 text-slate-600'>Per default il match 4/4 resta confermato con saldo al circolo. Puoi mantenere una caparra community dedicata oppure far ereditare la stessa caparra del booking pubblico del club.</p>
                    <label className='mt-4 flex items-start gap-3 text-sm text-slate-700'>
                      <input
                        type='checkbox'
                        checked={Boolean(settings.play_community_use_public_deposit)}
                        onChange={(event) => setSettings((prev) => prev ? {
                          ...prev,
                          play_community_use_public_deposit: event.target.checked,
                          play_community_deposit_enabled: event.target.checked ? false : prev.play_community_deposit_enabled,
                        } : prev)}
                      />
                      <span>Usa la stessa caparra del booking pubblico del club</span>
                    </label>
                    <label className='mt-4 flex items-start gap-3 text-sm text-slate-700'>
                      <input
                        type='checkbox'
                        checked={settings.play_community_deposit_enabled}
                        disabled={Boolean(settings.play_community_use_public_deposit)}
                        onChange={(event) => setSettings((prev) => prev ? { ...prev, play_community_deposit_enabled: event.target.checked } : prev)}
                      />
                      <span>Attiva caparra community online sul quarto player</span>
                    </label>
                    <div className='mt-4 grid gap-3 sm:grid-cols-2'>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-play-community-deposit-amount'>Importo caparra community</label>
                        <input
                          id='admin-settings-play-community-deposit-amount'
                          className='text-input'
                          type='number'
                          min={0}
                          max={999}
                          step='0.5'
                          disabled={!settings.play_community_deposit_enabled || Boolean(settings.play_community_use_public_deposit)}
                          value={settings.play_community_deposit_amount}
                          onChange={(event) => setSettings((prev) => prev ? { ...prev, play_community_deposit_amount: Number(event.target.value) } : prev)}
                        />
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-settings-play-community-timeout'>Timeout checkout community</label>
                        <input
                          id='admin-settings-play-community-timeout'
                          className='text-input'
                          type='number'
                          min={5}
                          max={120}
                          value={settings.play_community_payment_timeout_minutes}
                          onChange={(event) => setSettings((prev) => prev ? { ...prev, play_community_payment_timeout_minutes: Number(event.target.value) } : prev)}
                        />
                      </div>
                    </div>
                    {settings.play_community_use_public_deposit ? <p className='mt-3 text-sm text-slate-600'>La caparra Play usera la stessa policy del booking pubblico del club, ma manterra il timeout checkout community configurato qui.</p> : null}
                    <p className='mt-3 text-sm text-slate-600'>Provider online disponibili ora: Stripe <strong>{settings.stripe_enabled ? 'attivo' : 'non disponibile'}</strong> • PayPal <strong>{settings.paypal_enabled ? 'attivo' : 'non disponibile'}</strong>.</p>
                  </div>
                  <div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
                    <p className='text-sm font-semibold text-slate-900'>Inviti accesso community</p>
                    <p className='mt-1 text-sm leading-6 text-slate-600'>Genera un link personale per far entrare un giocatore nella community privata del club. Funziona anche se la community pubblica resta chiusa.</p>
                    <div className='mt-4 grid gap-3 sm:grid-cols-2'>
                      <div>
                        <label className='field-label' htmlFor='admin-community-invite-profile-name'>Nome profilo invito community</label>
                        <input
                          id='admin-community-invite-profile-name'
                          className='text-input'
                          value={communityInviteForm.profile_name}
                          onChange={(event) => setCommunityInviteForm((prev) => ({ ...prev, profile_name: event.target.value }))}
                          placeholder='Giulia Spin'
                        />
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-community-invite-phone'>Telefono invito community</label>
                        <input
                          id='admin-community-invite-phone'
                          className='text-input'
                          value={communityInviteForm.phone}
                          onChange={(event) => setCommunityInviteForm((prev) => ({ ...prev, phone: event.target.value }))}
                          placeholder='+39 333 111 2222'
                        />
                      </div>
                    </div>
                    <div className='mt-3 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end'>
                      <div>
                        <label className='field-label' htmlFor='admin-community-invite-level'>Livello iniziale</label>
                        <select
                          id='admin-community-invite-level'
                          className='text-input'
                          value={communityInviteForm.invited_level}
                          onChange={(event) => setCommunityInviteForm((prev) => ({ ...prev, invited_level: event.target.value as AdminCommunityInvitePayload['invited_level'] }))}
                        >
                          {PLAY_LEVEL_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </div>
                      <button className='btn-secondary sm:w-auto' type='button' onClick={() => void createCommunityInvite()}>
                        Genera link invito community
                      </button>
                    </div>
                    {communityInviteFeedback ? <div className='mt-4'><AlertBanner tone={communityInviteFeedback.tone}>{communityInviteFeedback.message}</AlertBanner></div> : null}
                    {latestCommunityInvite ? (
                      <div className='mt-4 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700'>
                        <p><strong className='text-slate-900'>Giocatore invitato:</strong> {latestCommunityInvite.profile_name}</p>
                        <p className='mt-1'><strong className='text-slate-900'>Telefono:</strong> {latestCommunityInvite.phone}</p>
                        <p className='mt-1'><strong className='text-slate-900'>Livello iniziale:</strong> {formatPlayLevel(latestCommunityInvite.invited_level)}</p>
                        <p className='mt-1'><strong className='text-slate-900'>Scadenza:</strong> {formatDateTime(latestCommunityInvite.expires_at, adminTimezone)}</p>
                        <div className='mt-3 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center'>
                          <input className='text-input' readOnly value={buildAbsoluteCommunityInviteUrl(latestCommunityInvite)} aria-label='Link accesso community generato' />
                          <button className='btn-secondary sm:w-auto' type='button' onClick={() => void copyCommunityInviteLink(latestCommunityInvite)}>
                            Copia link
                          </button>
                        </div>
                      </div>
                    ) : null}
                    <p className='mt-4 text-xs leading-5 text-slate-500'>Per sicurezza il link completo viene mostrato solo subito dopo la generazione. Nell elenco storico qui sotto puoi controllare stato e revoca, ma non recuperare di nuovo il token raw.</p>
                    <div className='mt-4 grid gap-3 sm:grid-cols-[220px_minmax(0,1fr)]'>
                      <div>
                        <label className='field-label' htmlFor='admin-community-invites-status-filter'>Filtra inviti community</label>
                        <select
                          id='admin-community-invites-status-filter'
                          className='text-input'
                          value={communityInviteStatusFilter}
                          onChange={(event) => updateCommunityInviteStatusFilter(event.target.value as CommunityInviteStatusFilter)}
                        >
                          {Object.entries(COMMUNITY_INVITE_FILTER_LABELS).map(([value, label]) => (
                            <option key={value} value={value}>{label}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className='field-label' htmlFor='admin-community-invites-search'>Cerca inviti community</label>
                        <input
                          id='admin-community-invites-search'
                          className='text-input'
                          value={communityInviteSearchQuery}
                          onChange={(event) => updateCommunityInviteSearchQuery(event.target.value)}
                          placeholder='Cerca per nome o telefono'
                        />
                      </div>
                    </div>
                    {filteredCommunityInvites.length > 0 ? (
                      <div className='mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500'>
                        <p>Mostro {communityInviteRangeStart}-{communityInviteRangeEnd} di {filteredCommunityInvites.length} inviti</p>
                        <div className='flex items-center gap-2'>
                          <button
                            className='btn-secondary sm:w-auto'
                            type='button'
                            disabled={currentCommunityInvitePage === 1}
                            onClick={() => setCommunityInvitePage((prev) => Math.max(1, prev - 1))}
                          >
                            Inviti precedenti
                          </button>
                          <span>Pagina {currentCommunityInvitePage} di {communityInviteTotalPages}</span>
                          <button
                            className='btn-secondary sm:w-auto'
                            type='button'
                            disabled={currentCommunityInvitePage >= communityInviteTotalPages}
                            onClick={() => setCommunityInvitePage((prev) => Math.min(communityInviteTotalPages, prev + 1))}
                          >
                            Inviti successivi
                          </button>
                        </div>
                      </div>
                    ) : null}
                    <div className='mt-4 space-y-3'>
                      {communityInvites.length === 0 ? (
                        <EmptyState icon={CalendarClock} title='Nessun invito community emesso' description='Gli inviti generati da questo pannello compariranno qui con stato attivo, usato, scaduto o revocato.' />
                      ) : filteredCommunityInvites.length === 0 ? (
                        <EmptyState icon={CalendarClock} title='Nessun invito corrisponde ai filtri' description={hasCommunityInviteFilters ? 'Prova a cambiare stato o ricerca per tornare a vedere gli inviti emessi.' : 'Non ci sono inviti da mostrare.'} />
                      ) : (
                        paginatedCommunityInvites.map((invite) => (
                          <div key={invite.id} className='rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700'>
                            <div className='flex flex-wrap items-start justify-between gap-3'>
                              <div>
                                <p className='font-semibold text-slate-900'>{invite.profile_name}</p>
                                <p className='mt-1 text-xs text-slate-500'>{invite.phone} • {formatPlayLevel(invite.invited_level)}</p>
                              </div>
                              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${COMMUNITY_INVITE_STATUS_STYLES[invite.status]}`}>
                                {COMMUNITY_INVITE_STATUS_LABELS[invite.status]}
                              </span>
                            </div>
                            <div className='mt-3 grid gap-2 text-xs text-slate-500 sm:grid-cols-2'>
                              <p><strong className='text-slate-700'>Creato:</strong> {formatDateTime(invite.created_at, adminTimezone)}</p>
                              <p><strong className='text-slate-700'>Scade:</strong> {formatDateTime(invite.expires_at, adminTimezone)}</p>
                              {invite.used_at ? <p><strong className='text-slate-700'>Usato:</strong> {formatDateTime(invite.used_at, adminTimezone)}</p> : null}
                              {invite.revoked_at ? <p><strong className='text-slate-700'>Revocato:</strong> {formatDateTime(invite.revoked_at, adminTimezone)}</p> : null}
                              {invite.accepted_player_name ? <p><strong className='text-slate-700'>Entrato come:</strong> {invite.accepted_player_name}</p> : null}
                            </div>
                            {invite.can_revoke ? (
                              <div className='mt-3'>
                                <button
                                  className='btn-secondary sm:w-auto'
                                  type='button'
                                  aria-label={`Revoca link ${invite.profile_name}`}
                                  onClick={() => void revokeCommunityInvite(invite.id)}
                                >
                                  Revoca link
                                </button>
                              </div>
                            ) : null}
                          </div>
                        ))
                      )}
                    </div>

                    <div className='mt-6 rounded-2xl border border-slate-200 bg-white p-4'>
                      <p className='text-sm font-semibold text-slate-900'>Link gruppo community</p>
                      <p className='mt-1 text-sm leading-6 text-slate-600'>Genera un link condivisibile per gruppi WhatsApp o mailing list. Ogni persona entra poi con nome, telefono, email e OTP personale.</p>
                      <div className='mt-4 grid gap-3 sm:grid-cols-3'>
                        <div>
                          <label className='field-label' htmlFor='admin-community-access-link-label'>Etichetta link gruppo</label>
                          <input
                            id='admin-community-access-link-label'
                            className='text-input'
                            value={communityAccessLinkForm.label}
                            onChange={(event) => setCommunityAccessLinkForm((prev) => ({ ...prev, label: event.target.value }))}
                            placeholder='Gruppo WhatsApp Open Match'
                          />
                        </div>
                        <div>
                          <label className='field-label' htmlFor='admin-community-access-link-max-uses'>Utilizzi massimi</label>
                          <input
                            id='admin-community-access-link-max-uses'
                            className='text-input'
                            type='number'
                            min={1}
                            value={communityAccessLinkForm.max_uses}
                            onChange={(event) => setCommunityAccessLinkForm((prev) => ({ ...prev, max_uses: event.target.value }))}
                            placeholder='200'
                          />
                        </div>
                        <div>
                          <label className='field-label' htmlFor='admin-community-access-link-expiry'>Scadenza link gruppo</label>
                          <input
                            id='admin-community-access-link-expiry'
                            className='text-input'
                            type='date'
                            value={communityAccessLinkForm.expires_at}
                            onChange={(event) => setCommunityAccessLinkForm((prev) => ({ ...prev, expires_at: event.target.value }))}
                          />
                        </div>
                      </div>
                      <div className='mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between'>
                        <p className='text-xs leading-5 text-slate-500'>Lascia vuota la scadenza per mantenere il link attivo fino a revoca. Svuota il massimo utilizzi per renderlo illimitato.</p>
                        <button className='btn-secondary sm:w-auto' type='button' onClick={() => void createCommunityAccessLink()}>
                          Genera link gruppo community
                        </button>
                      </div>
                      {communityAccessLinkFeedback ? <div className='mt-4'><AlertBanner tone={communityAccessLinkFeedback.tone}>{communityAccessLinkFeedback.message}</AlertBanner></div> : null}
                      {latestCommunityAccessLink ? (
                        <div className='mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700'>
                          <p><strong className='text-slate-900'>Etichetta:</strong> {latestCommunityAccessLink.label || 'Link gruppo community'}</p>
                          <p className='mt-1'><strong className='text-slate-900'>Utilizzi:</strong> {latestCommunityAccessLink.max_uses ? `0 / ${latestCommunityAccessLink.max_uses}` : 'Illimitati'}</p>
                          <p className='mt-1'><strong className='text-slate-900'>Scadenza:</strong> {latestCommunityAccessLink.expires_at ? formatDateTime(latestCommunityAccessLink.expires_at, adminTimezone) : 'Nessuna scadenza'}</p>
                          <div className='mt-3 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center'>
                            <input className='text-input' readOnly value={buildAbsoluteCommunityAccessLinkUrl(latestCommunityAccessLink)} aria-label='Link gruppo community generato' />
                            <button className='btn-secondary sm:w-auto' type='button' onClick={() => void copyCommunityAccessLink(latestCommunityAccessLink)}>
                              Copia link gruppo
                            </button>
                          </div>
                        </div>
                      ) : null}
                      <div className='mt-4 space-y-3'>
                        {communityAccessLinks.length === 0 ? (
                          <EmptyState icon={CalendarClock} title='Nessun link gruppo emesso' description='I link community condivisibili compariranno qui con stato attivo, esaurito, scaduto o revocato.' />
                        ) : (
                          communityAccessLinks.map((item) => (
                            <div key={item.id} className='rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700'>
                              <div className='flex flex-wrap items-start justify-between gap-3'>
                                <div>
                                  <p className='font-semibold text-slate-900'>{item.label || 'Link gruppo community'}</p>
                                  <p className='mt-1 text-xs text-slate-500'>Utilizzi: {item.max_uses ? `${item.used_count} / ${item.max_uses}` : `${item.used_count} / illimitati`}</p>
                                </div>
                                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${COMMUNITY_ACCESS_LINK_STATUS_STYLES[item.status]}`}>
                                  {COMMUNITY_ACCESS_LINK_STATUS_LABELS[item.status]}
                                </span>
                              </div>
                              <div className='mt-3 grid gap-2 text-xs text-slate-500 sm:grid-cols-2'>
                                <p><strong className='text-slate-700'>Creato:</strong> {formatDateTime(item.created_at, adminTimezone)}</p>
                                <p><strong className='text-slate-700'>Scade:</strong> {item.expires_at ? formatDateTime(item.expires_at, adminTimezone) : 'Nessuna scadenza'}</p>
                                {item.revoked_at ? <p><strong className='text-slate-700'>Revocato:</strong> {formatDateTime(item.revoked_at, adminTimezone)}</p> : null}
                              </div>
                              {item.can_revoke ? (
                                <div className='mt-3'>
                                  <button
                                    className='btn-secondary sm:w-auto'
                                    type='button'
                                    aria-label={`Revoca link gruppo ${item.label || item.id}`}
                                    onClick={() => void revokeCommunityAccessLink(item.id)}
                                  >
                                    Revoca link gruppo
                                  </button>
                                </div>
                              ) : null}
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                  <div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
                    <p className='text-sm font-semibold text-slate-900'>Campi disponibili</p>
                    <p className='mt-1 text-sm leading-6 text-slate-600'>Crea un nuovo campo o rinomina i campi gia presenti dal pannello admin.</p>
                    <div className='mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_220px_auto]'>
                      <input
                        className='text-input flex-1'
                        aria-label='Nome nuovo campo'
                        value={newCourtName}
                        onChange={(event) => setNewCourtName(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') {
                            event.preventDefault();
                            void createCourt();
                          }
                        }}
                        placeholder='Nome nuovo campo'
                      />
                      <input
                        className='text-input'
                        aria-label='Etichetta nuovo campo'
                        value={newCourtBadgeLabel}
                        onChange={(event) => setNewCourtBadgeLabel(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') {
                            event.preventDefault();
                            void createCourt();
                          }
                        }}
                        placeholder='Indoor / Outdoor'
                      />
                      <button className='btn-primary sm:w-auto' type='button' onClick={() => void createCourt()}>Crea campo</button>
                    </div>
                    <div className='mt-4 space-y-3'>
                      {courts.length === 0 ? <p className='text-sm text-slate-500'>Nessun campo caricato al momento.</p> : courts.map((court) => (
                        <div key={court.id} className='grid gap-3 rounded-2xl border border-slate-200 bg-white p-3 sm:grid-cols-[minmax(0,1fr)_220px_auto] sm:items-center'>
                          <input
                            className='text-input flex-1'
                            aria-label={`Nome ${court.name}`}
                            value={courtDrafts[court.id]?.name ?? court.name}
                            onChange={(event) => setCourtDrafts((prev) => ({
                              ...prev,
                              [court.id]: { name: event.target.value, badge_label: prev[court.id]?.badge_label ?? court.badge_label ?? '' },
                            }))}
                          />
                          <input
                            className='text-input'
                            aria-label={`Etichetta ${court.name}`}
                            value={courtDrafts[court.id]?.badge_label ?? court.badge_label ?? ''}
                            onChange={(event) => setCourtDrafts((prev) => ({
                              ...prev,
                              [court.id]: { name: prev[court.id]?.name ?? court.name, badge_label: event.target.value },
                            }))}
                            placeholder='Indoor / Outdoor'
                          />
                          <button className='btn-secondary sm:w-auto' type='button' onClick={() => void renameCourt(court.id)}>
                            Salva nome
                          </button>
                        </div>
                      ))}
                    </div>
                    {courtsFeedback ? <div className='mt-4'><AlertBanner tone={courtsFeedback.tone}>{courtsFeedback.message}</AlertBanner></div> : null}
                  </div>
                  <div className='surface-muted'>
                    <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Provider</p>
                    <p className='mt-2 text-sm text-slate-700'>Stripe: <strong>{settings.stripe_enabled ? 'disponibile' : 'non disponibile'}</strong> • PayPal: <strong>{settings.paypal_enabled ? 'disponibile' : 'non disponibile'}</strong></p>
                  </div>
                  <button className='btn-primary w-full' type='submit'>Salva impostazioni</button>
                  {settingsFeedback ? <AlertBanner tone={settingsFeedback.tone}>{settingsFeedback.message}</AlertBanner> : null}
                </form>
              )}
            </SectionCard>
          </div>
        </div>

      </div>
    </div>
  );
}

function getLocalDatePart(value: string) {
  return value.split('T')[0] || '';
}

function getLocalTimePart(value: string) {
  return value.split('T')[1]?.slice(0, 5) || '';
}

function updateLocalDateTimePart(
  value: string,
  part: 'date' | 'time',
  nextValue: string,
  fallbackDate: string,
  fallbackTime: string,
) {
  const currentDate = getLocalDatePart(value) || fallbackDate;
  const currentTime = getLocalTimePart(value) || fallbackTime;
  const nextDate = part === 'date' ? nextValue : currentDate;
  const nextTime = part === 'time' ? nextValue : currentTime;
  return `${nextDate}T${nextTime}`;
}

function StatCard({ title, value }: { title: string; value: string }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <section className='surface-card overflow-hidden p-0'>
      <button
        type='button'
        aria-expanded={expanded}
        aria-label={`${expanded ? 'Comprimi' : 'Espandi'} ${title}`}
        className='flex w-full items-center justify-between gap-3 px-5 py-4 text-left transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-cyan-100'
        onClick={() => setExpanded((prev) => !prev)}
      >
        <span className='text-sm font-medium text-slate-600'>{title}</span>
        <span className='flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-600'>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </span>
      </button>
      {expanded ? (
        <div className='border-t border-slate-100 px-5 pb-5 pt-3'>
          <p className='text-3xl font-bold text-slate-950'>{value}</p>
        </div>
      ) : null}
    </section>
  );
}

function SubscriptionBanner({ subscription }: { subscription: SubscriptionStatusBanner }) {
  const { status, plan_name, trial_ends_at, is_access_blocked } = subscription;

  const tone = is_access_blocked ? 'error' : status === 'PAST_DUE' ? 'error' : status === 'TRIALING' ? 'warning' : null;
  if (!tone) return null;

  let message = '';
  if (status === 'TRIALING' && trial_ends_at) {
    const ends = new Date(trial_ends_at).toLocaleDateString('it-IT', { day: '2-digit', month: 'long', year: 'numeric' });
    message = `Piano: ${plan_name} — periodo di prova attivo fino al ${ends}.`;
  } else if (status === 'PAST_DUE') {
    message = `Piano: ${plan_name} — pagamento in sospeso. Aggiorna il metodo di pagamento per evitare la sospensione.`;
  } else if (is_access_blocked) {
    message = `Account sospeso o abbonamento scaduto (piano: ${plan_name}). Contatta il supporto.`;
  }

  if (!message) return null;

  return <AlertBanner tone={tone === 'warning' ? 'error' : tone}>{message}</AlertBanner>;
}
