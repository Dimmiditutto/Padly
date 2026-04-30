import { ArrowLeft, ArrowRight, Building2, Calendar, CheckCircle2, ChevronDown, ChevronUp, Clock3, CreditCard, LocateFixed, LogIn, Mail, MapPin, Phone, ShieldCheck } from 'lucide-react';
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { LoadingBlock } from '../components/LoadingBlock';
import { PageBrandBar } from '../components/PageBrandBar';
import { SectionCard } from '../components/SectionCard';
import { SlotGrid } from '../components/SlotGrid';
import { createPublicBooking, createPublicCheckout, getAvailability, getPublicConfig, listPublicClubsNearby } from '../services/publicApi';
import type { AvailabilityResponse, CourtAvailability, PaymentProvider, PublicBookingSummary, PublicClubSummary, PublicConfig, TimeSlot } from '../types';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';
import { formatCurrency, formatDate, toDateInputValue } from '../utils/format';
import { buildPlayAccessPath } from '../utils/play';

const DURATIONS = [60, 90, 120, 150, 180, 210, 240, 270, 300];
const COLLAPSED_COURT_SLOT_COUNT = 8;
const NEARBY_CLUBS_LIMIT = 10;
const today = toDateInputValue(new Date());
const openingHoursText = 'Campo aperto da Lunedì a Domenica dalle 7 alle 24';
const secondarySectionTitleClassName = 'text-base font-semibold text-slate-800';
const eyebrowTextClassName = 'text-sm font-semibold uppercase tracking-[0.16em] text-slate-500';
type FeedbackState = { tone: 'error' | 'success' | 'info' | 'warning'; message: string } | null;
type PublicContextState = 'loading' | 'ready' | 'required' | 'error';
const CLUB_SELECTION_REQUIRED_MESSAGE = 'Seleziona prima il club in cui vuoi giocare.';

