import { Calendar, CheckCircle2, Clock3, CreditCard, ShieldCheck } from 'lucide-react';
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from 'react';
import { AlertBanner } from '../components/AlertBanner';
import { AppBrand } from '../components/AppBrand';
import { LoadingBlock } from '../components/LoadingBlock';
import { SectionCard } from '../components/SectionCard';
import { SlotGrid } from '../components/SlotGrid';
import { createPublicBooking, createPublicCheckout, getAvailability, getPublicConfig } from '../services/publicApi';
import type { PaymentProvider, PublicBookingSummary, PublicConfig, TimeSlot } from '../types';
import { formatCurrency, toDateInputValue } from '../utils/format';

const DURATIONS = [60, 90, 120, 150, 180, 210, 240, 270, 300];
const today = toDateInputValue(new Date());

const playerRates = [
  'Tesserati: € 7/ora per giocatore',
  'Non tesserati: € 9/ora per giocatore',
  '90 minuti: € 10 per giocatore tesserato',
  '90 minuti: € 13 per giocatore non tesserato',
];

export function PublicBookingPage() {
  const [bookingDate, setBookingDate] = useState(today);
  const [duration, setDuration] = useState(90);
  const [slots, setSlots] = useState<TimeSlot[]>([]);
  const [depositAmount, setDepositAmount] = useState<number>(20);
  const [publicConfig, setPublicConfig] = useState<PublicConfig | null>(null);
  const [selectedSlotId, setSelectedSlotId] = useState('');
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: 'error' | 'success' | 'info'; message: string } | null>(null);
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

  useEffect(() => {
    void loadConfig();
  }, []);

  useEffect(() => {
    void loadAvailability();
  }, [bookingDate, duration]);

  const availableProviders = useMemo<PaymentProvider[]>(() => {
    if (!publicConfig) return [];

    const providers: PaymentProvider[] = [];
    if (publicConfig.stripe_enabled) providers.push('STRIPE');
    if (publicConfig.paypal_enabled) providers.push('PAYPAL');
    return providers;
  }, [publicConfig]);

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
    try {
      const config = await getPublicConfig();
      setPublicConfig(config);
    } catch {
      setFeedback({ tone: 'error', message: 'Non riesco a caricare la configurazione pubblica del booking.' });
    } finally {
      setLoadingConfig(false);
    }
  }

  async function loadAvailability() {
    setLoadingSlots(true);
    setFeedback(null);
    setSelectedSlotId('');
    try {
      const response = await getAvailability(bookingDate, duration);
      setSlots(response.slots);
      setDepositAmount(Number(response.deposit_amount));
    } catch (error) {
      setFeedback({ tone: 'error', message: 'Non riesco a caricare gli slot disponibili in questo momento.' });
    } finally {
      setLoadingSlots(false);
    }
  }

  const selectedSlot = useMemo(
    () => slots.find((slot) => slot.slot_id === selectedSlotId),
    [selectedSlotId, slots]
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedSlot) {
      setFeedback({ tone: 'error', message: 'Seleziona prima un orario disponibile.' });
      return;
    }

    if (availableProviders.length === 0 || paymentProvider === 'NONE') {
      setFeedback({ tone: 'error', message: 'Il pagamento online non è disponibile in questo momento. Contatta il campo prima di completare la prenotazione.' });
      return;
    }

    setSubmitting(true);
    setFeedback(null);

    try {
      const bookingResponse = await createPublicBooking({
        ...formData,
        booking_date: bookingDate,
        start_time: selectedSlot.start_time,
        slot_id: selectedSlot.slot_id,
        duration_minutes: duration,
        payment_provider: paymentProvider,
      });

      const booking = bookingResponse.booking;
      setLastBooking(booking);
      const checkoutResponse = await createPublicCheckout(booking.id);
      window.location.assign(checkoutResponse.checkout_url);
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Non è stato possibile avviare la prenotazione.' });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='page-shell max-w-6xl'>
        <header className='mb-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]'>
          <div className='rounded-[28px] border border-cyan-400/20 bg-slate-950/80 p-6 text-white shadow-soft'>
            <AppBrand light />
            <p className='mt-4 inline-flex rounded-full border border-cyan-400/30 px-3 py-1 text-xs font-semibold text-cyan-200'>Padel booking pubblico • mobile first</p>
            <h1 className='text-3xl font-bold tracking-tight sm:text-4xl'>Prenota il tuo match in pochi minuti</h1>
            <p className='mt-3 max-w-xl text-sm text-slate-300 sm:text-base'>Scegli data, orario e durata. Paghi online solo la caparra, il saldo lo versi comodamente al campo.</p>
            <div className='mt-5 grid gap-3 sm:grid-cols-3'>
              <InfoPill icon={<Clock3 size={16} />} title='Aperto 24/7' text='Disponibilità continua' />
              <InfoPill icon={<CreditCard size={16} />} title='Caparra online' text='Stripe o PayPal' />
              <InfoPill icon={<ShieldCheck size={16} />} title='Conferma rapida' text='Slot protetto server-side' />
            </div>
          </div>

          <div className='surface-card bg-gradient-to-br from-white to-cyan-50'>
            <p className='text-sm font-semibold text-cyan-700'>Caparra online</p>
            <div className='mt-2 text-4xl font-bold text-slate-950'>{formatCurrency(depositAmount)}</div>
            <p className='mt-2 text-sm text-slate-600'>Fino a 90 minuti paghi €20. Poi si aggiungono €10 per ogni ulteriore blocco da 30 minuti.</p>
            {loadingConfig ? <div className='mt-4'><LoadingBlock label='Sto leggendo le regole operative…' /></div> : null}
            {publicConfig ? (
              <div className='mt-4 grid gap-3 sm:grid-cols-2'>
                <div className='surface-muted'>
                  <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Hold pagamento</p>
                  <p className='mt-2 text-sm font-medium text-slate-900'>{publicConfig.booking_hold_minutes} minuti</p>
                </div>
                <div className='surface-muted'>
                  <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Cancellazione</p>
                  <p className='mt-2 text-sm font-medium text-slate-900'>Self-service fino all'inizio della prenotazione</p>
                  <p className='mt-1 text-xs text-slate-600'>Rimborso automatico solo se annulli prima di {publicConfig.cancellation_window_hours} ore. Nelle ultime {publicConfig.cancellation_window_hours} ore la caparra non e rimborsabile.</p>
                </div>
              </div>
            ) : null}
            <div className='mt-4 rounded-2xl bg-slate-950 p-4 text-sm text-slate-100'>
              <p className='font-semibold'>Tariffe informative per giocatore</p>
              <ul className='mt-2 space-y-1 text-slate-300'>
                {playerRates.map((rate) => (
                  <li key={rate}>• {rate}</li>
                ))}
              </ul>
              <p className='mt-3 text-xs text-slate-400'>Tariffe informative: non sostituiscono la caparra online.</p>
            </div>
          </div>
        </header>

        <main className='grid gap-6 lg:grid-cols-[1.05fr_0.95fr]'>
          <section className='space-y-6'>
            <SectionCard title='Scegli data e durata' description='Il campo è aperto 24/7. La disponibilità cambia in tempo reale.' elevated>
              <div className='mb-4 flex items-center gap-2'>
                <Calendar size={18} className='text-cyan-600' />
                <p className='text-sm font-semibold text-slate-700'>Selezione slot</p>
              </div>
              <div className='grid gap-4 sm:grid-cols-2'>
                <div>
                  <label className='field-label' htmlFor='booking-date'>Data</label>
                  <input id='booking-date' className='text-input' type='date' value={bookingDate} min={today} onChange={(e) => setBookingDate(e.target.value)} />
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
                  <p className='text-sm font-semibold text-slate-700'>Orari disponibili</p>
                  {loadingSlots && <p className='text-sm text-slate-500'>Aggiornamento in corso…</p>}
                </div>
                {loadingSlots ? <LoadingBlock label='Sto caricando gli slot disponibili…' /> : <SlotGrid slots={slots} selectedSlotId={selectedSlotId} onSelect={setSelectedSlotId} />}
                {selectedSlot && (
                  <p className='mt-3 text-sm text-emerald-700'>Hai selezionato {selectedSlot.display_start_time} → {selectedSlot.display_end_time}</p>
                )}
              </div>
            </SectionCard>

            <SectionCard title='Come funziona' description='Un flusso lineare e leggibile, ottimizzato per smartphone.'>
              <div className='grid gap-3 sm:grid-cols-3'>
                <StepCard index='1' title='Seleziona slot' description='Scegli data, orario e durata tra le fasce realmente libere.' />
                <StepCard index='2' title='Compila i dati' description='Inserisci contatti e una nota facoltativa per il campo.' />
                <StepCard index='3' title='Versa la caparra' description='Completa il checkout e ricevi subito la conferma.' />
              </div>
            </SectionCard>
          </section>

          <section className='space-y-6'>
            <SectionCard title='Completa la prenotazione' description='Inserisci i tuoi dati e scegli come versare la caparra.' elevated>
              {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}
              {lastBooking && !feedback ? (
                <AlertBanner tone='success' title='Richiesta creata'>
                  Codice {lastBooking.public_reference}. Ti sto reindirizzando al checkout della caparra.
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

                <div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
                  <p className='text-sm font-semibold text-slate-800'>Metodo pagamento caparra</p>
                  <p className='mt-1 text-xs text-slate-500'>Mostro solo i provider di pagamento attualmente disponibili in questo ambiente.</p>
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

                <div className='rounded-2xl bg-cyan-50 p-4 text-sm text-slate-700'>
                  <p className='font-semibold text-slate-900'>Riepilogo</p>
                  <p className='mt-2'>Data: <strong>{bookingDate}</strong></p>
                  <p>Inizio: <strong>{selectedSlot?.display_start_time || 'Seleziona uno slot'}</strong></p>
                  <p>Durata: <strong>{duration} minuti</strong></p>
                  <p>Caparra online: <strong>{formatCurrency(depositAmount)}</strong></p>
                  <p className='mt-2 text-xs text-slate-600'>Il saldo residuo viene pagato direttamente al campo. Nessuna registrazione obbligatoria.</p>
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

                <button className='btn-primary w-full' type='submit' disabled={submitting || loadingSlots || availableProviders.length === 0}>
                  {submitting ? 'Sto preparando il checkout…' : 'Continua al pagamento della caparra'}
                </button>
              </form>
            </SectionCard>
          </section>
        </main>
      </div>
    </div>
  );
}

function StepCard({ index, title, description }: { index: string; title: string; description: string }) {
  return (
    <div className='surface-muted'>
      <div className='inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-white text-slate-950 shadow-sm'>
        <CheckCircle2 size={18} />
      </div>
      <p className='mt-4 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Step {index}</p>
      <h3 className='mt-2 text-base font-semibold text-slate-950'>{title}</h3>
      <p className='mt-2 text-sm text-slate-600'>{description}</p>
    </div>
  );
}

function InfoPill({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className='rounded-2xl border border-slate-800 bg-slate-900/90 p-3'>
      <div className='mb-2 text-cyan-300'>{icon}</div>
      <p className='text-sm font-semibold'>{title}</p>
      <p className='text-xs text-slate-400'>{text}</p>
    </div>
  );
}
