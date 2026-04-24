import { ArrowLeft, Clock3, Mail, MapPin, Phone, UsersRound } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { AppBrand } from '../components/AppBrand';
import { LoadingBlock } from '../components/LoadingBlock';
import { SectionCard } from '../components/SectionCard';
import { getPublicClubDetail } from '../services/publicApi';
import type { PlayLevel, PublicClubDetailResponse } from '../types';
import { formatDate, formatTimeValue } from '../utils/format';
import { buildClubPlayPath, formatPlayLevel, PLAY_LEVEL_OPTIONS } from '../utils/play';

type LevelFilter = 'ALL' | PlayLevel;

function formatWeekday(dateValue: string, timeZone: string) {
  const label = new Intl.DateTimeFormat('it-IT', { weekday: 'long', timeZone }).format(new Date(dateValue));
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function buildLocationLine(payload: PublicClubDetailResponse['club']) {
  return [payload.public_address, payload.public_postal_code, payload.public_city, payload.public_province].filter(Boolean).join(' • ');
}

export function PublicClubPage() {
  const { clubSlug } = useParams();
  const [detail, setDetail] = useState<PublicClubDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ tone: 'error' | 'warning'; message: string } | null>(null);
  const [selectedLevel, setSelectedLevel] = useState<LevelFilter>('ALL');

  useEffect(() => {
    if (!clubSlug) {
      setLoading(false);
      setFeedback({ tone: 'error', message: 'Club pubblico non valido.' });
      return;
    }
    void loadDetail(clubSlug, selectedLevel === 'ALL' ? null : selectedLevel);
  }, [clubSlug, selectedLevel]);

  async function loadDetail(resolvedClubSlug: string, level: PlayLevel | null) {
    setLoading(true);
    setFeedback(null);
    try {
      const response = await getPublicClubDetail(resolvedClubSlug, level);
      setDetail(response);
    } catch {
      setFeedback({ tone: 'error', message: 'Non riesco a caricare la pagina pubblica del club.' });
    } finally {
      setLoading(false);
    }
  }

  const levelOptions = useMemo(() => PLAY_LEVEL_OPTIONS.filter((option) => option.value !== 'NO_PREFERENCE'), []);

  if (!clubSlug) {
    return (
      <div className='page-shell max-w-4xl'>
        <AlertBanner tone='error'>Club pubblico non valido.</AlertBanner>
      </div>
    );
  }

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='page-shell max-w-6xl'>
        {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

        {loading ? (
          <LoadingBlock label='Carico la pagina pubblica del club…' labelClassName='text-base' />
        ) : detail ? (
          <>
            <header className='rounded-[28px] border border-cyan-400/20 bg-slate-950/80 p-6 text-white shadow-soft'>
              <div className='flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between'>
                <div className='max-w-3xl'>
                  <AppBrand light label='Club pubblico' />
                  <h1 className='mt-4 text-3xl font-bold tracking-tight text-white sm:text-4xl'>{detail.club.public_name}</h1>
                  <p className='mt-3 text-sm leading-6 text-slate-300 sm:text-base'>La pagina pubblica del club mostra solo identita minima e partite open sintetiche. Nomi dei player, join e funzioni community restano private.</p>
                  {buildLocationLine(detail.club) ? (
                    <p className='mt-4 flex items-start gap-2 text-sm text-slate-200'>
                      <MapPin size={16} className='mt-0.5 shrink-0 text-cyan-200' />
                      <span>{buildLocationLine(detail.club)}</span>
                    </p>
                  ) : null}
                </div>

                <div className='flex flex-col gap-3 sm:flex-row'>
                  <Link className='btn-secondary' to='/clubs'>
                    <ArrowLeft size={16} />
                    <span>Torna ai club</span>
                  </Link>
                  <Link className='btn-primary' to={buildClubPlayPath(detail.club.club_slug)}>
                    <UsersRound size={16} />
                    <span>{detail.club.is_community_open ? 'Entra nella community' : 'Apri la community privata'}</span>
                  </Link>
                </div>
              </div>
            </header>

            <div className='mt-6 grid gap-6 lg:grid-cols-[0.95fr_1.05fr]'>
              <SectionCard title='Informazioni pubbliche' description='Contatti minimi, presenza nell app e stato di apertura della community.' elevated>
                <div className='space-y-4'>
                  <div className='surface-muted'>
                    <p className='text-sm font-semibold text-slate-900'>Stato community</p>
                    <p className='mt-2 text-sm text-slate-600'>{detail.club.is_community_open ? 'Il club accetta nuovi ingressi nella community.' : 'La community del club resta privata e l accesso va richiesto.'}</p>
                  </div>
                  <div className='grid gap-3 sm:grid-cols-2'>
                    <div className='surface-muted'>
                      <p className='text-sm font-semibold text-slate-900'>Campi attivi</p>
                      <p className='mt-2 text-2xl font-semibold text-slate-950'>{detail.club.courts_count}</p>
                    </div>
                    <div className='surface-muted'>
                      <p className='text-sm font-semibold text-slate-900'>Finestra partite open</p>
                      <p className='mt-2 text-sm text-slate-600'>Mostriamo solo i prossimi {detail.public_match_window_days} giorni utili.</p>
                    </div>
                  </div>
                  <div className='surface-muted text-sm text-slate-600'>
                    {detail.club.contact_email ? <p className='flex items-center gap-2'><Mail size={16} className='text-cyan-700' /> {detail.club.contact_email}</p> : null}
                    {detail.support_phone ? <p className='mt-2 flex items-center gap-2'><Phone size={16} className='text-cyan-700' /> {detail.support_phone}</p> : null}
                    {!detail.club.contact_email && !detail.support_phone ? <p>Contatti pubblici non disponibili.</p> : null}
                  </div>
                </div>
              </SectionCard>

              <SectionCard title='Partite open del club' description='Solo vista pubblica leggera: niente nomi dei player, niente join diretto, solo segnali utili per capire se il club fa al caso tuo.'>
                <div className='space-y-4'>
                  <div className='grid gap-3 sm:grid-cols-[minmax(0,1fr)_220px] sm:items-end'>
                    <div className='surface-muted'>
                      <p className='text-sm text-slate-600'>Filtra le partite open per livello e poi passa alla community del club per agire.</p>
                    </div>
                    <div>
                      <label className='field-label' htmlFor='public-club-level-filter'>Livello</label>
                      <select id='public-club-level-filter' className='text-input' value={selectedLevel} onChange={(event) => setSelectedLevel(event.target.value as LevelFilter)}>
                        <option value='ALL'>Tutti i livelli</option>
                        {levelOptions.map((option) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {detail.open_matches.length === 0 ? (
                    <div className='surface-muted text-sm text-slate-700'>Nessuna partita open pubblica disponibile con i filtri correnti.</div>
                  ) : (
                    <div className='space-y-3'>
                      {detail.open_matches.map((match) => (
                        <article key={match.id} data-testid='public-open-match-card' className='rounded-2xl border border-slate-200 bg-white px-4 py-4'>
                          <div className='flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between'>
                            <div>
                              <p className='text-sm font-semibold text-slate-900'>{formatWeekday(match.start_at, detail.timezone)} • {formatDate(match.start_at)}</p>
                              <p className='mt-1 flex items-center gap-2 text-sm text-slate-600'>
                                <Clock3 size={16} className='text-cyan-700' />
                                <span>{formatTimeValue(match.start_at, detail.timezone)} - {formatTimeValue(match.end_at, detail.timezone)}</span>
                              </p>
                              <p className='mt-2 text-sm text-slate-600'>{match.court_name || 'Campo del club'}{match.court_badge_label ? ` • ${match.court_badge_label}` : ''}</p>
                            </div>
                            <div className='flex flex-col gap-2 lg:items-end'>
                              <span className='rounded-full bg-cyan-100 px-3 py-1 text-xs font-semibold text-cyan-800'>{formatPlayLevel(match.level_requested)}</span>
                              <span className='rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700'>{match.occupancy_label}</span>
                            </div>
                          </div>
                          <p className='mt-3 text-sm font-medium text-slate-900'>{match.missing_players_message}</p>
                          <p className='mt-1 text-sm text-slate-600'>Per unirti devi passare dalla community del club. La pagina pubblica non mostra nomi dei partecipanti o dettagli interni.</p>
                        </article>
                      ))}
                    </div>
                  )}
                </div>
              </SectionCard>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}