import { AxiosError } from 'axios';
import { ArrowRight, BellRing, Building2, LocateFixed, Mail, MapPin, Phone, Search, UsersRound } from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { AppBrand } from '../components/AppBrand';
import { LoadingBlock } from '../components/LoadingBlock';
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

const DEFAULT_DISCOVERY_TIME_SLOTS: PublicDiscoveryTimeSlot[] = ['morning', 'afternoon', 'evening'];
const DISCOVERY_TIME_SLOT_OPTIONS: Array<{ value: PublicDiscoveryTimeSlot; label: string }> = [
  { value: 'morning', label: 'Mattina' },
  { value: 'afternoon', label: 'Pomeriggio' },
  { value: 'evening', label: 'Sera' },
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

function createDiscoveryFormFromSession(subscriber: PublicDiscoverySession): DiscoveryFormState {
  return {
    preferred_level: subscriber.preferred_level,
    preferred_time_slots: subscriber.preferred_time_slots.length ? subscriber.preferred_time_slots : [...DEFAULT_DISCOVERY_TIME_SLOTS],
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

  function toggleDiscoveryTimeSlot(slot: PublicDiscoveryTimeSlot) {
    setDiscoveryForm((prev) => ({
      ...prev,
      preferred_time_slots: prev.preferred_time_slots.includes(slot)
        ? prev.preferred_time_slots.filter((item) => item !== slot)
        : [...prev.preferred_time_slots, slot],
    }));
  }

  async function requestDiscoveryCoordinates() {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setDiscoveryFeedback({ tone: 'warning', message: 'Questo browser non supporta la geolocalizzazione per il digest discovery.' });
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
        setDiscoveryFeedback({ tone: 'success', message: 'Posizione aggiornata nelle preferenze discovery.' });
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
      preferred_time_slots: discoveryForm.preferred_time_slots,
      latitude: parseOptionalNumber(discoveryForm.latitude),
      longitude: parseOptionalNumber(discoveryForm.longitude),
      nearby_radius_km: Number(discoveryForm.nearby_radius_km) || 25,
      nearby_digest_enabled: discoveryForm.nearby_digest_enabled,
    };

    try {
      if (discovery.subscriber) {
        await updatePublicDiscoveryPreferences(payload);
        setDiscoveryFeedback({ tone: 'success', message: 'Preferenze discovery aggiornate.' });
        await loadDiscoveryContext();
      } else {
        const response = await identifyPublicDiscovery({ ...payload, privacy_accepted: discoveryForm.privacy_accepted });
        setDiscovery(response);
        if (response.subscriber) {
          setDiscoveryForm(createDiscoveryFormFromSession(response.subscriber));
          const watchlistResponse = await listPublicWatchlist();
          setWatchlist(watchlistResponse.items);
        }
        setDiscoveryFeedback({ tone: 'success', message: 'Sessione discovery attivata. Ora puoi seguire i club.' });
      }
    } catch (error) {
      setDiscoveryFeedback({ tone: 'error', message: parseApiError(error, 'Salvataggio preferenze discovery non riuscito.') });
    } finally {
      setDiscoverySubmitting(false);
    }
  }

  async function toggleWatch(club: PublicClubSummary) {
    if (!discovery.subscriber) {
      setDiscoveryFeedback({ tone: 'info', message: 'Attiva prima la sessione discovery per seguire un club.' });
      return;
    }

    setWatchActionClubSlug(club.club_slug);
    setDiscoveryFeedback(null);
    try {
      if (watchlistBySlug.has(club.club_slug)) {
        await unfollowPublicClub(club.club_slug);
        setDiscoveryFeedback({ tone: 'success', message: `${club.public_name} rimosso dalla watchlist.` });
      } else {
        await followPublicClub(club.club_slug);
        setDiscoveryFeedback({ tone: 'success', message: `${club.public_name} aggiunto alla watchlist.` });
      }
      await loadDiscoveryContext();
    } catch (error) {
      setDiscoveryFeedback({ tone: 'error', message: parseApiError(error, 'Aggiornamento watchlist non riuscito.') });
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
      setDiscoveryFeedback({ tone: 'success', message: 'Notifica segnata come letta.' });
    } catch (error) {
      setDiscoveryFeedback({ tone: 'error', message: parseApiError(error, 'Aggiornamento stato notifica non riuscito.') });
    } finally {
      setReadingNotificationId(null);
    }
  }

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='page-shell max-w-6xl'>
        <header className='rounded-[28px] border border-cyan-400/20 bg-slate-950/80 p-6 text-white shadow-soft'>
          <div className='flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between'>
            <div className='max-w-3xl'>
              <AppBrand light label='Club pubblici' />
              <h1 className='mt-4 text-3xl font-bold tracking-tight text-white sm:text-4xl'>Trova un club del network prima di entrare nella community</h1>
              <p className='mt-3 text-sm leading-6 text-slate-300 sm:text-base'>La directory pubblica mostra solo i dati minimi utili del club. La community resta privata: qui scopri, poi decidi se vale la pena entrare.</p>
            </div>
            <div className='surface-muted max-w-sm bg-white/10 text-white'>
              <p className='text-sm font-semibold text-cyan-100'>Ricerca senza servizi esterni</p>
              <p className='mt-2 text-sm leading-6 text-slate-200'>Cerca manualmente per citta, CAP o provincia, oppure usa la posizione del browser per ordinare i club vicini.</p>
            </div>
          </div>
        </header>

        <div className='mt-6 space-y-6'>
          {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

          <SectionCard
            title={autoLocateOnMount ? 'Club vicini a me' : 'Directory club'}
            description='Ricerca manuale sempre disponibile. Geolocalizzazione opzionale e limitata all ordinamento per distanza.'
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
                <span>{locating ? 'Rilevamento…' : autoLocateOnMount ? 'Riprova geolocalizzazione' : 'Trova club vicino a me'}</span>
              </button>
            </form>
          </SectionCard>

          <SectionCard
            title='Discovery pubblico'
            description='Sessione minima separata dalla community: preferenze leggere, watchlist club e feed persistente degli alert utili.'
            elevated
          >
            {discoveryFeedback ? <AlertBanner tone={discoveryFeedback.tone}>{discoveryFeedback.message}</AlertBanner> : null}

            {discoveryLoading ? (
              <LoadingBlock label='Carico la sessione discovery…' labelClassName='text-sm' />
            ) : (
              <div className='space-y-5'>
                <div className='surface-muted'>
                  <p className='text-sm font-semibold text-slate-900'>
                    {discovery.subscriber ? 'Sessione discovery attiva' : 'Attiva una sessione discovery leggera'}
                  </p>
                  <p className='mt-2 text-sm leading-6 text-slate-600'>
                    {discovery.subscriber
                      ? 'Le preferenze restano su cookie discovery dedicato e pilotano watchlist, alert 2/4-3/4 e digest vicino.'
                      : 'Non crei ancora un profilo player: salvi solo livello, fasce orarie, posizione opzionale e consenso privacy per il feed pubblico.'}
                  </p>
                </div>

                <form className='grid gap-4 lg:grid-cols-2' onSubmit={handleDiscoverySubmit}>
                  <div>
                    <label className='field-label' htmlFor='discovery-level'>Livello preferito</label>
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
                    <label className='field-label' htmlFor='discovery-radius'>Raggio digest vicino (km)</label>
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
                    <label className='field-label' htmlFor='discovery-latitude'>Latitudine</label>
                    <input
                      id='discovery-latitude'
                      className='text-input'
                      type='number'
                      step='0.000001'
                      min={-90}
                      max={90}
                      value={discoveryForm.latitude}
                      onChange={(event) => setDiscoveryForm((prev) => ({ ...prev, latitude: event.target.value }))}
                    />
                  </div>

                  <div>
                    <label className='field-label' htmlFor='discovery-longitude'>Longitudine</label>
                    <input
                      id='discovery-longitude'
                      className='text-input'
                      type='number'
                      step='0.000001'
                      min={-180}
                      max={180}
                      value={discoveryForm.longitude}
                      onChange={(event) => setDiscoveryForm((prev) => ({ ...prev, longitude: event.target.value }))}
                    />
                  </div>

                  <div className='lg:col-span-2'>
                    <p className='field-label'>Fasce orarie utili</p>
                    <div className='mt-2 flex flex-wrap gap-3'>
                      {DISCOVERY_TIME_SLOT_OPTIONS.map((slot) => (
                        <label key={slot.value} className='flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700'>
                          <input
                            type='checkbox'
                            checked={discoveryForm.preferred_time_slots.includes(slot.value)}
                            onChange={() => toggleDiscoveryTimeSlot(slot.value)}
                            className='h-4 w-4 rounded border-slate-300'
                          />
                          <span>{slot.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className='lg:col-span-2 flex flex-col gap-3 rounded-2xl border border-slate-200 p-4 text-sm text-slate-700 sm:flex-row sm:items-start sm:justify-between'>
                    <div>
                      <p className='font-semibold text-slate-900'>Posizione browser opzionale</p>
                      <p className='mt-1 text-sm leading-6 text-slate-600'>La posizione serve solo per ordinare club vicini e per il digest giornaliero, non per sbloccare accessi community.</p>
                    </div>
                    <button type='button' className='btn-secondary' onClick={() => void requestDiscoveryCoordinates()} disabled={locatingDiscovery}>
                      <LocateFixed size={16} />
                      <span>{locatingDiscovery ? 'Rilevamento…' : 'Usa la posizione del browser'}</span>
                    </button>
                  </div>

                  <label className='lg:col-span-2 flex items-start gap-3 rounded-2xl border border-slate-200 p-4 text-sm text-slate-700'>
                    <input
                      type='checkbox'
                      checked={discoveryForm.nearby_digest_enabled}
                      onChange={(event) => setDiscoveryForm((prev) => ({ ...prev, nearby_digest_enabled: event.target.checked }))}
                      className='mt-1 h-4 w-4 rounded border-slate-300'
                    />
                    <span>Attiva digest giornaliero dei club vicini con match aperti compatibili.</span>
                  </label>

                  <label className='lg:col-span-2 flex items-start gap-3 rounded-2xl border border-slate-200 p-4 text-sm text-slate-700'>
                    <input
                      type='checkbox'
                      checked={discoveryForm.privacy_accepted}
                      onChange={(event) => setDiscoveryForm((prev) => ({ ...prev, privacy_accepted: event.target.checked }))}
                      className='mt-1 h-4 w-4 rounded border-slate-300'
                      required={!discovery.subscriber}
                    />
                    <span>Accetto il trattamento dei dati per salvare la sessione discovery pubblica e ricevere alert nel feed.</span>
                  </label>

                  <div className='lg:col-span-2 flex flex-col gap-3 sm:flex-row'>
                    <button className='btn-primary' type='submit' disabled={discoverySubmitting}>
                      <BellRing size={16} />
                      <span>{discoverySubmitting ? 'Salvataggio…' : discovery.subscriber ? 'Aggiorna preferenze discovery' : 'Attiva discovery pubblico'}</span>
                    </button>
                    {discovery.subscriber ? (
                      <div className='surface-muted text-sm text-slate-600'>
                        Watchlist attuale: <strong>{watchlist.length}</strong> club seguiti.
                      </div>
                    ) : null}
                  </div>
                </form>

                <div className='grid gap-4 lg:grid-cols-2'>
                  <div className='surface-card border border-slate-200'>
                    <p className='text-sm font-semibold text-slate-900'>Watchlist club</p>
                    <div className='mt-3 space-y-3'>
                      {watchlist.length === 0 ? (
                        <p className='text-sm text-slate-600'>Nessun club seguito per ora. Attiva discovery e usa i pulsanti “Segui questo club” nelle card della directory.</p>
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
                      <p className='text-sm font-semibold text-slate-900'>Feed discovery persistente</p>
                      <span className='rounded-full bg-cyan-100 px-3 py-1 text-xs font-semibold text-cyan-800'>Non lette: {discovery.unread_notifications_count}</span>
                    </div>
                    <div className='mt-3 space-y-3'>
                      {discovery.recent_notifications.length === 0 ? (
                        <p className='text-sm text-slate-600'>Ancora nessun alert. Il feed si popola con watchlist 2/4-3/4 e digest giornalieri vicini.</p>
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
            <SectionCard title='Club disponibili' description='Ogni card espone solo identita pubblica, contatto minimo e stato community del club.'>
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