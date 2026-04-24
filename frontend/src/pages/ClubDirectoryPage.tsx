import { ArrowRight, Building2, LocateFixed, Mail, MapPin, Navigation, Phone, Search, UsersRound } from 'lucide-react';
import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { AppBrand } from '../components/AppBrand';
import { LoadingBlock } from '../components/LoadingBlock';
import { SectionCard } from '../components/SectionCard';
import { listPublicClubs, listPublicClubsNearby } from '../services/publicApi';
import type { PublicClubSummary } from '../types';

type FeedbackState = { tone: 'info' | 'warning' | 'error'; message: string } | null;

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

export function ClubDirectoryPage({ autoLocateOnMount = false }: { autoLocateOnMount?: boolean }) {
  const [query, setQuery] = useState('');
  const [clubs, setClubs] = useState<PublicClubSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [locating, setLocating] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState>(null);

  useEffect(() => {
    if (autoLocateOnMount) {
      void requestNearby();
      return;
    }
    void loadClubs();
  }, [autoLocateOnMount]);

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
                        <Link className='btn-secondary' to={`/c/${club.club_slug}/play`}>
                          <ArrowRight size={16} />
                          <span>Vai alla community</span>
                        </Link>
                      </div>
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