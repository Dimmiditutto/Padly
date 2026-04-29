import { AxiosError } from 'axios';
import { ArrowLeft, BellRing, Clock3, Mail, MapPin, Phone, UsersRound } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { AppBrand } from '../components/AppBrand';
import { LoadingBlock } from '../components/LoadingBlock';
import { SectionCard } from '../components/SectionCard';
import {
  createPublicClubContactRequest,
  followPublicClub,
  getPublicClubDetail,
  getPublicDiscoveryMe,
  listPublicWatchlist,
  unfollowPublicClub,
} from '../services/publicApi';
import type { PlayLevel, PublicClubDetailResponse, PublicClubWatchSummary, PublicDiscoveryMeResponse } from '../types';
import { formatDate, formatTimeValue } from '../utils/format';
import { buildClubPlayPath, formatPlayLevel, PLAY_LEVEL_OPTIONS } from '../utils/play';

type LevelFilter = 'ALL' | PlayLevel;
type FeedbackState = { tone: 'error' | 'warning' | 'success' | 'info'; message: string } | null;
type ContactFormState = {
  name: string;
  email: string;
  phone: string;
  preferred_level: PlayLevel;
  note: string;
  privacy_accepted: boolean;
};

function formatWeekday(dateValue: string, timeZone: string) {
  const label = new Intl.DateTimeFormat('it-IT', { weekday: 'long', timeZone }).format(new Date(dateValue));
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function buildLocationLine(payload: PublicClubDetailResponse['club']) {
  return [payload.public_address, payload.public_postal_code, payload.public_city, payload.public_province].filter(Boolean).join(' • ');
}

function createDefaultContactForm(): ContactFormState {
  return {
    name: '',
    email: '',
    phone: '',
    preferred_level: 'NO_PREFERENCE',
    note: '',
    privacy_accepted: false,
  };
}

function parseApiError(error: unknown, fallback: string) {
  const requestError = error as AxiosError<{ detail?: string }>;
  return requestError.response?.data?.detail || fallback;
}

function buildPriorityGroups(matches: PublicClubDetailResponse['open_matches']) {
  return [
    {
      key: 'three-of-four',
      title: 'Da chiudere subito',
      badge: '3/4',
      description: 'Le occasioni piu semplici da convertire: manca solo un giocatore.',
      items: matches.filter((match) => match.participant_count >= 3),
    },
    {
      key: 'two-of-four',
      title: 'Buone occasioni',
      badge: '2/4',
      description: 'Match gia avviati: utili se stai valutando il club e vuoi capire dove c e movimento.',
      items: matches.filter((match) => match.participant_count === 2),
    },
    {
      key: 'one-of-four',
      title: 'Da monitorare',
      badge: '1/4',
      description: 'Partite ancora agli inizi ma gia pubblicamente visibili per il tuo livello.',
      items: matches.filter((match) => match.participant_count === 1),
    },
  ].filter((group) => group.items.length > 0);
}

export function PublicClubPage() {
  const { clubSlug } = useParams();
  const [detail, setDetail] = useState<PublicClubDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<FeedbackState>(null);
  const [selectedLevel, setSelectedLevel] = useState<LevelFilter>('ALL');
  const [discovery, setDiscovery] = useState<PublicDiscoveryMeResponse>({
    subscriber: null,
    recent_notifications: [],
    unread_notifications_count: 0,
  });
  const [watchlist, setWatchlist] = useState<PublicClubWatchSummary[]>([]);
  const [discoveryLoading, setDiscoveryLoading] = useState(true);
  const [watchActionLoading, setWatchActionLoading] = useState(false);
  const [contactSubmitting, setContactSubmitting] = useState(false);
  const [contactFeedback, setContactFeedback] = useState<FeedbackState>(null);
  const [contactForm, setContactForm] = useState<ContactFormState>(() => createDefaultContactForm());

  useEffect(() => {
    if (!clubSlug) {
      setLoading(false);
      setFeedback({ tone: 'error', message: 'Club pubblico non valido.' });
      return;
    }
    void loadDetail(clubSlug, selectedLevel === 'ALL' ? null : selectedLevel);
  }, [clubSlug, selectedLevel]);

  useEffect(() => {
    if (!clubSlug) {
      return;
    }
    void loadDiscoveryContext();
  }, [clubSlug]);

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

  async function loadDiscoveryContext() {
    setDiscoveryLoading(true);
    try {
      const response = await getPublicDiscoveryMe();
      setDiscovery(response);
      if (response.subscriber) {
        const watchlistResponse = await listPublicWatchlist();
        setWatchlist(watchlistResponse.items);
        setContactForm((prev) => ({
          ...prev,
          preferred_level: prev.preferred_level === 'NO_PREFERENCE' ? response.subscriber!.preferred_level : prev.preferred_level,
        }));
      } else {
        setWatchlist([]);
      }
    } catch {
      setFeedback({ tone: 'warning', message: 'Non riesco a leggere la tua sessione discovery pubblica.' });
    } finally {
      setDiscoveryLoading(false);
    }
  }

  const levelOptions = useMemo(() => PLAY_LEVEL_OPTIONS.filter((option) => option.value !== 'NO_PREFERENCE'), []);
  const watchItem = useMemo(
    () => watchlist.find((item) => item.club.club_slug === clubSlug),
    [clubSlug, watchlist]
  );
  const priorityGroups = useMemo(() => (detail ? buildPriorityGroups(detail.open_matches) : []), [detail]);

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
        {contactFeedback ? <AlertBanner tone={contactFeedback.tone}>{contactFeedback.message}</AlertBanner> : null}

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
                  {detail.club.is_community_open ? (
                    <Link className='btn-primary' to={buildClubPlayPath(detail.club.club_slug)}>
                      <UsersRound size={16} />
                      <span>Entra nella community</span>
                    </Link>
                  ) : (
                    <a className='btn-primary' href='#club-contact-request'>
                      <Mail size={16} />
                      <span>Richiedi accesso</span>
                    </a>
                  )}
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
                  <div className='surface-muted'>
                    <p className='text-sm font-semibold text-slate-900'>Discovery pubblico</p>
                    <p className='mt-2 text-sm text-slate-600'>
                      {watchItem
                        ? `Stai seguendo questo club. Match compatibili ora visibili in watchlist: ${watchItem.matching_open_match_count}.`
                        : discovery.subscriber
                          ? 'Puoi seguire questo club per ricevere alert 2/4, 3/4 e tenerlo nella watchlist pubblica.'
                          : 'Per seguire il club devi prima attivare la sessione discovery dalla directory pubblica.'}
                    </p>
                    <div className='mt-3 flex flex-col gap-3 sm:flex-row'>
                      <button
                        type='button'
                        className='btn-secondary'
                        disabled={watchActionLoading || discoveryLoading}
                        onClick={() => void (async () => {
                          if (!clubSlug) {
                            return;
                          }
                          if (!discovery.subscriber) {
                            setContactFeedback({ tone: 'info', message: 'Attiva discovery dalla directory per seguire i club pubblici.' });
                            return;
                          }
                          setWatchActionLoading(true);
                          setContactFeedback(null);
                          try {
                            if (watchItem) {
                              await unfollowPublicClub(clubSlug);
                              setContactFeedback({ tone: 'success', message: 'Club rimosso dalla watchlist pubblica.' });
                            } else {
                              await followPublicClub(clubSlug);
                              setContactFeedback({ tone: 'success', message: 'Club aggiunto alla watchlist pubblica.' });
                            }
                            await loadDiscoveryContext();
                          } catch (error) {
                            setContactFeedback({ tone: 'error', message: parseApiError(error, 'Aggiornamento watchlist non riuscito.') });
                          } finally {
                            setWatchActionLoading(false);
                          }
                        })()}
                      >
                        <BellRing size={16} />
                        <span>
                          {watchActionLoading
                            ? 'Aggiornamento…'
                            : watchItem
                              ? 'Rimuovi dalla watchlist'
                              : 'Segui questo club'}
                        </span>
                      </button>
                      <Link className='btn-secondary' to='/clubs'>
                        <span>{discovery.subscriber ? 'Apri feed discovery' : 'Attiva discovery'}</span>
                      </Link>
                    </div>
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
                  <div className='surface-muted'>
                    <p className='text-sm font-semibold text-slate-900'>Ranking pubblico minimo</p>
                    <p className='mt-2 text-sm text-slate-600'>{detail.club.public_activity_label}</p>
                    <p className='mt-2 text-sm text-slate-600'>Score pubblico {detail.club.public_activity_score} calcolato su {detail.club.recent_open_matches_count} match open visibili nei prossimi {detail.public_match_window_days} giorni.</p>
                  </div>
                  <div className='surface-muted text-sm text-slate-600'>
                    {detail.club.contact_email ? <p className='flex items-center gap-2'><Mail size={16} className='text-cyan-700' /> {detail.club.contact_email}</p> : null}
                    {detail.support_phone ? <p className='mt-2 flex items-center gap-2'><Phone size={16} className='text-cyan-700' /> {detail.support_phone}</p> : null}
                    {!detail.club.contact_email && !detail.support_phone ? <p>Contatti pubblici non disponibili.</p> : null}
                  </div>
                </div>
              </SectionCard>

              <SectionCard title='Partite da chiudere' description='Vista pubblica leggera e orientata alla scoperta: prima le occasioni piu vicine a chiudersi, poi il resto.'>
                <div className='space-y-4'>
                  <div className='grid gap-3 sm:grid-cols-[minmax(0,1fr)_220px] sm:items-end'>
                    <div className='surface-muted'>
                      <p className='text-sm text-slate-600'>Filtra per livello, valuta dove ci sono piu probabilita di chiudere un match e poi scegli se entrare nella community o richiedere accesso.</p>
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
                    <div className='space-y-5'>
                      {priorityGroups.map((group) => (
                        <section key={group.key} data-testid='public-match-priority-group' className='space-y-3'>
                          <div className='surface-muted'>
                            <div className='flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between'>
                              <div>
                                <p className='text-sm font-semibold text-slate-900'>{group.title}</p>
                                <p className='mt-1 text-sm text-slate-600'>{group.description}</p>
                              </div>
                              <span className='rounded-full bg-slate-950 px-3 py-1 text-xs font-semibold text-white'>{group.badge}</span>
                            </div>
                          </div>

                          {group.items.map((match) => (
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
                              <p className='mt-1 text-sm text-slate-600'>Per agire devi passare dalla community del club. Qui vedi solo segnali pubblici: nessun nome partecipante, nessun dettaglio interno.</p>
                            </article>
                          ))}
                        </section>
                      ))}
                    </div>
                  )}
                </div>
              </SectionCard>
            </div>

            <div className='mt-6 grid gap-6 lg:grid-cols-[1.05fr_0.95fr]'>
              <SectionCard
                sectionId='club-contact-request'
                title={detail.club.is_community_open ? 'Richiedi contatto al club' : 'Richiedi accesso alla community'}
                description={detail.club.is_community_open ? 'Flusso guidato per chi non vuole entrare subito nella community o ha bisogno di un contatto umano.' : 'Se la community del club e chiusa, usa questo passaggio pubblico per chiedere accesso senza esporre dati interni del club.'}
                elevated
              >
                <form
                  className='grid gap-4 sm:grid-cols-2'
                  onSubmit={(event) => {
                    event.preventDefault();
                    if (!clubSlug) {
                      return;
                    }
                    void (async () => {
                      setContactSubmitting(true);
                      setContactFeedback(null);
                      try {
                        const response = await createPublicClubContactRequest(clubSlug, {
                          name: contactForm.name,
                          email: contactForm.email || null,
                          phone: contactForm.phone || null,
                          preferred_level: contactForm.preferred_level,
                          note: contactForm.note || null,
                          privacy_accepted: contactForm.privacy_accepted,
                        });
                        setContactFeedback({ tone: 'success', message: response.message });
                        setContactForm((prev) => ({ ...prev, note: '', privacy_accepted: false }));
                      } catch (error) {
                        setContactFeedback({ tone: 'error', message: parseApiError(error, 'Invio richiesta contatto non riuscito.') });
                      } finally {
                        setContactSubmitting(false);
                      }
                    })();
                  }}
                >
                  <div>
                    <label className='field-label' htmlFor='club-contact-name'>Nome</label>
                    <input id='club-contact-name' className='text-input' value={contactForm.name} onChange={(event) => setContactForm((prev) => ({ ...prev, name: event.target.value }))} required />
                  </div>
                  <div>
                    <label className='field-label' htmlFor='club-contact-level'>Livello dichiarato</label>
                    <select id='club-contact-level' className='text-input' value={contactForm.preferred_level} onChange={(event) => setContactForm((prev) => ({ ...prev, preferred_level: event.target.value as PlayLevel }))}>
                      {PLAY_LEVEL_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className='field-label' htmlFor='club-contact-email'>Email</label>
                    <input id='club-contact-email' className='text-input' type='email' value={contactForm.email} onChange={(event) => setContactForm((prev) => ({ ...prev, email: event.target.value }))} />
                  </div>
                  <div>
                    <label className='field-label' htmlFor='club-contact-phone'>Telefono</label>
                    <input id='club-contact-phone' className='text-input' value={contactForm.phone} onChange={(event) => setContactForm((prev) => ({ ...prev, phone: event.target.value }))} />
                  </div>
                  <div className='sm:col-span-2'>
                    <label className='field-label' htmlFor='club-contact-note'>Messaggio</label>
                    <textarea id='club-contact-note' className='text-input min-h-24' value={contactForm.note} onChange={(event) => setContactForm((prev) => ({ ...prev, note: event.target.value }))} placeholder={detail.club.is_community_open ? 'Dimmi se vuoi informazioni su community, livello, orari o modalità di ingresso.' : 'Spiega perche vuoi entrare nella community, il tuo livello e quando ti piacerebbe giocare.'} />
                  </div>
                  <label className='sm:col-span-2 flex items-start gap-3 rounded-2xl border border-slate-200 p-4 text-sm text-slate-700'>
                    <input type='checkbox' checked={contactForm.privacy_accepted} onChange={(event) => setContactForm((prev) => ({ ...prev, privacy_accepted: event.target.checked }))} className='mt-1 h-4 w-4 rounded border-slate-300' required />
                    <span>Accetto il trattamento dei dati per l invio della richiesta di contatto al club.</span>
                  </label>
                  <button className='btn-primary sm:col-span-2' type='submit' disabled={contactSubmitting}>
                    <Mail size={16} />
                    <span>{contactSubmitting ? 'Invio in corso…' : detail.club.is_community_open ? 'Invia richiesta contatto' : 'Invia richiesta accesso'}</span>
                  </button>
                </form>
              </SectionCard>

              <SectionCard title='Come muoversi da qui' description='La pagina pubblica resta read-only: osservi segnali utili, poi scegli il passo successivo.'>
                <div className='space-y-4 text-sm text-slate-600'>
                  <div className='surface-muted'>
                    <p className='font-semibold text-slate-900'>1. Segui il club</p>
                    <p className='mt-2'>Usa la watchlist pubblica per far comparire alert persistenti quando un match arriva a 2/4 o 3/4.</p>
                  </div>
                  <div className='surface-muted'>
                    <p className='font-semibold text-slate-900'>2. Valuta le partite open</p>
                    <p className='mt-2'>Qui vedi solo livello, campo, orario e riempimento. I nomi player restano privati fino all ingresso community.</p>
                  </div>
                  <div className='surface-muted'>
                    <p className='font-semibold text-slate-900'>3. Entra o fatti contattare</p>
                    <p className='mt-2'>{detail.club.is_community_open ? 'Se vuoi agire subito passa alla community del club; se preferisci un passaggio umano usa il form contatto qui sopra.' : 'La community del club e su richiesta: usa il form qui sopra per chiedere accesso senza uscire dal perimetro pubblico.'}</p>
                  </div>
                </div>
              </SectionCard>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}