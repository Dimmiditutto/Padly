import { AxiosError } from 'axios';
import { ArrowLeft, ArrowRight, BellRing, Building2, LocateFixed, Mail, MapPin, Phone, Search, UsersRound } from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { LoadingBlock } from '../components/LoadingBlock';
import { PageBrandBar } from '../components/PageBrandBar';
import { SectionCard } from '../components/SectionCard';
import {
  followPublicClub,
  getPublicDiscoveryMe,
  identifyPublicDiscovery,
  listPublicClubs,
  listPublicClubsNearby,
  listPublicWatchlist,
  markPublicDiscoveryNotificationRead,
  unfollowPublicClub,
  updatePublicDiscoveryPreferences,
} from '../services/publicApi';
import type {
  PlayLevel,
  PublicClubSummary,
  PublicClubWatchSummary,
  PublicDiscoveryMeResponse,
  PublicDiscoverySession,
  PublicDiscoveryTimeSlot,
} from '../types';
import { formatDate, formatTimeValue } from '../utils/format';
import { formatPlayLevel, PLAY_LEVEL_OPTIONS } from '../utils/play';

type FeedbackState = { tone: 'info' | 'warning' | 'error' | 'success'; message: string } | null;
type DiscoveryFormState = {
  preferred_level: PlayLevel;
  preferred_time_slots: PublicDiscoveryTimeSlot[];
  latitude: string;
  longitude: string;
  nearby_radius_km: string;
  nearby_digest_enabled: boolean;
  privacy_accepted: boolean;
};

const MATCH_ALERT_ALL_DAY = 'all_day' as const;
type MatchAlertTimeSlot = PublicDiscoveryTimeSlot | typeof MATCH_ALERT_ALL_DAY;

const DEFAULT_DISCOVERY_TIME_SLOTS: PublicDiscoveryTimeSlot[] = ['morning', 'lunch_break', 'early_afternoon', 'late_afternoon', 'evening'];
const DISCOVERY_TIME_SLOT_OPTIONS: Array<{ value: MatchAlertTimeSlot; label: string }> = [
  { value: MATCH_ALERT_ALL_DAY, label: 'Tutti gli orari' },
  { value: 'morning', label: 'Mattina 07:00-12:00' },
  { value: 'lunch_break', label: 'Pausa pranzo 12:00-14:30' },
  { value: 'early_afternoon', label: 'Primo pomeriggio 14:30-17:00' },
  { value: 'late_afternoon', label: 'Tardo pomeriggio 17:00-19:30' },
  { value: 'evening', label: 'Sera 19:30-23:30' },
];

function formatDistance(distanceKm: number | null | undefined) {
  if (distanceKm == null) {
    return 'Distanza non disponibile';
  }
  return `${distanceKm.toFixed(1).replace('.', ',')} km`;
}

function buildLocationLine(club: PublicClubSummary) {
  return [club.public_address, club.public_postal_code, club.public_city, club.public_province].filter(Boolean).join(' • ');
}

function geolocationDeniedMessage(error: GeolocationPositionError | { code?: number } | null | undefined) {
  if (error?.code === 1) {
    return 'Permesso geolocalizzazione negato. Usa la ricerca manuale per citta, CAP o provincia.';
  }
  return 'Geolocalizzazione non disponibile in questo momento. Usa la ricerca manuale per trovare il club.';
}

function createDefaultDiscoveryForm(): DiscoveryFormState {
  return {
    preferred_level: 'NO_PREFERENCE',
    preferred_time_slots: [...DEFAULT_DISCOVERY_TIME_SLOTS],
    latitude: '',
    longitude: '',
    nearby_radius_km: '25',
    nearby_digest_enabled: false,
    privacy_accepted: false,
  };
}

function normalizeDiscoveryTimeSlots(timeSlots: PublicDiscoveryTimeSlot[] | null | undefined) {
  const selected = new Set(timeSlots ?? []);
  const normalized = DEFAULT_DISCOVERY_TIME_SLOTS.filter((slot) => selected.has(slot));
  return normalized.length ? normalized : [...DEFAULT_DISCOVERY_TIME_SLOTS];
}

