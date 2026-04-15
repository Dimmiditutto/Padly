import { Calendar, Clock3, CreditCard, ShieldCheck } from 'lucide-react';
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import type { AvailabilityResponse, BookingSummary, PaymentProvider, TimeSlot } from '../types';

const DURATIONS = [60, 90, 120, 150, 180, 210, 240, 270, 300];
const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

const playerRates = [
  'Tesserati: €7/ora per giocatore',
  'Non tesserati: €9/ora per giocatore',
  '90 minuti: €10 tesserati per giocatore',
  '90 minuti: €13 non tesserati per giocatore',
];

export function PublicBookingPage() {
  const [bookingDate, setBookingDate] = useState(tomorrow);
  const [duration, setDuration] = useState(90);
  const [slots, setSlots] = useState<TimeSlot[]>([]);
  const [depositAmount, setDepositAmount] = useState<number>(20);
  const [selectedTime, setSelectedTime] = useState('');
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string>('');
  const [paymentProvider, setPaymentProvider] = useState<PaymentProvider>('STRIPE');
  const [lastBooking, setLastBooking] = useState<BookingSummary | null>(null);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    note: '',
    privacy_accepted: false,
  });

  useEffect(() => {
    void loadAvailability();
  }, [bookingDate, duration]);

  async function loadAvailability() {
    setLoadingSlots(true);
    setFeedback('');
    setSelectedTime('');
    try {
      const response = await api.get<AvailabilityResponse>('/public/availability', {
        params: { date: bookingDate, duration_minutes: duration },
      });
      setSlots(response.data.slots);
      setDepositAmount(Number(response.data.deposit_amount));
    } catch (error) {
      setFeedback('Non riesco a caricare gli slot disponibili in questo momento.');
    } finally {
      setLoadingSlots(false);
    }
  }

  const selectedSlot = useMemo(
    () => slots.find((slot) => slot.start_time === selectedTime),
    [selectedTime, slots]
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedTime) {
      setFeedback('Seleziona prima un orario disponibile.');
      return;
    }

    setSubmitting(true);
    setFeedback('');

    try {
      const bookingResponse = await api.post<{ booking: BookingSummary }>('/public/bookings', {
        ...formData,
        booking_date: bookingDate,
        start_time: selectedTime,
        duration_minutes: duration,
        payment_provider: paymentProvider,
      });

      const booking = bookingResponse.data.booking;
      setLastBooking(booking);
      const checkoutResponse = await api.post<{ checkout_url: string }>(`/public/bookings/${booking.id}/checkout`);
      window.location.assign(checkoutResponse.data.checkout_url);
    } catch (error: any) {
      setFeedback(error?.response?.data?.detail || 'Non è stato possibile avviare la prenotazione.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8'>
        <header className='mb-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]'>
          <div className='rounded-[28px] border border-cyan-400/20 bg-slate-950/80 p-6 text-white shadow-soft'>
            <p className='mb-3 inline-flex rounded-full border border-cyan-400/30 px-3 py-1 text-xs font-semibold text-cyan-200'>Padel booking • 1 campo</p>
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
            <div className='mt-2 text-4xl font-bold text-slate-950'>€{depositAmount}</div>
            <p className='mt-2 text-sm text-slate-600'>Fino a 90 minuti paghi €20. Poi si aggiungono €10 per ogni ulteriore blocco da 30 minuti.</p>
            <div className='mt-4 rounded-2xl bg-slate-950 p-4 text-sm text-slate-100'>
              <p className='font-semibold'>Tariffe indicative per giocatore</p>
              <ul className='mt-2 space-y-1 text-slate-300'>
                {playerRates.map((rate) => (
                  <li key={rate}>• {rate}</li>
                ))}
              </ul>
              <p className='mt-3 text-xs text-slate-400'>Le tariffe sono solo informative e non cambiano la caparra online.</p>
            </div>
          </div>
        </header>

        <main className='grid gap-6 lg:grid-cols-[1.05fr_0.95fr]'>
          <section className='space-y-6'>
            <div className='surface-card'>
              <div className='mb-4 flex items-center gap-2'>
                <Calendar size={18} className='text-cyan-600' />
                <h2 className='section-title'>Scegli data e durata</h2>
              </div>
              <div className='grid gap-4 sm:grid-cols-2'>
                <div>
                  <label className='field-label'>Data</label>
                  <input className='text-input' type='date' value={bookingDate} min={tomorrow} onChange={(e) => setBookingDate(e.target.value)} />
                </div>
                <div>
                  <label className='field-label'>Durata</label>
                  <select className='text-input' value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
                    {DURATIONS.map((minutes) => (
                      <option key={minutes} value={minutes}>{minutes} minuti</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className='mt-5'>
                <div className='mb-3 flex items-center justify-between'>
                  <p className='text-sm font-semibold text-slate-700'>Orari disponibili</p>
                  {loadingSlots && <p className='text-sm text-slate-500'>Caricamento...</p>}
                </div>
                <div className='grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5'>
                  {slots.map((slot) => (
                    <button
                      key={`${slot.start_time}-${slot.end_time}`}
                      type='button'
                      onClick={() => slot.available && setSelectedTime(slot.start_time)}
                      disabled={!slot.available}
                      className={`rounded-2xl border px-3 py-3 text-sm font-medium transition ${
                        selectedTime === slot.start_time
                          ? 'border-cyan-600 bg-cyan-50 text-cyan-800'
                          : slot.available
                            ? 'border-slate-200 bg-white text-slate-700 hover:border-slate-400'
                            : 'cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400'
                      }`}
                    >
                      {slot.start_time}
                    </button>
                  ))}
                </div>
                {selectedSlot && (
                  <p className='mt-3 text-sm text-emerald-700'>Hai selezionato {selectedSlot.start_time} → {selectedSlot.end_time}</p>
                )}
              </div>
            </div>
          </section>

          <section className='space-y-6'>
            <div className='surface-card'>
              <h2 className='section-title'>Completa la prenotazione</h2>
              <p className='mt-1 text-sm text-slate-600'>Inserisci i tuoi dati e scegli come versare la caparra.</p>

              <form className='mt-5 space-y-4' onSubmit={handleSubmit}>
                <div className='grid gap-4 sm:grid-cols-2'>
                  <div>
                    <label className='field-label'>Nome</label>
                    <input className='text-input' value={formData.first_name} onChange={(e) => setFormData((prev) => ({ ...prev, first_name: e.target.value }))} required />
                  </div>
                  <div>
                    <label className='field-label'>Cognome</label>
                    <input className='text-input' value={formData.last_name} onChange={(e) => setFormData((prev) => ({ ...prev, last_name: e.target.value }))} required />
                  </div>
                  <div>
                    <label className='field-label'>Telefono</label>
                    <input className='text-input' value={formData.phone} onChange={(e) => setFormData((prev) => ({ ...prev, phone: e.target.value }))} required />
                  </div>
                  <div>
                    <label className='field-label'>Email</label>
                    <input className='text-input' type='email' value={formData.email} onChange={(e) => setFormData((prev) => ({ ...prev, email: e.target.value }))} required />
                  </div>
                </div>

                <div>
                  <label className='field-label'>Nota facoltativa</label>
                  <textarea className='text-input min-h-24' value={formData.note} onChange={(e) => setFormData((prev) => ({ ...prev, note: e.target.value }))} />
                </div>

                <div className='rounded-2xl border border-slate-200 bg-slate-50 p-4'>
                  <p className='text-sm font-semibold text-slate-800'>Metodo pagamento caparra</p>
                  <div className='mt-3 grid gap-2 sm:grid-cols-2'>
                    {(['STRIPE', 'PAYPAL'] as PaymentProvider[]).map((provider) => (
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
                  <p>Inizio: <strong>{selectedTime || 'Seleziona uno slot'}</strong></p>
                  <p>Durata: <strong>{duration} minuti</strong></p>
                  <p>Caparra online: <strong>€{depositAmount}</strong></p>
                  <p className='mt-2 text-xs text-slate-600'>Il saldo residuo viene pagato direttamente al campo.</p>
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

                {feedback && <div className='rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700'>{feedback}</div>}
                {lastBooking && !feedback && (
                  <div className='rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700'>Richiesta creata con codice {lastBooking.public_reference}. Reindirizzamento al pagamento in corso…</div>
                )}

                <button className='btn-primary w-full' type='submit' disabled={submitting || loadingSlots}>
                  {submitting ? 'Sto preparando il checkout…' : 'Continua al pagamento della caparra'}
                </button>
              </form>
            </div>
          </section>
        </main>
      </div>
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
