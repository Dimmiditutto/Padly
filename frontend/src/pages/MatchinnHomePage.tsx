import { ArrowRight, Building2, CalendarClock, LocateFixed, ShieldCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { LoadingBlock } from '../components/LoadingBlock';
import { SectionCard } from '../components/SectionCard';
import {
  getMatchinnHomeCommunities,
  getMatchinnHomeOpenMatches,
  getPublicDiscoveryMe,
  listPublicClubsNearby,
} from '../services/publicApi';
import type {
  MatchinnHomeOpenMatchItem,
  PlayLevel,
  PublicClubSummary,
  PublicDiscoveryMeResponse,
} from '../types';
import { formatDate, formatTimeValue } from '../utils/format';
import { buildClubPlayPath, formatPlayLevel } from '../utils/play';

type FeedbackState = { tone: 'info' | 'warning' | 'error' | 'success'; message: string } | null;
type LocationSource = 'query' | 'discovery' | 'none';

const NEARBY_CLUBS_LIMIT = 6;
const HOME_MATCH_LIMIT = 6;

function formatDistance(distanceKm: number | null | undefined) {
  if (distanceKm == null) {
    return 'Distanza non disponibile';
  }
  return `${distanceKm.toFixed(1).replace('.', ',')} km`;
}

function buildLocationLine(club: PublicClubSummary) {
  return [club.public_city, club.public_province, club.public_address].filter(Boolean).join(' • ');
}

function buildCommunitySignal(club: PublicClubSummary) {
  if (club.open_matches_three_of_four_count > 0) {
    return 'Manca 1 giocatore';
  }
  if (club.open_matches_two_of_four_count > 0) {
    return 'Mancano 2 giocatori';
  }
  if (club.open_matches_one_of_four_count > 0) {
    return 'Ci sono partite aperte da completare';
  }
  return club.public_activity_label;
}

function geolocationDeniedMessage(error: GeolocationPositionError | { code?: number } | null | undefined) {
  if (error?.code === 1) {
    return 'Permesso geolocalizzazione negato. Usa la directory per cercare manualmente il club giusto.';
  }
  return 'Geolocalizzazione non disponibile in questo momento. Usa la directory per cercare manualmente il club giusto.';
}

export function MatchinnHomePage() {
  const [communities, setCommunities] = useState<PublicClubSummary[]>([]);
  const [communitiesLoading, setCommunitiesLoading] = useState(true);
  const [communitiesFeedback, setCommunitiesFeedback] = useState<FeedbackState>(null);
  const [discovery, setDiscovery] = useState<PublicDiscoveryMeResponse>({
    subscriber: null,
    recent_notifications: [],
    unread_notifications_count: 0,
  });
  const [discoveryLoading, setDiscoveryLoading] = useState(true);
  const [discoveryFeedback, setDiscoveryFeedback] = useState<FeedbackState>(null);
  const [nearbyClubs, setNearbyClubs] = useState<PublicClubSummary[]>([]);
  const [nearbyLoading, setNearbyLoading] = useState(false);
  const [nearbyFeedback, setNearbyFeedback] = useState<FeedbackState>(null);
  const [openMatches, setOpenMatches] = useState<MatchinnHomeOpenMatchItem[]>([]);
  const [openMatchesLoading, setOpenMatchesLoading] = useState(true);
  const [openMatchesFeedback, setOpenMatchesFeedback] = useState<FeedbackState>(null);
  const [locating, setLocating] = useState(false);

  useEffect(() => {
    void loadCommunities();
    void loadDiscoveryContext();
    void loadOpenMatches();
  }, []);

  async function loadCommunities() {
    setCommunitiesLoading(true);
    try {
      const response = await getMatchinnHomeCommunities();
      setCommunities(response.items);
      setCommunitiesFeedback(null);
    } catch {
      setCommunities([]);
      setCommunitiesFeedback({ tone: 'info', message: 'Le community non sono disponibili ora. Puoi comunque aprire un club e rientrare con OTP.' });
    } finally {
      setCommunitiesLoading(false);
    }
  }

  async function loadDiscoveryContext() {
    setDiscoveryLoading(true);
    try {
      const response = await getPublicDiscoveryMe();
      setDiscovery(response);
      setDiscoveryFeedback(null);
      if (response.subscriber?.has_coordinates && response.subscriber.latitude != null && response.subscriber.longitude != null) {
        await loadNearbyClubs(response.subscriber.latitude, response.subscriber.longitude);
      }
    } catch {
      setDiscoveryFeedback({ tone: 'info', message: 'Discovery non disponibile ora. Usa la tua posizione o apri la directory club.' });
    } finally {
      setDiscoveryLoading(false);
    }
  }

  async function loadNearbyClubs(latitude: number, longitude: number) {
    setNearbyLoading(true);
    try {
      const response = await listPublicClubsNearby(latitude, longitude);
      const items = response.items.slice(0, NEARBY_CLUBS_LIMIT);
      setNearbyClubs(items);
      setNearbyFeedback(items.length > 0 ? null : { tone: 'info', message: 'Nessun club vicino trovato con i dati disponibili. Apri la directory per cercare manualmente.' });
    } catch {
      setNearbyClubs([]);
      setNearbyFeedback({ tone: 'info', message: 'I club vicini non sono disponibili ora. Continua dalla directory completa.' });
    } finally {
      setNearbyLoading(false);
    }
  }

  async function loadOpenMatches(position?: { latitude: number; longitude: number }) {
    setOpenMatchesLoading(true);
    try {
      const response = await getMatchinnHomeOpenMatches({
        ...(position ? { latitude: position.latitude, longitude: position.longitude } : {}),
        limit: HOME_MATCH_LIMIT,
      });
      setOpenMatches(response.items);

      if (response.items.length > 0) {
        setOpenMatchesFeedback(null);
      } else if (response.location_source === 'none') {
        setOpenMatchesFeedback({ tone: 'info', message: 'Aggiungi la posizione o attiva discovery per vedere partite aperte vicino a te.' });
      } else {
        setOpenMatchesFeedback({ tone: 'info', message: 'Nessuna partita aperta visibile vicino a te in questo momento.' });
      }
    } catch {
      setOpenMatches([]);
      setOpenMatchesFeedback({ tone: 'info', message: 'Le partite aperte vicine non sono disponibili ora. Apri un club per vedere il dettaglio pubblico.' });
    } finally {
      setOpenMatchesLoading(false);
    }
  }

  function requestCurrentPosition() {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setNearbyFeedback({ tone: 'warning', message: 'Questo browser non supporta la geolocalizzazione. Usa la directory per cercare per citta o provincia.' });
      return;
    }

    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false);
        void Promise.all([
          loadNearbyClubs(position.coords.latitude, position.coords.longitude),
          loadOpenMatches({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
        ]);
      },
      (error) => {
        setLocating(false);
        setNearbyFeedback({ tone: 'warning', message: geolocationDeniedMessage(error) });
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
    );
  }

  const recognizedCommunitySlugs = new Set(communities.map((club) => club.club_slug));
  const discoverySubscriber = discovery.subscriber;

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='page-shell max-w-6xl space-y-6'>
        <header className='product-hero-panel'>
          <div className='product-hero-logo-slot'>
            <img className='product-hero-logo-image' src='/dark.png' alt='Matchinn' />
          </div>
          <div className='product-hero-layout gap-6'>
            <div className='product-hero-copy'>
              <h1 className='max-w-3xl text-3xl font-bold tracking-tight text-white sm:text-4xl sm:leading-tight'>
                Matchinn ti trova il club e la partita giusta. Tu devi solo entrare in campo.
              </h1>
              <div className='mt-6 product-hero-actions'>
                <Link className='hero-action-primary' to='/clubs'>
                  <LocateFixed size={16} />
                  <span>Trova campi vicino a te</span>
                </Link>
                <Link className='hero-action-secondary' to='/clubs'>
                  <CalendarClock size={16} />
                  <span>Scegli il club per prenotare</span>
                </Link>
              </div>
            </div>

            <div className='w-full max-w-sm rounded-[24px] border border-white/10 bg-white/5 p-4 text-white'>
              <p className='text-xs font-semibold uppercase tracking-[0.18em] text-cyan-100/80'>Stato rapido</p>
              <div className='mt-4 space-y-3'>
                <QuickMetric label='Community riconosciute' value={String(communities.length)} />
                <QuickMetric label='Club vicini caricati' value={String(nearbyClubs.length)} />
                <QuickMetric label='Partite aperte in evidenza' value={String(openMatches.length)} />
              </div>
              <div className='mt-4 rounded-2xl border border-white/10 bg-slate-950/30 p-3 text-sm text-slate-200'>
                {discoverySubscriber
                  ? `Discovery attiva: ${formatPlayLevel(discoverySubscriber.preferred_level)} • raggio ${discoverySubscriber.nearby_radius_km} km.`
                  : 'Nessuna discovery salvata: usa la posizione o apri la directory club.'}
              </div>
            </div>
          </div>
        </header>

        <div className='grid items-start gap-6 lg:grid-cols-[1.15fr_0.85fr]'>
          <SectionCard title='Le tue community' elevated>
            {communitiesLoading ? (
              <LoadingBlock label='Cerco le community riconosciute…' labelClassName='text-base' />
            ) : communitiesFeedback ? (
              <AlertBanner tone={communitiesFeedback.tone}>{communitiesFeedback.message}</AlertBanner>
            ) : communities.length === 0 ? (
              <div className='space-y-4 rounded-[24px] border border-dashed border-slate-300 bg-slate-50/90 p-5'>
                <p className='text-sm text-slate-700'>
                  Nessuna community attiva trovata in questo browser. Per entrare o rientrare ti basta aprire il club giusto e richiedere il tuo codice OTP self-service.
                </p>
                <div className='action-cluster'>
                  <Link className='btn-primary' to='/clubs'>Ottieni codice OTP dal tuo club</Link>
                  <Link className='btn-secondary' to='/clubs/nearby'>Scopri club vicini</Link>
                </div>
              </div>
            ) : (
              <div className='grid gap-4 lg:grid-cols-2'>
                {communities.map((club) => (
                  <article key={club.club_id} className='surface-card-compact border border-slate-200'>
                    <div className='flex items-start justify-between gap-3'>
                      <div>
                        <p className='text-xs font-semibold uppercase tracking-[0.16em] text-cyan-700'>Community</p>
                        <h3 className='mt-2 text-lg font-semibold text-slate-950'>{club.public_name}</h3>
                        <p className='mt-1 text-sm text-slate-600'>{buildLocationLine(club) || 'Club riconosciuto da una sessione valida nel browser corrente.'}</p>
                      </div>
                      <span className='rounded-full bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-800'>
                        {club.recent_open_matches_count} open
                      </span>
                    </div>

                    <div className='mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3'>
                      <p className='text-sm font-semibold text-slate-900'>{buildCommunitySignal(club)}</p>
                      <p className='mt-1 text-sm text-slate-600'>{club.public_activity_label}</p>
                    </div>

                    <div className='mt-4 flex items-center justify-between gap-3'>
                      <p className='text-xs text-slate-500'>
                        {club.open_matches_three_of_four_count} x 3/4 • {club.open_matches_two_of_four_count} x 2/4 • {club.open_matches_one_of_four_count} x 1/4
                      </p>
                      <Link
                        className='btn-primary'
                        to={buildClubPlayPath(club.club_slug)}
                        aria-label={`Entra nella community ${club.public_name}`}
                      >
                        Entra
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </SectionCard>

          <div className='space-y-6'>
            <section className='surface-card bg-gradient-to-br from-white to-cyan-50'>
              <div className='flex items-start justify-between gap-4'>
                <div>
                  <p className='text-xs font-semibold uppercase tracking-[0.16em] text-cyan-700'>Posizione</p>
                  <h2 className='mt-2 text-xl font-semibold text-slate-950'>Trova i campi più vicini a te</h2>
                  <p className='mt-2 text-sm text-slate-600'>Usa la geolocalizzazione o cerca un campo</p>
                </div>
                <ShieldCheck size={20} className='shrink-0 text-cyan-700' />
              </div>
              <div className='mt-4 action-cluster'>
                <button type='button' className='btn-primary' onClick={requestCurrentPosition} disabled={locating || nearbyLoading || openMatchesLoading}>
                  <LocateFixed size={16} />
                  <span>{locating ? 'Posizione in corso…' : 'Usa la mia posizione'}</span>
                </button>
                <Link className='btn-secondary' to='/clubs'>Cerca un campo</Link>
              </div>
              {discoveryLoading ? (
                <div className='mt-4'>
                  <LoadingBlock label='Leggo la sessione discovery…' labelClassName='text-sm' />
                </div>
              ) : discoveryFeedback ? (
                <div className='mt-4'>
                  <AlertBanner tone={discoveryFeedback.tone}>{discoveryFeedback.message}</AlertBanner>
                </div>
              ) : discoverySubscriber ? (
                <div className='mt-4 rounded-2xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-700'>
                  Discovery salvata: livello {formatPlayLevel(discoverySubscriber.preferred_level)} • raggio {discoverySubscriber.nearby_radius_km} km • notifiche non lette {discovery.unread_notifications_count}.
                </div>
              ) : null}
            </section>

            <section className='surface-card-compact border border-slate-200'>
              <div className='flex items-start justify-between gap-4'>
                <div>
                  <p className='text-xs font-semibold uppercase tracking-[0.16em] text-slate-500'>Area club</p>
                  <h2 className='mt-2 text-lg font-semibold text-slate-950'>Accesso gestori e admin</h2>
                  <p className='mt-2 text-sm text-slate-600'>Sei un gestore? Entra nella tua dashboard.</p>
                </div>
                <Building2 size={20} className='shrink-0 text-slate-500' />
              </div>
              <div className='mt-4'>
                <Link className='btn-secondary w-full justify-center' to='/admin'>Apri Area club</Link>
              </div>
            </section>
          </div>
        </div>

        <SectionCard
          title='Match da completare'
          description='Scopri le partite aperte nei club della tua zona e unisciti!'
        >
          {openMatchesLoading ? (
            <LoadingBlock label='Cerco partite aperte vicine…' labelClassName='text-base' />
          ) : openMatchesFeedback ? (
            <AlertBanner tone={openMatchesFeedback.tone}>{openMatchesFeedback.message}</AlertBanner>
          ) : (
            <div className='grid gap-4 md:grid-cols-2 xl:grid-cols-3'>
              {openMatches.map((item) => {
                const canEnterDirectly = recognizedCommunitySlugs.has(item.club.club_slug);
                return (
                  <article key={`${item.club.club_id}-${item.match.id}`} className='surface-card-compact border border-slate-200'>
                    <div className='flex items-start justify-between gap-3'>
                      <div>
                        <p className='text-xs font-semibold uppercase tracking-[0.16em] text-cyan-700'>{item.match.occupancy_label}</p>
                        <h3 className='mt-2 text-lg font-semibold text-slate-950'>{formatDate(item.match.start_at)}</h3>
                        <p className='mt-1 text-sm text-slate-600'>
                          {formatTimeValue(item.match.start_at)} - {formatTimeValue(item.match.end_at)}
                        </p>
                      </div>
                      <span className='rounded-full bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-800'>{formatPlayLevel(item.match.level_requested)}</span>
                    </div>

                    <div className='mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3'>
                      <p className='text-sm font-semibold text-slate-900'>{item.match.missing_players_message}</p>
                      <p className='mt-1 text-sm text-slate-600'>{item.club.public_name} • {formatDistance(item.club.distance_km)}</p>
                    </div>

                    <div className='mt-4 flex items-center justify-between gap-3'>
                      <span className='text-xs text-slate-500'>{buildLocationLine(item.club) || 'Club pubblico visibile'}</span>
                      <Link
                        className='btn-primary'
                        to={canEnterDirectly ? buildClubPlayPath(item.club.club_slug) : `/c/${encodeURIComponent(item.club.club_slug)}`}
                        aria-label={`${canEnterDirectly ? 'Entra e gioca' : 'Apri club'} ${item.club.public_name}`}
                      >
                        {canEnterDirectly ? 'Entra e gioca' : 'Apri club'}
                        <ArrowRight size={16} />
                      </Link>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  );
}

function QuickMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className='flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/5 px-3 py-2.5'>
      <span className='text-sm text-slate-200'>{label}</span>
      <span className='inline-flex min-w-9 items-center justify-center rounded-full bg-white/10 px-2.5 py-1 text-sm font-semibold text-white'>
        {value}
      </span>
    </div>
  );
}