function allDiscoveryTimeSlotsSelected(timeSlots: PublicDiscoveryTimeSlot[]) {
  return DEFAULT_DISCOVERY_TIME_SLOTS.every((slot) => timeSlots.includes(slot));
}

function createDiscoveryFormFromSession(subscriber: PublicDiscoverySession): DiscoveryFormState {
  return {
    preferred_level: subscriber.preferred_level,
    preferred_time_slots: normalizeDiscoveryTimeSlots(subscriber.preferred_time_slots),
    latitude: subscriber.latitude != null ? String(subscriber.latitude) : '',
    longitude: subscriber.longitude != null ? String(subscriber.longitude) : '',
    nearby_radius_km: String(subscriber.nearby_radius_km),
    nearby_digest_enabled: subscriber.nearby_digest_enabled,
    privacy_accepted: true,
  };
}

function parseApiError(error: unknown, fallback: string) {
  const requestError = error as AxiosError<{ detail?: string }>;
  return requestError.response?.data?.detail || fallback;
}

function parseOptionalNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatNotificationTimestamp(value: string) {
  return new Intl.DateTimeFormat('it-IT', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));
}

export function ClubDirectoryPage({ autoLocateOnMount = false }: { autoLocateOnMount?: boolean }) {
  const [query, setQuery] = useState('');
  const [clubs, setClubs] = useState<PublicClubSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [locating, setLocating] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState>(null);
  const [discovery, setDiscovery] = useState<PublicDiscoveryMeResponse>({
    subscriber: null,
    recent_notifications: [],
    unread_notifications_count: 0,
  });
  const [watchlist, setWatchlist] = useState<PublicClubWatchSummary[]>([]);
  const [discoveryLoading, setDiscoveryLoading] = useState(true);
  const [discoverySubmitting, setDiscoverySubmitting] = useState(false);
  const [locatingDiscovery, setLocatingDiscovery] = useState(false);
  const [watchActionClubSlug, setWatchActionClubSlug] = useState<string | null>(null);
  const [readingNotificationId, setReadingNotificationId] = useState<string | null>(null);
  const [discoveryFeedback, setDiscoveryFeedback] = useState<FeedbackState>(null);
  const [discoveryForm, setDiscoveryForm] = useState<DiscoveryFormState>(() => createDefaultDiscoveryForm());

  const watchlistBySlug = useMemo(
    () => new Map(watchlist.map((item) => [item.club.club_slug, item])),
    [watchlist]
  );
  const levelOptions = useMemo(() => PLAY_LEVEL_OPTIONS, []);

  useEffect(() => {
    if (autoLocateOnMount) {
      void requestNearby();
      return;
    }
    void loadClubs();
  }, [autoLocateOnMount]);

  useEffect(() => {
    void loadDiscoveryContext();
  }, []);

  async function loadClubs(searchQuery?: string) {
    setLoading(true);
    try {
      const response = await listPublicClubs(searchQuery || undefined);
      setClubs(response.items);
    } catch {
      setFeedback({ tone: 'error', message: 'Non riesco a caricare la directory pubblica dei club.' });
    } finally {
      setLoading(false);
    }
  }

  async function loadNearby(latitude: number, longitude: number, searchQuery?: string) {
    setLoading(true);
    try {
      const response = await listPublicClubsNearby(latitude, longitude, searchQuery || undefined);
      setClubs(response.items);
    } catch {
      setFeedback({ tone: 'error', message: 'Non riesco a ordinare i club vicini alla tua posizione.' });
    } finally {
      setLoading(false);
      setLocating(false);
    }
  }

  async function loadDiscoveryContext() {
    setDiscoveryLoading(true);
    try {
      const response = await getPublicDiscoveryMe();
      setDiscovery(response);
      if (response.subscriber) {
        setDiscoveryForm(createDiscoveryFormFromSession(response.subscriber));
        const watchlistResponse = await listPublicWatchlist();
        setWatchlist(watchlistResponse.items);
      } else {
        setWatchlist([]);
        setDiscoveryForm(createDefaultDiscoveryForm());
      }
    } catch {
      setDiscoveryFeedback({ tone: 'error', message: 'Non riesco a caricare la sessione discovery pubblica.' });
    } finally {
      setDiscoveryLoading(false);
    }
  }

  async function requestNearby() {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setFeedback({ tone: 'warning', message: 'Questo browser non supporta la geolocalizzazione. Usa la ricerca manuale per citta, CAP o provincia.' });
      await loadClubs(query.trim() || undefined);
      return;
    }

    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setFeedback(null);
        void loadNearby(position.coords.latitude, position.coords.longitude, query.trim() || undefined);
      },
      (error) => {
        setFeedback({ tone: 'warning', message: geolocationDeniedMessage(error) });
        setLocating(false);
        void loadClubs(query.trim() || undefined);
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
    );
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    await loadClubs(query.trim() || undefined);
  }

  function toggleDiscoveryTimeSlot(slot: MatchAlertTimeSlot) {
    setDiscoveryForm((prev) => {
      if (slot === MATCH_ALERT_ALL_DAY) {
        return { ...prev, preferred_time_slots: [...DEFAULT_DISCOVERY_TIME_SLOTS] };
      }

      if (allDiscoveryTimeSlotsSelected(prev.preferred_time_slots)) {
        return { ...prev, preferred_time_slots: [slot] };
      }

      const nextTimeSlots = prev.preferred_time_slots.includes(slot)
        ? prev.preferred_time_slots.filter((item) => item !== slot)
        : [...prev.preferred_time_slots, slot];

      return {
        ...prev,
        preferred_time_slots: normalizeDiscoveryTimeSlots(nextTimeSlots),
      };
    });
  }

  async function requestDiscoveryCoordinates() {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setDiscoveryFeedback({ tone: 'warning', message: 'Questo browser non supporta la posizione per i Match Alert.' });
      return;
    }

    setLocatingDiscovery(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setDiscoveryForm((prev) => ({
          ...prev,
          latitude: position.coords.latitude.toFixed(6),
          longitude: position.coords.longitude.toFixed(6),
        }));
        setDiscoveryFeedback({ tone: 'success', message: 'Posizione aggiornata per i Match Alert.' });
        setLocatingDiscovery(false);
      },
      (error) => {
        setDiscoveryFeedback({ tone: 'warning', message: geolocationDeniedMessage(error) });
        setLocatingDiscovery(false);
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
    );
  }

  async function handleDiscoverySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDiscoverySubmitting(true);
    setDiscoveryFeedback(null);
    const payload = {
      preferred_level: discoveryForm.preferred_level,
      preferred_time_slots: normalizeDiscoveryTimeSlots(discoveryForm.preferred_time_slots),
      latitude: parseOptionalNumber(discoveryForm.latitude),
      longitude: parseOptionalNumber(discoveryForm.longitude),
      nearby_radius_km: Number(discoveryForm.nearby_radius_km) || 25,
      nearby_digest_enabled: discoveryForm.nearby_digest_enabled,
    };

    try {
      if (discovery.subscriber) {
        await updatePublicDiscoveryPreferences(payload);
        setDiscoveryFeedback({ tone: 'success', message: 'Match Alert aggiornati.' });
        await loadDiscoveryContext();
      } else {
        const response = await identifyPublicDiscovery({ ...payload, privacy_accepted: discoveryForm.privacy_accepted });
        setDiscovery(response);
        if (response.subscriber) {
          setDiscoveryForm(createDiscoveryFormFromSession(response.subscriber));
          const watchlistResponse = await listPublicWatchlist();
          setWatchlist(watchlistResponse.items);
        }
        setDiscoveryFeedback({ tone: 'success', message: 'Match Alert salvati. Ora puoi seguire i club e ricevere notifiche compatibili.' });
      }
    } catch (error) {
      setDiscoveryFeedback({ tone: 'error', message: parseApiError(error, 'Salvataggio Match Alert non riuscito.') });
    } finally {
      setDiscoverySubmitting(false);
    }
  }

  async function toggleWatch(club: PublicClubSummary) {
    if (!discovery.subscriber) {
      setDiscoveryFeedback({ tone: 'info', message: 'Prima salva i tuoi alert per seguire un club.' });
      return;
    }

    setWatchActionClubSlug(club.club_slug);
    setDiscoveryFeedback(null);
    try {
      if (watchlistBySlug.has(club.club_slug)) {
        await unfollowPublicClub(club.club_slug);
        setDiscoveryFeedback({ tone: 'success', message: `${club.public_name} rimosso dai club seguiti.` });
      } else {
        await followPublicClub(club.club_slug);
        setDiscoveryFeedback({ tone: 'success', message: `${club.public_name} aggiunto ai club seguiti.` });
      }
      await loadDiscoveryContext();
    } catch (error) {
      setDiscoveryFeedback({ tone: 'error', message: parseApiError(error, 'Aggiornamento club seguiti non riuscito.') });
    } finally {
      setWatchActionClubSlug(null);
    }
  }

  async function markNotificationRead(notificationId: string) {
    setReadingNotificationId(notificationId);
    setDiscoveryFeedback(null);
    try {
      const response = await markPublicDiscoveryNotificationRead(notificationId);
      setDiscovery(response);
      setDiscoveryFeedback({ tone: 'success', message: 'Alert segnato come letto.' });
    } catch (error) {
      setDiscoveryFeedback({ tone: 'error', message: parseApiError(error, 'Aggiornamento stato alert non riuscito.') });
    } finally {
      setReadingNotificationId(null);
    }
  }

  const allTimeSlotsSelected = allDiscoveryTimeSlotsSelected(discoveryForm.preferred_time_slots);
  const hasSavedDiscoveryCoordinates = discoveryForm.latitude.trim() !== '' && discoveryForm.longitude.trim() !== '';

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='page-shell max-w-6xl'>
        <header className='product-hero-panel'>
          <PageBrandBar
            className='mb-6'
            actions={(
              <Link className='hero-action-secondary' to='/'>
                <ArrowLeft size={16} />
                <span>Torna alla home</span>
              </Link>
            )}
          />
          <div className='product-hero-layout gap-6'>
            <div className='product-hero-copy'>
              <h1 className='text-3xl font-bold tracking-tight text-white sm:text-4xl'>Scopri i club vicino a te</h1>
              <p className='mt-3 text-sm leading-6 text-slate-300 sm:text-base'>Trova un club, scegli una partita ed entra in campo.</p>
            </div>
          </div>
        </header>

        <div className='mt-6 space-y-6'>
          {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

          <SectionCard
            title='Trova dove giocare'
            description='Cerca un club o usa la posizione per vedere quelli più vicini a te.'
            elevated
          >
            <form className='grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto_auto]' onSubmit={handleSearch}>
              <label className='sr-only' htmlFor='public-club-query'>Citta, CAP o provincia</label>
              <input
                id='public-club-query'
                className='text-input'
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder='Citta, CAP o provincia'
              />
              <button type='submit' className='btn-secondary'>
                <Search size={16} />
                <span>Cerca club</span>
              </button>
              <button type='button' className='btn-primary' disabled={locating} onClick={() => void requestNearby()}>
                <LocateFixed size={16} />
                <span>{locating ? 'Rilevamento…' : autoLocateOnMount ? 'Riprova geolocalizzazione club' : 'Usa la mia posizione per i club'}</span>
              </button>
            </form>
          </SectionCard>

          <SectionCard
            title='Match Alert'
            description='Scopri i match piu rilevanti per te, segui i club che ti interessano e ricevi notifiche quando si libera la partita giusta.'
            elevated
          >
            {discoveryFeedback ? <AlertBanner tone={discoveryFeedback.tone}>{discoveryFeedback.message}</AlertBanner> : null}

            {discoveryLoading ? (
              <LoadingBlock label='Carico i Match Alert…' labelClassName='text-sm' />
            ) : (
              <div className='space-y-5'>
                <form className='space-y-4' onSubmit={handleDiscoverySubmit}>
                  <div className='grid gap-4 xl:grid-cols-2'>
                    <div className='surface-card border border-slate-200'>
                      <p className='text-sm font-semibold text-slate-900'>Filtri notifiche</p>
                      <p className='mt-2 text-sm leading-6 text-slate-600'>Scegli livello, orari e distanza massima per concentrare gli alert sui match compatibili.</p>

                      <div className='mt-4 grid gap-4'>
                        <div>
                          <label className='field-label' htmlFor='discovery-level'>Livello</label>
                          <select
                            id='discovery-level'
                            className='text-input'
                            value={discoveryForm.preferred_level}
                            onChange={(event) => setDiscoveryForm((prev) => ({ ...prev, preferred_level: event.target.value as PlayLevel }))}
                          >
                            {levelOptions.map((option) => (
                              <option key={option.value} value={option.value}>{option.label}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className='field-label' htmlFor='discovery-radius'>Distanza massima (km)</label>
                          <input
                            id='discovery-radius'
                            className='text-input'
                            type='number'
                            min={5}
                            max={250}
                            value={discoveryForm.nearby_radius_km}
                            onChange={(event) => setDiscoveryForm((prev) => ({ ...prev, nearby_radius_km: event.target.value }))}
                          />
                        </div>

                        <div>
                          <p className='field-label'>Orari preferiti</p>
                          <div className='match-alert-slot-list'>
                            {DISCOVERY_TIME_SLOT_OPTIONS.map((slot) => {
                              const checked = slot.value === MATCH_ALERT_ALL_DAY
                                ? allTimeSlotsSelected
                                : !allTimeSlotsSelected && discoveryForm.preferred_time_slots.includes(slot.value);

                              return (
                                <label key={slot.value} className={`match-alert-slot-option ${checked ? 'match-alert-slot-option-active' : ''}`}>
                                  <input
                                    type='checkbox'
                                    checked={checked}
                                    onChange={() => toggleDiscoveryTimeSlot(slot.value)}
                                    className='h-4 w-4 rounded border-slate-300'
                                  />
                                  <span>{slot.label}</span>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className='surface-card border border-slate-200'>
                      <p className='text-sm font-semibold text-slate-900'>Match vicino a te</p>
                      <p className='mt-2 text-sm leading-6 text-slate-600'>Decidi se vuoi ricevere anche i match vicini e salva la posizione solo quando ti serve.</p>

                      <label className='mt-4 flex items-start gap-3 rounded-2xl border border-slate-200 p-4 text-sm text-slate-700'>
                        <input
                          type='checkbox'
                          checked={discoveryForm.nearby_digest_enabled}
                          onChange={(event) => setDiscoveryForm((prev) => ({ ...prev, nearby_digest_enabled: event.target.checked }))}
                          className='mt-1 h-4 w-4 rounded border-slate-300'
                        />
                        <span>Attiva match alert</span>
                      </label>

                      <div className='match-alert-location-card'>
                        <div>
                          <p className='font-semibold text-slate-900'>{hasSavedDiscoveryCoordinates ? 'Posizione salvata' : 'Posizione non ancora salvata'}</p>
                          <p className='mt-1 text-sm leading-6 text-slate-600'>
                            {hasSavedDiscoveryCoordinates
                              ? 'Il digest vicino a te usa la tua posizione solo per trovare club compatibili nel raggio scelto.'
                              : 'Usa la tua posizione per ricevere alert sui club vicini senza inserire coordinate manualmente.'}
                          </p>
                        </div>
                        <button type='button' className='match-alert-location-button' onClick={() => void requestDiscoveryCoordinates()} disabled={locatingDiscovery}>
                          <LocateFixed size={16} />
                          <span>{locatingDiscovery ? 'Rilevamento…' : 'Usa la mia posizione per gli alert'}</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className='surface-muted'>
                    <p className='text-sm font-semibold text-slate-900'>Privacy e salvataggio</p>
                    <p className='mt-2 text-sm leading-6 text-slate-600'>Usiamo questi dati solo per salvare i filtri alert, i club seguiti e gli avvisi compatibili con le tue preferenze pubbliche.</p>

                    <label className='mt-4 flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700'>
                      <input
                        type='checkbox'
                        checked={discoveryForm.privacy_accepted}
                        onChange={(event) => setDiscoveryForm((prev) => ({ ...prev, privacy_accepted: event.target.checked }))}
                        className='mt-1 h-4 w-4 rounded border-slate-300'
                        required={!discovery.subscriber}
                      />
                      <span>Accetto il trattamento dei dati per salvare i filtri alert e ricevere notifiche nella sezione Match Alert.</span>
                    </label>

                    <div className='mt-4 flex flex-col gap-3 sm:flex-row sm:items-center'>
                      <button className='btn-primary' type='submit' disabled={discoverySubmitting}>
                        <BellRing size={16} />
                        <span>{discoverySubmitting ? 'Salvataggio…' : 'Salva alert'}</span>
                      </button>
                      {discovery.subscriber ? <p className='text-sm text-slate-600'>I tuoi filtri restano separati dalla community privata Play.</p> : null}
                    </div>
                  </div>
                </form>

                <div className='grid gap-4 xl:grid-cols-2'>
                  <div className='surface-card border border-slate-200'>
                    <div className='flex items-center justify-between gap-3'>
                      <p className='text-sm font-semibold text-slate-900'>Club seguiti</p>
                      <span className='rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700'>
                        {watchlist.length} {watchlist.length === 1 ? 'seguito' : 'seguiti'}
                      </span>
                    </div>
                    <div className='mt-3 space-y-3'>
                      {watchlist.length === 0 ? (
                        <div className='space-y-3 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-sm text-slate-600'>
                          <p>Nessun club seguito per ora. Scegline uno dalla directory qui sotto e Match Alert iniziera a monitorarlo per te.</p>
                          <a className='btn-secondary w-fit' href='#club-directory'>Trova il club</a>
                        </div>
                      ) : (
                        watchlist.map((item) => (
                          <article key={item.watch_id} className='rounded-2xl border border-slate-200 bg-white px-4 py-3'>
                            <div className='flex items-start justify-between gap-3'>
                              <div>
                                <p className='font-semibold text-slate-950'>{item.club.public_name}</p>
                                <p className='mt-1 text-sm text-slate-600'>
                                  {item.matching_open_match_count} match compatibili ora disponibili
                                  {item.club.distance_km != null ? ` • ${formatDistance(item.club.distance_km)}` : ''}
                                </p>
                              </div>
                              <Link className='btn-secondary' to={`/c/${item.club.club_slug}`}>
                                <span>Apri club</span>
                              </Link>
                            </div>
                          </article>
                        ))
                      )}
                    </div>
                  </div>

                  <div className='surface-card border border-slate-200'>
                    <div className='flex items-center justify-between gap-3'>
                      <p className='text-sm font-semibold text-slate-900'>Alert recenti</p>
                      <span className='rounded-full bg-cyan-100 px-3 py-1 text-xs font-semibold text-cyan-800'>Non lette: {discovery.unread_notifications_count}</span>
                    </div>
                    <div className='mt-3 space-y-3'>
                      {discovery.recent_notifications.length === 0 ? (
                        <p className='text-sm text-slate-600'>Ancora nessun alert. Potrai vedere qui i match aperti che adottano le tue preferenze.</p>
                      ) : (
                        discovery.recent_notifications.map((item) => (
                          <article key={item.id} data-testid='public-discovery-notification' className={`rounded-2xl border bg-white px-4 py-3 ${item.read_at ? 'border-slate-200' : 'border-cyan-300 ring-1 ring-cyan-100'}`}>
                            <div className='flex items-start justify-between gap-3'>
                              <div>
                                <p className='font-semibold text-slate-950'>{item.title}</p>
                                <p className='mt-1 text-sm text-slate-600'>{item.message}</p>
                              </div>
                              <div className='flex flex-col items-end gap-2'>
                                <span className='text-xs font-medium uppercase tracking-[0.14em] text-cyan-700'>{item.kind.split('_').join(' ')}</span>
                                <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${item.read_at ? 'bg-slate-100 text-slate-600' : 'bg-amber-100 text-amber-700'}`}>
                                  {item.read_at ? 'Letta' : 'Non letta'}
                                </span>
                              </div>
                            </div>
                            <div className='mt-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between'>
                              <p className='text-xs text-slate-500'>
                                {item.read_at ? `Letta ${formatNotificationTimestamp(item.read_at)}` : formatNotificationTimestamp(item.created_at)}
                              </p>
                              {!item.read_at ? (
                                <button
                                  type='button'
                                  className='btn-secondary'
                                  onClick={() => void markNotificationRead(item.id)}
                                  disabled={readingNotificationId === item.id}
                                >
                                  <span>{readingNotificationId === item.id ? 'Aggiornamento…' : 'Segna come letta'}</span>
                                </button>
                              ) : null}
                            </div>
                          </article>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </SectionCard>

          {loading ? (
            <LoadingBlock label='Carico la directory pubblica dei club…' labelClassName='text-base' />
          ) : (
            <SectionCard sectionId='club-directory' title='Club disponibili'>
              <div className='grid gap-4 lg:grid-cols-2'>
                {clubs.map((club) => {
                  const locationLine = buildLocationLine(club);
                  return (
                    <article key={club.club_id} data-testid='public-club-card' className='surface-card border border-slate-200'>
                      <div className='flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between'>
                        <div>
                          <p className='text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700'>Club pubblico</p>
                          <h2 className='mt-2 text-xl font-semibold text-slate-950'>{club.public_name}</h2>
                          {locationLine ? (
                            <p className='mt-2 flex items-start gap-2 text-sm text-slate-600'>
                              <MapPin size={16} className='mt-0.5 shrink-0 text-cyan-700' />
                              <span>{locationLine}</span>
                            </p>
                          ) : null}
                        </div>
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${club.is_community_open ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-700'}`}>
                          {club.is_community_open ? 'Community aperta' : 'Community privata'}
                        </span>
                      </div>

                      <div className='mt-4 grid gap-3 sm:grid-cols-2'>
                        <div className='surface-muted'>
                          <p className='flex items-center gap-2 text-sm font-semibold text-slate-900'>
                            <UsersRound size={16} /> {club.courts_count} {club.courts_count === 1 ? 'campo' : 'campi'}
                          </p>
                          <p className='mt-2 text-sm text-slate-600'>{formatDistance(club.distance_km)}</p>
                          <p className='mt-2 text-xs font-medium uppercase tracking-[0.14em] text-cyan-700'>Score pubblico {club.public_activity_score}</p>
                        </div>
                        <div className='surface-muted text-sm text-slate-600'>
                          {club.contact_email ? (
                            <p className='flex items-center gap-2'><Mail size={16} className='text-cyan-700' /> {club.contact_email}</p>
                          ) : null}
                          {club.support_phone ? (
                            <p className='mt-2 flex items-center gap-2'><Phone size={16} className='text-cyan-700' /> {club.support_phone}</p>
                          ) : null}
                          {!club.contact_email && !club.support_phone ? <p>Contatti pubblici non disponibili.</p> : null}
                        </div>
                      </div>

                      <div className='mt-3 rounded-2xl border border-cyan-100 bg-cyan-50/70 px-4 py-3 text-sm text-slate-700'>
                        <p className='font-semibold text-slate-900'>{club.public_activity_label}</p>
                        <p className='mt-1'>Match open visibili nei prossimi 7 giorni: {club.recent_open_matches_count}.</p>
                      </div>

                      <div className='mt-4 flex flex-col gap-3 sm:flex-row'>
                        <Link className='btn-primary' to={`/c/${club.club_slug}`}>
                          <Building2 size={16} />
                          <span>Apri pagina club</span>
                        </Link>
                        <button
                          type='button'
                          className='btn-secondary'
                          onClick={() => void toggleWatch(club)}
                          disabled={watchActionClubSlug === club.club_slug}
                        >
                          <BellRing size={16} />
                          <span>
                            {watchActionClubSlug === club.club_slug
                              ? 'Aggiornamento…'
                              : watchlistBySlug.has(club.club_slug)
                                ? 'Rimuovi dalla watchlist'
                                : 'Segui questo club'}
                          </span>
                        </button>
                        <Link className='btn-secondary' to={`/c/${club.club_slug}/play`}>
                          <ArrowRight size={16} />
                          <span>Vai alla community</span>
                        </Link>
                      </div>

                      {watchlistBySlug.has(club.club_slug) ? (
                        <p className='mt-3 text-sm text-emerald-700'>
                          Club seguito. Match compatibili in watchlist: {watchlistBySlug.get(club.club_slug)?.matching_open_match_count ?? 0}.
                        </p>
                      ) : null}
                    </article>
                  );
                })}
              </div>

              {clubs.length === 0 ? (
                <div className='surface-muted text-sm text-slate-700'>Nessun club trovato con i criteri selezionati. Prova una citta, un CAP o una provincia diversa.</div>
              ) : null}
            </SectionCard>
          )}
        </div>
      </div>
    </div>
  );
}