export function PublicBookingPage() {
  const [searchParams] = useSearchParams();
  const tenantSlug = getTenantSlugFromSearchParams(searchParams);
  const [bookingDate, setBookingDate] = useState(today);
  const [duration, setDuration] = useState(90);
  const [courtGroups, setCourtGroups] = useState<CourtAvailability[]>([]);
  const [depositAmount, setDepositAmount] = useState<number>(20);
  const [depositRequired, setDepositRequired] = useState(true);
  const [publicConfig, setPublicConfig] = useState<PublicConfig | null>(null);
  const [publicContextState, setPublicContextState] = useState<PublicContextState>('loading');
  const [selectedCourtId, setSelectedCourtId] = useState('');
  const [selectedSlotId, setSelectedSlotId] = useState('');
  const [expandedCourtIds, setExpandedCourtIds] = useState<Record<string, boolean>>({});
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState>(null);
  const [nearbyClubs, setNearbyClubs] = useState<PublicClubSummary[]>([]);
  const [loadingNearbyClubs, setLoadingNearbyClubs] = useState(false);
  const [nearbyFeedback, setNearbyFeedback] = useState<FeedbackState>(null);
  const [hasRequestedNearbyClubs, setHasRequestedNearbyClubs] = useState(false);
  const [paymentProvider, setPaymentProvider] = useState<PaymentProvider>('STRIPE');
  const [lastBooking, setLastBooking] = useState<PublicBookingSummary | null>(null);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    note: '',
    privacy_accepted: false,
  });
  const bookingDayLabel = useMemo(() => formatBookingDayLabel(bookingDate, publicConfig?.timezone), [bookingDate, publicConfig?.timezone]);
  const visibleCourtGroups = useMemo(
    () => courtGroups.map((group) => ({ ...group, slots: group.slots.filter(isSlotWithinOpeningHours) })),
    [courtGroups]
  );
  const tenantDisplayName = publicConfig?.public_name || publicConfig?.app_name || 'Booking pubblico';
  const communityAccessPath = publicConfig ? buildPlayAccessPath(publicConfig.tenant_slug) : null;
  const playerRates = useMemo(() => buildPublicRateLines(publicConfig), [publicConfig]);
  const publicBookingDepositEnabled = useMemo(() => hasEnabledPublicBookingDeposit(publicConfig), [publicConfig]);
  const publicBookingExtras = publicConfig?.public_booking_extras || [];

  useEffect(() => {
    void loadConfig();
  }, [tenantSlug]);

  useEffect(() => {
    if (publicContextState !== 'ready' || !publicConfig) {
      return;
    }
    void loadAvailability();
  }, [bookingDate, duration, publicConfig, publicContextState, tenantSlug]);

  const availableProviders = useMemo<PaymentProvider[]>(() => {
    if (!publicConfig || !publicBookingDepositEnabled) return [];

    const providers: PaymentProvider[] = [];
    if (publicConfig.stripe_enabled) providers.push('STRIPE');
    if (publicConfig.paypal_enabled) providers.push('PAYPAL');
    return providers;
  }, [publicBookingDepositEnabled, publicConfig]);

  useEffect(() => {
    if (availableProviders.length === 0) {
      if (paymentProvider !== 'NONE') {
        setPaymentProvider('NONE');
      }
      return;
    }

    if (!availableProviders.includes(paymentProvider)) {
      setPaymentProvider(availableProviders[0]);
    }
  }, [availableProviders, paymentProvider]);

  async function loadConfig() {
    setLoadingConfig(true);
    setPublicContextState('loading');
    setPublicConfig(null);
    try {
      const config = await getPublicConfig(tenantSlug);
      setPublicConfig(config);
      setPublicContextState('ready');
      setFeedback(null);
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      if (detail === CLUB_SELECTION_REQUIRED_MESSAGE) {
        setPublicContextState('required');
        setFeedback({ tone: 'info', message: CLUB_SELECTION_REQUIRED_MESSAGE });
      } else {
        setPublicContextState('error');
        setFeedback({ tone: 'error', message: detail || 'Non riesco a caricare la configurazione pubblica del booking.' });
      }
    } finally {
      setLoadingConfig(false);
    }
  }

  async function loadAvailability() {
    if (!publicConfig) {
      return;
    }
    setLoadingSlots(true);
    setFeedback(null);
    setSelectedSlotId('');
    setSelectedCourtId('');
    setExpandedCourtIds({});
    try {
      const response = await getAvailability(bookingDate, duration, tenantSlug);
      setCourtGroups(normalizeCourtGroups(response));
      setDepositAmount(Number(response.deposit_amount));
      setDepositRequired(Boolean(response.deposit_required ?? publicBookingDepositEnabled));
    } catch (error) {
      setFeedback({ tone: 'error', message: 'Non riesco a caricare gli slot disponibili in questo momento.' });
      setCourtGroups([]);
    } finally {
      setLoadingSlots(false);
    }
  }

  async function loadNearbyClubs(latitude: number, longitude: number) {
    setLoadingNearbyClubs(true);
    try {
      const response = await listPublicClubsNearby(latitude, longitude);
      const items = response.items.slice(0, NEARBY_CLUBS_LIMIT);
      setNearbyClubs(items);
      setNearbyFeedback(items.length > 0 ? null : { tone: 'info', message: 'Nessun club vicino trovato con i dati disponibili. Apri la directory completa per cercare manualmente.' });
    } catch {
      setNearbyClubs([]);
      setNearbyFeedback({ tone: 'error', message: 'Non riesco a caricare i club vicini in questo momento.' });
    } finally {
      setLoadingNearbyClubs(false);
    }
  }

  function requestNearbyClubs() {
    setHasRequestedNearbyClubs(true);
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setNearbyClubs([]);
      setNearbyFeedback({ tone: 'warning', message: 'Questo browser non supporta la geolocalizzazione. Usa la directory pubblica per cercare per citta, CAP o provincia.' });
      return;
    }

    setLoadingNearbyClubs(true);
    setNearbyFeedback(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        void loadNearbyClubs(position.coords.latitude, position.coords.longitude);
      },
      (error) => {
        setLoadingNearbyClubs(false);
        setNearbyClubs([]);
        setNearbyFeedback({ tone: 'warning', message: geolocationDeniedMessage(error) });
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
    );
  }

  const selectedSlot = useMemo(
    () => flattenCourtSlots(visibleCourtGroups).find((slot) => slot.slot_id === selectedSlotId && (!selectedCourtId || slot.court_id === selectedCourtId)),
    [selectedCourtId, selectedSlotId, visibleCourtGroups]
  );
  const selectedCourt = useMemo(
    () => visibleCourtGroups.find((group) => group.court_id === selectedCourtId) || courtGroups.find((group) => group.court_id === selectedCourtId) || null,
    [courtGroups, selectedCourtId, visibleCourtGroups]
  );
  const selectedCourtSlots = useMemo(
    () => visibleCourtGroups.find((group) => group.court_id === selectedCourtId)?.slots || [],
    [selectedCourtId, visibleCourtGroups]
  );
  const highlightedSlotIds = useMemo(
    () => buildHighlightedSlotIds(selectedCourtSlots, selectedSlotId, duration),
    [duration, selectedCourtSlots, selectedSlotId]
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedSlot) {
      setFeedback({ tone: 'error', message: 'Seleziona prima un orario disponibile.' });
      return;
    }

    if (depositRequired && (availableProviders.length === 0 || paymentProvider === 'NONE')) {
      setFeedback({ tone: 'error', message: 'Il pagamento online non è disponibile in questo momento. Contatta il campo prima di completare la prenotazione.' });
      return;
    }

    setSubmitting(true);
    setFeedback(null);

    try {
      const bookingResponse = await createPublicBooking(
        {
          ...formData,
          booking_date: bookingDate,
          court_id: selectedCourtId || selectedSlot.court_id || null,
          start_time: selectedSlot.start_time,
          slot_id: selectedSlot.slot_id,
          duration_minutes: duration,
          payment_provider: depositRequired ? paymentProvider : 'NONE',
        },
        tenantSlug,
      );

      const booking = bookingResponse.booking;
      setLastBooking(booking);
      if (booking.status === 'PENDING_PAYMENT') {
        const checkoutResponse = await createPublicCheckout(booking.id, tenantSlug);
        window.location.assign(checkoutResponse.checkout_url);
        return;
      }
      setFeedback({ tone: 'success', message: `Prenotazione ${booking.public_reference} confermata. Nessuna caparra online richiesta per questo club.` });
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Non è stato possibile avviare la prenotazione.' });
    } finally {
      setSubmitting(false);
    }
  }

  if (publicContextState === 'required') {
    return (
      <div className='min-h-screen text-slate-900'>
        <div className='page-shell max-w-4xl space-y-6'>
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
            <div className='product-hero-copy'>
              <p className='text-sm font-semibold uppercase tracking-[0.18em] text-cyan-100/80'>Booking pubblico</p>
              <h1 className='text-3xl font-bold tracking-tight text-white sm:text-4xl sm:leading-tight'>Seleziona prima il club in cui vuoi giocare</h1>
              <p className='product-hero-description max-w-2xl'>Il booking non parte piu senza contesto club. Prima scegli il circolo giusto, poi apri il booking con listini e caparra corretti per quel club.</p>
            </div>
          </header>

          {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

          <SectionCard title='Scegli il club' description='Apri la directory pubblica o la scheda del club per entrare nel booking tenant-aware.' elevated>
            <div className='action-cluster'>
              <Link className='btn-primary' to='/clubs'>Apri directory club</Link>
            </div>
          </SectionCard>
        </div>
      </div>
    );
  }

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='page-shell max-w-6xl'>
        <header className='mb-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]'>
          <div className='product-hero-panel'>
            <PageBrandBar
              className='mb-6'
              actions={(
                <>
                  <Link className='hero-action-secondary' to='/clubs'>
                    <ArrowLeft size={16} />
                    <span>Torna ai club</span>
                  </Link>
                  <Link className='hero-action-secondary' to='/'>
                    <span>Torna alla home</span>
                  </Link>
                </>
              )}
            />
            <div className='mt-6 product-hero-copy'>
              <p className='text-sm font-semibold uppercase tracking-[0.18em] text-cyan-100/80'>Booking pubblico tenant-aware</p>
              <h1 className='text-3xl font-bold tracking-tight text-white sm:text-4xl sm:leading-tight'>{tenantDisplayName}: prenota il tuo match in pochi minuti</h1>
              <p className='product-hero-description max-w-xl'>
                {depositRequired
                  ? 'Scegli data, orario e durata. Paghi online solo la caparra del club, il saldo lo versi comodamente al campo.'
                  : 'Scegli data, orario e durata. Per questo club non e prevista una caparra online: la prenotazione viene confermata direttamente con le regole del circolo.'}
              </p>
            </div>
            <div className='mt-6 border-t border-white/10 pt-5'>
              <div className='grid gap-3 sm:grid-cols-3'>
                <InfoPill icon={<Clock3 size={16} />} title='Campo aperto' text='Da Lunedì a Domenica dalle 7 alle 24' />
                <InfoPill icon={<CreditCard size={16} />} title={depositRequired ? 'Caparra online' : 'Prenotazione'} text={depositRequired ? 'Stripe o PayPal' : 'Conferma diretta'} />
                <InfoPill icon={<ShieldCheck size={16} />} title='Conferma rapida' text='Slot protetto server-side' />
              </div>
            </div>
            {publicConfig ? (
              <div className='product-context-panel'>
                <div className='product-context-layout'>
                  <div>
                    <p className='text-xs font-semibold uppercase tracking-[0.18em] text-cyan-100/80'>Tenant attivo</p>
                    <div className='mt-2 flex items-center gap-2 text-lg font-semibold text-white'>
                      <Building2 size={18} className='text-cyan-200' />
                      <span>{tenantDisplayName}</span>
                    </div>
                    <p className='mt-1 text-sm text-slate-300'>Slug: {publicConfig.tenant_slug} • Fuso: {publicConfig.timezone}</p>
                  </div>
                  <div className='flex flex-col gap-2 text-sm text-slate-200'>
                    {publicConfig.contact_email ? (
                      <a href={`mailto:${publicConfig.contact_email}`} className='inline-flex items-center gap-2 hover:text-white'>
                        <Mail size={16} className='text-cyan-200' />
                        <span>{publicConfig.contact_email}</span>
                      </a>
                    ) : null}
                    {publicConfig.support_phone ? (
                      <a href={`tel:${publicConfig.support_phone}`} className='inline-flex items-center gap-2 hover:text-white'>
                        <Phone size={16} className='text-cyan-200' />
                        <span>{publicConfig.support_phone}</span>
                      </a>
                    ) : null}
                    {communityAccessPath ? (
                      <Link to={communityAccessPath} className='hero-action-secondary'>
                        <LogIn size={16} className='text-cyan-200' />
                        <span>Entra o rientra nella community</span>
                      </Link>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          <div className='surface-card bg-gradient-to-br from-white to-cyan-50'>
            <p className='text-base font-semibold text-cyan-700'>{depositRequired ? 'Caparra online' : 'Tariffe e regole del club'}</p>
            {depositRequired ? <div className='mt-2 text-4xl font-bold text-slate-950'>{formatCurrency(depositAmount)}</div> : null}
            <p className='mt-2 text-base leading-6 text-slate-600'>
              {depositRequired
                ? buildPublicDepositRuleText(publicConfig, depositAmount)
                : 'Per questo club la caparra online non e attiva. Vedi listino ed eventuali extra direttamente sotto.'}
            </p>
            {loadingConfig ? <div className='mt-4'><LoadingBlock label='Sto leggendo le regole operative…' labelClassName='text-base' /></div> : null}
            {publicConfig ? (
              <div className='mt-4 grid gap-3 sm:grid-cols-2'>
                <div className='surface-muted'>
                  <p className={eyebrowTextClassName}>Hold pagamento</p>
                  <p className='mt-2 text-base font-medium text-slate-900'>{publicConfig.booking_hold_minutes} minuti</p>
                  <p className='mt-1 text-sm leading-6 text-slate-600'>Tempo massimo per completare il checkout.</p>
                </div>
                <div className='surface-muted'>
                  <p className={eyebrowTextClassName}>Cancellazione</p>
                  <p className='mt-2 text-base font-medium text-slate-900'>Self-service fino all'inizio della prenotazione</p>
                  <p className='mt-1 text-sm leading-6 text-slate-600'>Rimborso automatico solo se annulli prima di {publicConfig.cancellation_window_hours} ore. Nelle ultime {publicConfig.cancellation_window_hours} ore la caparra non e rimborsabile.</p>
                </div>
              </div>
            ) : null}
            <div className='mt-4 rounded-2xl bg-slate-950 p-4 text-base text-slate-100'>
              <p className='font-semibold'>Tariffe del club per giocatore</p>
              <ul className='mt-2 space-y-1 text-slate-300'>
                {playerRates.map((rate) => (
                  <li key={rate}>• {rate}</li>
                ))}
              </ul>
              {publicBookingExtras.length > 0 ? (
                <div className='mt-4'>
                  <p className='text-sm font-semibold text-slate-100'>Extra del club</p>
                  <ul className='mt-2 space-y-1 text-slate-300'>
                    {publicBookingExtras.map((extra) => (
                      <li key={extra}>• {extra}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              <p className='mt-3 text-sm leading-5 text-slate-400'>Listini e extra sono mostrati solo nel contesto del club selezionato.</p>
            </div>
          </div>
        </header>

        <main className='space-y-6'>
          <div className='grid gap-6 lg:grid-cols-[1.05fr_0.95fr]'>
            <section>
              <SectionCard title='Scegli data e durata' description={`${openingHoursText}. La disponibilità cambia in tempo reale.`} elevated>
              <div className='mb-4 flex items-center gap-2'>
                <Calendar size={18} className='text-cyan-600' />
                <p className={secondarySectionTitleClassName}>Selezione slot</p>
              </div>
              <div className='grid gap-4 sm:grid-cols-2'>
                <div>
                  <label className='field-label' htmlFor='booking-date'>Data</label>
                  <input id='booking-date' className='text-input' type='date' value={bookingDate} min={today} onChange={(e) => setBookingDate(e.target.value)} />
                  <div className='mt-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3'>
                    <p className={eyebrowTextClassName}>Giorno</p>
                    <p className='mt-2 text-base font-medium text-slate-900'>{bookingDayLabel}</p>
                  </div>
                </div>
                <div>
                  <label className='field-label' htmlFor='booking-duration'>Durata</label>
                  <select id='booking-duration' className='text-input' value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
                    {DURATIONS.map((minutes) => (
                      <option key={minutes} value={minutes}>{minutes} minuti</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className='mt-5'>
                <div className='mb-3 flex items-center justify-between'>
                  <p className={secondarySectionTitleClassName}>Orari disponibili per campo</p>
                  {loadingSlots && <p className='text-sm text-slate-500'>Aggiornamento in corso…</p>}
                </div>
                {loadingSlots ? <LoadingBlock label='Sto caricando gli slot disponibili…' /> : visibleCourtGroups.length === 0 ? <SlotGrid slots={[]} selectedSlotId={selectedSlotId} highlightedSlotIds={[]} onSelect={setSelectedSlotId} /> : (
                  <div className='space-y-4'>
                    {visibleCourtGroups.map((group) => (
                      <div key={group.court_id} className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
                        <div className='mb-3 flex items-center justify-between gap-3'>
                          <div>
                            <p className='text-sm font-semibold text-slate-900'>{group.court_name}</p>
                            <p className='text-xs text-slate-500'>Slot disponibili aggiornati in tempo reale per questo campo.</p>
                          </div>
                          <div className='flex items-center gap-2'>
                            {group.badge_label ? <span className='rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-600'>{group.badge_label}</span> : null}
                            {group.slots.length > COLLAPSED_COURT_SLOT_COUNT ? (
                              <button
                                type='button'
                                aria-expanded={expandedCourtIds[group.court_id] ? 'true' : 'false'}
                                aria-label={`${expandedCourtIds[group.court_id] ? 'Comprimi' : 'Espandi'} orari di ${group.court_name}`}
                                className='inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:text-slate-900'
                                onClick={() => setExpandedCourtIds((prev) => ({ ...prev, [group.court_id]: !prev[group.court_id] }))}
                              >
                                {expandedCourtIds[group.court_id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                              </button>
                            ) : null}
                          </div>
                        </div>
                        <SlotGrid
                          slots={getDisplayedCourtSlots({
                            slots: group.slots,
                            expanded: Boolean(expandedCourtIds[group.court_id]),
                            selectedSlotId: selectedCourtId === group.court_id ? selectedSlotId : '',
                            highlightedSlotIds: selectedCourtId === group.court_id ? highlightedSlotIds : [],
                          })}
                          selectedSlotId={selectedCourtId === group.court_id ? selectedSlotId : ''}
                          highlightedSlotIds={selectedCourtId === group.court_id ? highlightedSlotIds : []}
                          unavailableStateContent={buildCollapsedCourtCta({
                            courtId: group.court_id,
                            slots: group.slots,
                            expanded: Boolean(expandedCourtIds[group.court_id]),
                            onExpand: () => setExpandedCourtIds((prev) => ({ ...prev, [group.court_id]: true })),
                          })}
                          onSelect={(slotId) => {
                            setSelectedCourtId(group.court_id);
                            setSelectedSlotId(slotId);
                          }}
                        />
                      </div>
                    ))}
                  </div>
                )}
                {selectedSlot && (
                  <p className='mt-3 text-sm font-medium text-emerald-700'>Hai selezionato {selectedCourt?.court_name || 'il campo'} • {selectedSlot.display_start_time} → {selectedSlot.display_end_time}</p>
                )}
              </div>
            </SectionCard>
            </section>

            <section>
              <SectionCard title='Completa la prenotazione' description={depositRequired ? 'Inserisci i tuoi dati e scegli come versare la caparra.' : 'Inserisci i tuoi dati e conferma la prenotazione del club selezionato.'} elevated>
              {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}
              {lastBooking && !feedback ? (
                <AlertBanner tone='success' title={lastBooking.status === 'PENDING_PAYMENT' ? 'Richiesta creata' : 'Prenotazione confermata'}>
                  {lastBooking.status === 'PENDING_PAYMENT'
                    ? `Codice ${lastBooking.public_reference}. Ti sto reindirizzando al checkout della caparra.`
                    : `Codice ${lastBooking.public_reference}. Il club non richiede caparra online per questo booking.`}
                </AlertBanner>
              ) : null}

              <form className='mt-5 space-y-4' onSubmit={handleSubmit}>
                <div className='grid gap-4 sm:grid-cols-2'>
                  <div>
                    <label className='field-label' htmlFor='public-first-name'>Nome</label>
                    <input id='public-first-name' className='text-input' value={formData.first_name} onChange={(e) => setFormData((prev) => ({ ...prev, first_name: e.target.value }))} required />
                  </div>
                  <div>
                    <label className='field-label' htmlFor='public-last-name'>Cognome</label>
                    <input id='public-last-name' className='text-input' value={formData.last_name} onChange={(e) => setFormData((prev) => ({ ...prev, last_name: e.target.value }))} required />
                  </div>
                  <div>
                    <label className='field-label' htmlFor='public-phone'>Telefono</label>
                    <input id='public-phone' className='text-input' value={formData.phone} onChange={(e) => setFormData((prev) => ({ ...prev, phone: e.target.value }))} required />
                  </div>
                  <div>
                    <label className='field-label' htmlFor='public-email'>Email</label>
                    <input id='public-email' className='text-input' type='email' value={formData.email} onChange={(e) => setFormData((prev) => ({ ...prev, email: e.target.value }))} required />
                  </div>
                </div>

                <div>
                  <label className='field-label' htmlFor='public-note'>Nota facoltativa</label>
                  <textarea id='public-note' className='text-input min-h-24' value={formData.note} onChange={(e) => setFormData((prev) => ({ ...prev, note: e.target.value }))} />
                </div>

                {depositRequired ? (
                  <div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
                    <p className={secondarySectionTitleClassName}>Metodo pagamento caparra</p>
                    {availableProviders.length === 0 ? (
                      <div className='mt-3'>
                        <AlertBanner tone='error'>Il pagamento online non è disponibile in questo momento. Contatta il campo prima di completare la prenotazione.</AlertBanner>
                      </div>
                    ) : null}
                    <div className='mt-3 grid gap-2 sm:grid-cols-2'>
                      {availableProviders.map((provider) => (
                        <button
                          type='button'
                          key={provider}
                          onClick={() => setPaymentProvider(provider)}
                          className={`rounded-2xl border px-4 py-3 text-sm font-semibold ${paymentProvider === provider ? 'border-slate-950 bg-slate-950 text-white' : 'border-slate-200 bg-white text-slate-700'}`}
                        >
                          {provider === 'STRIPE' ? 'Stripe' : 'PayPal'}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className='rounded-2xl bg-cyan-50 p-4 text-sm text-slate-700'>
                  <p className={secondarySectionTitleClassName}>Riepilogo</p>
                  <p className='mt-2'>Data: <strong>{formatDate(bookingDate)}</strong></p>
                  <p>Campo: <strong>{selectedCourt?.court_name || 'Seleziona uno slot'}</strong></p>
                  <p>Inizio: <strong>{selectedSlot?.display_start_time || 'Seleziona uno slot'}</strong></p>
                  <p>Durata: <strong>{duration} minuti</strong></p>
                  {depositRequired ? <p>Caparra online: <strong>{formatCurrency(depositAmount)}</strong></p> : null}
                  <p className='mt-2 text-sm leading-6 text-slate-600'>{depositRequired ? 'Il saldo residuo viene pagato direttamente al campo. Nessuna registrazione obbligatoria.' : 'Nessuna caparra online prevista: il club gestisce l intero incasso secondo le proprie regole operative.'}</p>
                </div>

                <label className='flex items-start gap-3 rounded-2xl border border-slate-200 p-4 text-sm text-slate-700'>
                  <input
                    type='checkbox'
                    checked={formData.privacy_accepted}
                    onChange={(e) => setFormData((prev) => ({ ...prev, privacy_accepted: e.target.checked }))}
                    className='mt-1 h-4 w-4 rounded border-slate-300'
                    required
                  />
                  <span>Accetto il trattamento dei dati per la gestione della prenotazione.</span>
                </label>

                <button className='btn-primary w-full' type='submit' disabled={submitting || loadingSlots || (depositRequired && availableProviders.length === 0)}>
                  {submitting ? (depositRequired ? 'Sto preparando il checkout…' : 'Sto confermando il booking…') : (depositRequired ? 'Continua al pagamento della caparra' : 'Conferma prenotazione')}
                </button>
              </form>
            </SectionCard>
              <div className='mt-4 flex justify-end'>
                <Link
                  to={withTenantPath('/admin/login', tenantSlug)}
                  className='inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-cyan-200'
                >
                  <LogIn size={16} />
                  Accesso admin
                </Link>
              </div>
            </section>
          </div>

          <SectionCard title='Come funziona' description='Un flusso lineare e leggibile, ottimizzato per smartphone.'>
            <div className='grid gap-3 sm:grid-cols-3'>
              <StepCard index='1' title='Seleziona slot' description='Scegli data, orario e durata tra le fasce realmente libere.' />
              <StepCard index='2' title='Compila i dati' description='Inserisci contatti e una nota facoltativa per il campo.' />
              <StepCard index='3' title={depositRequired ? 'Versa la caparra' : 'Conferma la prenotazione'} description={depositRequired ? 'Completa il checkout e ricevi subito la conferma.' : 'Invia la richiesta e ricevi subito la conferma del booking.'} />
            </div>
          </SectionCard>

          <SectionCard
            title='Club vicini a te'
            description='Se stai giocando fuori zona, usa la geolocalizzazione per trovare i club del network che vale la pena aprire subito.'
            actions={(
              <div className='flex flex-col gap-2 sm:flex-row'>
                <button type='button' className='btn-secondary' onClick={requestNearbyClubs} disabled={loadingNearbyClubs}>
                  <LocateFixed size={16} />
                  <span>{loadingNearbyClubs ? 'Ricerca in corso…' : 'Usa la mia posizione'}</span>
                </button>
                <Link className='btn-secondary' to='/clubs'>
                  <span>Apri directory club</span>
                </Link>
              </div>
            )}
          >
            <div className='space-y-4'>
              {nearbyFeedback ? <AlertBanner tone={nearbyFeedback.tone}>{nearbyFeedback.message}</AlertBanner> : null}
              {loadingNearbyClubs ? <LoadingBlock label='Sto cercando i club piu vicini…' /> : null}
              {!loadingNearbyClubs && nearbyClubs.length > 0 ? (
                <div className='grid gap-4 lg:grid-cols-2'>
                  {nearbyClubs.map((club) => (
                    <article key={club.club_id} data-testid='nearby-club-card' className='rounded-2xl border border-slate-200 bg-white p-4'>
                      <div className='flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between'>
                        <div className='min-w-0'>
                          <p className='text-base font-semibold text-slate-950'>{club.public_name}</p>
                          <p className='mt-2 flex items-start gap-2 text-sm text-slate-600'>
                            <MapPin size={16} className='mt-0.5 shrink-0 text-cyan-700' />
                            <span>{buildNearbyClubLocationLine(club)}</span>
                          </p>
                          <p className='mt-2 text-sm text-slate-600'>
                            {formatDistance(club.distance_km)} • {club.courts_count} {club.courts_count === 1 ? 'campo' : 'campi'}
                          </p>
                        </div>
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${club.is_community_open ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
                          {club.is_community_open ? 'Community aperta' : 'Community su richiesta'}
                        </span>
                      </div>

                      <div className='mt-4 grid gap-2 sm:grid-cols-3'>
                        <NearbyClubCountCard label='3/4' value={club.open_matches_three_of_four_count} helper='Da chiudere subito' />
                        <NearbyClubCountCard label='2/4' value={club.open_matches_two_of_four_count} helper='Buone occasioni' />
                        <NearbyClubCountCard label='1/4' value={club.open_matches_one_of_four_count} helper='Da monitorare' />
                      </div>

                      <div className='mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between'>
                        <p className='text-sm text-slate-600'>{club.public_activity_label}</p>
                        <Link aria-label={`Apri scheda club ${club.public_name}`} className='btn-secondary sm:w-auto' to={`/c/${club.club_slug}`}>
                          <span>Apri scheda club</span>
                          <ArrowRight size={16} />
                        </Link>
                      </div>
                    </article>
                  ))}
                </div>
              ) : null}
              {!loadingNearbyClubs && nearbyClubs.length === 0 && !nearbyFeedback ? (
                <div className='surface-muted text-sm text-slate-600'>
                  {hasRequestedNearbyClubs
                    ? 'Nessun club vicino disponibile in questo momento. Apri la directory completa per cercare manualmente.'
                    : 'Attiva la geolocalizzazione solo quando ti serve: vedrai i 10 club piu vicini e potrai aprire la scheda pubblica di ciascun club.'}
                </div>
              ) : null}
            </div>
          </SectionCard>
        </main>
      </div>
    </div>
  );
}

function formatBookingDayLabel(value: string, timezone = 'Europe/Rome') {
  const [year, month, day] = value.split('-').map(Number);
  if (!year || !month || !day) {
    return '';
  }

  const normalizedDate = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
  const label = new Intl.DateTimeFormat('it-IT', {
    weekday: 'long',
    timeZone: timezone,
  }).format(normalizedDate);
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function geolocationDeniedMessage(error: GeolocationPositionError | { code?: number } | null | undefined) {
  if (error?.code === 1) {
    return 'Permesso geolocalizzazione negato. Usa la directory pubblica per cercare per citta, CAP o provincia.';
  }
  return 'Geolocalizzazione non disponibile in questo momento. Usa la directory pubblica per trovare il club giusto.';
}

function buildNearbyClubLocationLine(club: PublicClubSummary) {
  return [club.public_city, club.public_province, club.public_postal_code].filter(Boolean).join(' • ') || 'Zona non disponibile';
}

function formatDistance(distanceKm: number | null | undefined) {
  if (distanceKm == null) {
    return 'Distanza non disponibile';
  }
  return `${distanceKm.toFixed(1).replace('.', ',')} km`;
}

function buildPublicRateLines(config: PublicConfig | null) {
  if (!config) {
    return [];
  }

  const memberHourlyRate = config.member_hourly_rate;
  const nonMemberHourlyRate = config.non_member_hourly_rate;
  const memberNinetyMinuteRate = config.member_ninety_minute_rate;
  const nonMemberNinetyMinuteRate = config.non_member_ninety_minute_rate;

  return [
    `Tesserati: ${formatCurrency(memberHourlyRate)}/ora per giocatore`,
    `Non tesserati: ${formatCurrency(nonMemberHourlyRate)}/ora per giocatore`,
    `90 minuti: ${formatCurrency(memberNinetyMinuteRate)} per giocatore tesserato`,
    `90 minuti: ${formatCurrency(nonMemberNinetyMinuteRate)} per giocatore non tesserato`,
  ];
}

function hasEnabledPublicBookingDeposit(config: PublicConfig | null) {
  if (!config) {
    return false;
  }

  const enabled = config.public_booking_deposit_enabled ?? true;
  const baseAmount = config.public_booking_base_amount ?? 20;
  const includedMinutes = config.public_booking_included_minutes ?? 90;

  return Boolean(enabled)
    && Number(baseAmount) > 0
    && Number(includedMinutes) > 0;
}

function buildPublicDepositRuleText(config: PublicConfig | null, currentDepositAmount: number) {
  if (!config || !hasEnabledPublicBookingDeposit(config)) {
    return 'Nessuna caparra online prevista per questo club.';
  }

  const baseAmount = Number(config.public_booking_base_amount ?? 20);
  const includedMinutes = Number(config.public_booking_included_minutes ?? 90);
  const extraAmount = Number(config.public_booking_extra_amount ?? 10);
  const extraStepMinutes = Number(config.public_booking_extra_step_minutes ?? 30);

  if (extraAmount > 0 && extraStepMinutes > 0) {
    return `${formatCurrency(baseAmount)} fino a ${includedMinutes} minuti. Poi si aggiungono ${formatCurrency(extraAmount)} ogni ${extraStepMinutes} minuti successivi. Importo attuale: ${formatCurrency(currentDepositAmount)}.`;
  }

  return `${formatCurrency(baseAmount)} fino a ${includedMinutes} minuti. Nessun extra oltre la soglia configurata dal club.`;
}

function normalizeCourtGroups(response: AvailabilityResponse): CourtAvailability[] {
  if (response.courts && response.courts.length > 0) {
    return response.courts;
  }

  if (response.slots.length === 0) {
    return [];
  }

  const fallbackCourtId = response.slots[0].court_id || 'default-court';
  const fallbackCourtName = response.slots[0].court_name || 'Campo 1';
  const fallbackBadgeLabel = response.slots[0].court_badge_label || null;

  return [{
    court_id: fallbackCourtId,
    court_name: fallbackCourtName,
    badge_label: fallbackBadgeLabel,
    slots: response.slots.map((slot) => ({
      ...slot,
      court_id: slot.court_id || fallbackCourtId,
      court_name: slot.court_name || fallbackCourtName,
      court_badge_label: slot.court_badge_label || fallbackBadgeLabel,
    })),
  }];
}

function flattenCourtSlots(groups: CourtAvailability[]) {
  return groups.flatMap((group) => group.slots);
}

function getDisplayedCourtSlots({
  slots,
  expanded,
  selectedSlotId,
  highlightedSlotIds,
}: {
  slots: TimeSlot[];
  expanded: boolean;
  selectedSlotId: string;
  highlightedSlotIds: string[];
}) {
  if (expanded || slots.length <= COLLAPSED_COURT_SLOT_COUNT) {
    return slots;
  }

  const initialSlots = slots.slice(0, COLLAPSED_COURT_SLOT_COUNT);
  const initialSlotIds = new Set(initialSlots.map((slot) => slot.slot_id));
  const pinnedSlotIds = new Set<string>();

  if (selectedSlotId) {
    pinnedSlotIds.add(selectedSlotId);
  }
  for (const slotId of highlightedSlotIds) {
    pinnedSlotIds.add(slotId);
  }

  const pinnedSlots = slots.filter((slot) => pinnedSlotIds.has(slot.slot_id) && !initialSlotIds.has(slot.slot_id));
  return [...initialSlots, ...pinnedSlots];
}

function buildCollapsedCourtCta({
  courtId,
  slots,
  expanded,
  onExpand,
}: {
  courtId: string;
  slots: TimeSlot[];
  expanded: boolean;
  onExpand: () => void;
}) {
  if (expanded || slots.length <= COLLAPSED_COURT_SLOT_COUNT) {
    return null;
  }

  const initialSlots = slots.slice(0, COLLAPSED_COURT_SLOT_COUNT);
  const hasVisibleAvailableSlots = initialSlots.some((slot) => slot.available);
  const hasHiddenSlots = slots.length > initialSlots.length;

  if (!hasHiddenSlots || hasVisibleAvailableSlots) {
    return null;
  }

  return (
    <button
      type='button'
      className='btn-secondary w-full'
      onClick={onExpand}
      aria-label='Vedi tutti gli orari'
    >
      Vedi tutti gli orari
    </button>
  );
}

function buildHighlightedSlotIds(slots: TimeSlot[], selectedSlotId: string, durationMinutes: number) {
  if (!selectedSlotId) {
    return [];
  }

  const selectedStart = new Date(selectedSlotId).getTime();
  if (Number.isNaN(selectedStart)) {
    return [];
  }

  const coveredStartTimes = new Set<number>();
  const slotCount = Math.max(1, durationMinutes / 30);
  for (let index = 0; index < slotCount; index += 1) {
    coveredStartTimes.add(selectedStart + (index * 30 * 60 * 1000));
  }

  return slots
    .filter((slot) => coveredStartTimes.has(new Date(slot.slot_id).getTime()))
    .map((slot) => slot.slot_id);
}

function isSlotWithinOpeningHours(slot: TimeSlot) {
  if (slot.start_time < '07:00') {
    return false;
  }

  return slot.end_time === '00:00' || slot.end_time > slot.start_time;
}

function StepCard({ index, title, description }: { index: string; title: string; description: string }) {
  return (
    <div className='surface-muted'>
      <div className='inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-white text-slate-950 shadow-sm'>
        <CheckCircle2 size={18} />
      </div>
      <p className='mt-4 text-sm font-semibold uppercase tracking-[0.16em] text-slate-500'>Step {index}</p>
      <h3 className='mt-2 text-base font-semibold text-slate-950'>{title}</h3>
      <p className='mt-2 text-sm leading-6 text-slate-600'>{description}</p>
    </div>
  );
}

function InfoPill({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className='rounded-2xl border border-slate-800 bg-slate-900/90 p-3'>
      <div className='mb-2 text-cyan-300'>{icon}</div>
      <p className='text-sm font-semibold'>{title}</p>
      <p className='mt-1 text-sm leading-5 text-slate-400'>{text}</p>
    </div>
  );
}

function NearbyClubCountCard({ label, value, helper }: { label: string; value: number; helper: string }) {
  return (
    <div className='rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3'>
      <p className='text-xs font-semibold uppercase tracking-[0.16em] text-slate-500'>{label}</p>
      <p className='mt-2 text-2xl font-semibold text-slate-950'>{value}</p>
      <p className='mt-1 text-xs text-slate-600'>{helper}</p>
    </div>
  );
}
