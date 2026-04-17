import { CalendarClock, ClipboardList, Repeat2, Settings2 } from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AdminBookingCard } from '../components/AdminBookingCard';
import { AlertBanner } from '../components/AlertBanner';
import { AppBrand } from '../components/AppBrand';
import { EmptyState } from '../components/EmptyState';
import { LoadingBlock } from '../components/LoadingBlock';
import { SectionCard } from '../components/SectionCard';
import { getAvailability } from '../services/publicApi';
import {
  createAdminBooking,
  createBlackout,
  createRecurring,
  getAdminReport,
  getAdminSession,
  getAdminSettings,
  listAdminBookings,
  listAdminEvents,
  listBlackouts,
  logoutAdmin,
  markAdminBalancePaid,
  previewRecurring,
  updateAdminBookingStatus,
  updateAdminSettings,
} from '../services/adminApi';
import type { AdminEvent, AdminManualBookingPayload, AdminSettings, BlackoutItem, BookingSummary, RecurringOccurrence, ReportResponse, TimeSlot } from '../types';
import { formatCurrency, formatDateTime, toDateInputValue } from '../utils/format';

const today = toDateInputValue(new Date());

function getRequestStatus(error: any) {
  return error?.response?.status;
}

function getRequestMessage(error: any, fallback: string) {
  return error?.response?.data?.detail || fallback;
}

export function AdminDashboardPage() {
  const navigate = useNavigate();
  const [bookings, setBookings] = useState<BookingSummary[]>([]);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [events, setEvents] = useState<AdminEvent[]>([]);
  const [blackouts, setBlackouts] = useState<BlackoutItem[]>([]);
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ tone: 'error' | 'success'; message: string } | null>(null);
  const [filters, setFilters] = useState({ booking_date: '', status: '', payment_provider: '', customer: '' });
  const [manualForm, setManualForm] = useState<AdminManualBookingPayload>({
    first_name: 'Mario',
    last_name: 'Rossi',
    phone: '3331234567',
    email: 'mario@example.com',
    note: '',
    booking_date: today,
    start_time: '18:00',
    slot_id: null,
    duration_minutes: 90,
    payment_provider: 'NONE',
  });
  const [manualSlots, setManualSlots] = useState<TimeSlot[]>([]);
  const [blackoutForm, setBlackoutForm] = useState({
    title: 'Manutenzione ordinaria',
    reason: 'Pulizia e controllo rete',
    start_at: `${today}T12:00`,
    end_at: `${today}T13:30`,
  });
  const [recurringForm, setRecurringForm] = useState({ label: 'Allenamento fisso', weekday: 2, start_date: today, weeks_count: 6, start_time: '20:00', duration_minutes: 90 });
  const [recurringPreview, setRecurringPreview] = useState<RecurringOccurrence[]>([]);
  const manualMatchingSlots = useMemo(
    () => manualSlots.filter((slot) => slot.start_time === manualForm.start_time),
    [manualSlots, manualForm.start_time]
  );

  useEffect(() => {
    void bootstrap();
  }, []);

  useEffect(() => {
    let ignore = false;

    async function loadManualSlots() {
      try {
        const response = await getAvailability(manualForm.booking_date, manualForm.duration_minutes);
        if (!ignore) {
          setManualSlots(response.slots);
        }
      } catch {
        if (!ignore) {
          setManualSlots([]);
        }
      }
    }

    void loadManualSlots();

    return () => {
      ignore = true;
    };
  }, [manualForm.booking_date, manualForm.duration_minutes]);

  useEffect(() => {
    if (manualMatchingSlots.length === 0) {
      if (manualForm.slot_id) {
        setManualForm((prev) => ({ ...prev, slot_id: null }));
      }
      return;
    }

    if (manualMatchingSlots.some((slot) => slot.slot_id === manualForm.slot_id)) {
      return;
    }

    setManualForm((prev) => ({ ...prev, slot_id: manualMatchingSlots[0].slot_id }));
  }, [manualForm.slot_id, manualMatchingSlots]);

  async function bootstrap() {
    setLoading(true);
    setFeedback(null);
    try {
      await getAdminSession();
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate('/admin/login');
        return;
      }
      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Non riesco a verificare la sessione admin in questo momento.') });
      setLoading(false);
      return;
    }

    try {
      const results = await Promise.allSettled([loadBookings(), loadReport(), loadEvents(), loadBlackouts(), loadSettings()]);
      const unauthorized = results.find((result) => result.status === 'rejected' && getRequestStatus(result.reason) === 401);
      if (unauthorized) {
        navigate('/admin/login');
        return;
      }

      const failures = results.filter((result) => result.status === 'rejected');
      if (failures.length > 0) {
        setFeedback({ tone: 'error', message: 'Dashboard caricata solo parzialmente. Alcuni pannelli non sono disponibili al momento.' });
      }
    } finally {
      setLoading(false);
    }
  }

  async function loadBookings() {
    const response = await listAdminBookings(filters);
    setBookings(response.items);
  }

  async function loadReport() {
    const response = await getAdminReport();
    setReport(response);
  }

  async function loadEvents() {
    const response = await listAdminEvents();
    setEvents(response);
  }

  async function loadBlackouts() {
    const response = await listBlackouts();
    setBlackouts(response);
  }

  async function loadSettings() {
    const response = await getAdminSettings();
    setSettings(response);
  }

  async function refreshBookings(fallbackMessage: string) {
    setFeedback(null);
    try {
      await loadBookings();
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate('/admin/login');
        return;
      }
      setFeedback({ tone: 'error', message: getRequestMessage(error, fallbackMessage) });
    }
  }

  async function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await refreshBookings('Applicazione filtri non riuscita.');
  }

  async function createManualBooking(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    try {
      await createAdminBooking(manualForm);
      setFeedback({ tone: 'success', message: 'Prenotazione manuale creata con successo.' });
      await Promise.all([loadBookings(), loadReport(), loadEvents()]);
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Creazione prenotazione non riuscita.' });
    }
  }

  async function submitBlackout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    try {
      await createBlackout(blackoutForm);
      setFeedback({ tone: 'success', message: 'Blackout creato correttamente.' });
      await Promise.all([loadBookings(), loadEvents(), loadBlackouts()]);
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Creazione blackout non riuscita.' });
    }
  }

  async function submitRecurringPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const response = await previewRecurring(recurringForm);
      setRecurringPreview(response.occurrences);
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Preview ricorrenza non disponibile.' });
    }
  }

  async function createRecurringSeries() {
    setFeedback(null);
    try {
      const response = await createRecurring(recurringForm);
      setFeedback({ tone: 'success', message: `Serie creata. Occorrenze create: ${response.created_count}. Saltate: ${response.skipped_count}.` });
      await Promise.all([loadBookings(), loadReport(), loadEvents()]);
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Creazione serie ricorrente non riuscita.' });
    }
  }

  async function markBookingState(bookingId: string, status: 'CONFIRMED' | 'COMPLETED' | 'NO_SHOW' | 'CANCELLED') {
    setFeedback(null);
    try {
      await updateAdminBookingStatus(bookingId, { status });
      await Promise.all([loadBookings(), loadReport(), loadEvents()]);
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate('/admin/login');
        return;
      }
      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Aggiornamento stato non riuscito.') });
    }
  }

  async function markBalancePaid(bookingId: string) {
    setFeedback(null);
    try {
      await markAdminBalancePaid(bookingId);
      await Promise.all([loadBookings(), loadEvents()]);
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate('/admin/login');
        return;
      }
      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Marcatura saldo non riuscita.') });
    }
  }

  async function saveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!settings) return;
    setFeedback(null);
    try {
      const response = await updateAdminSettings({
        booking_hold_minutes: settings.booking_hold_minutes,
        cancellation_window_hours: settings.cancellation_window_hours,
        reminder_window_hours: settings.reminder_window_hours,
      });
      setSettings(response);
      setFeedback({ tone: 'success', message: 'Regole operative aggiornate.' });
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Aggiornamento settings non riuscito.' });
    }
  }

  async function logout() {
    await logoutAdmin();
    navigate('/admin/login');
  }

  return (
    <div className='min-h-screen px-4 py-6 sm:px-6 lg:px-8'>
      <div className='page-shell space-y-6'>
        <div className='flex flex-col gap-3 rounded-[28px] border border-cyan-400/20 bg-slate-950/80 p-5 text-white shadow-soft sm:flex-row sm:items-center sm:justify-between'>
          <div>
            <AppBrand light />
            <p className='mt-4 text-sm font-semibold text-cyan-200'>Dashboard admin</p>
            <h1 className='text-3xl font-bold'>Controllo prenotazioni e operatività</h1>
          </div>
          <button onClick={logout} className='btn-secondary'>Esci</button>
        </div>

        {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

        {loading ? <LoadingBlock label='Sto sincronizzando dashboard, report e log…' /> : null}

        <div className='grid gap-4 md:grid-cols-4'>
          <StatCard title='Prenotazioni totali' value={String(report?.total_bookings ?? 0)} />
          <StatCard title='Confermate' value={String(report?.confirmed_bookings ?? 0)} />
          <StatCard title='In attesa' value={String(report?.pending_bookings ?? 0)} />
          <StatCard title='Caparre incassate' value={formatCurrency(report?.collected_deposits ?? 0)} />
        </div>

        <div className='grid gap-6 xl:grid-cols-[1.2fr_0.8fr]'>
          <div className='space-y-6'>
            <SectionCard
              title='Prenotazioni'
              description='Filtra, controlla stato e apri il dettaglio completo di ogni richiesta.'
              actions={<button className='btn-secondary' onClick={() => void refreshBookings('Aggiornamento prenotazioni non riuscito.')}>Aggiorna</button>}
              elevated
            >

              <form className='mb-4 grid gap-3 md:grid-cols-4' onSubmit={applyFilters}>
                <input className='text-input' type='date' value={filters.booking_date} onChange={(e) => setFilters((prev) => ({ ...prev, booking_date: e.target.value }))} />
                <select className='text-input' value={filters.status} onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))}>
                  <option value=''>Tutti gli stati</option>
                  <option value='PENDING_PAYMENT'>PENDING_PAYMENT</option>
                  <option value='CONFIRMED'>CONFIRMED</option>
                  <option value='CANCELLED'>CANCELLED</option>
                  <option value='COMPLETED'>COMPLETED</option>
                  <option value='NO_SHOW'>NO_SHOW</option>
                  <option value='EXPIRED'>EXPIRED</option>
                </select>
                <select className='text-input' value={filters.payment_provider} onChange={(e) => setFilters((prev) => ({ ...prev, payment_provider: e.target.value }))}>
                  <option value=''>Tutti i pagamenti</option>
                  <option value='STRIPE'>STRIPE</option>
                  <option value='PAYPAL'>PAYPAL</option>
                  <option value='NONE'>NONE</option>
                </select>
                <input className='text-input' placeholder='Cliente o riferimento' value={filters.customer} onChange={(e) => setFilters((prev) => ({ ...prev, customer: e.target.value }))} />
                <button className='btn-primary' type='submit'>Filtra</button>
              </form>

              {bookings.length === 0 ? (
                <EmptyState icon={ClipboardList} title='Nessuna prenotazione per questi filtri' description='Allarga i filtri oppure crea una prenotazione manuale dal pannello laterale.' />
              ) : (
                <div className='space-y-3'>
                  {bookings.map((booking) => (
                    <AdminBookingCard key={booking.id} booking={booking} onMarkBalancePaid={markBalancePaid} onUpdateStatus={markBookingState} />
                  ))}
                </div>
              )}
            </SectionCard>

            <SectionCard title='Log essenziali' description='Traccia sintetica di booking, pagamenti e operazioni admin.'>
              {events.length === 0 ? (
                <EmptyState icon={CalendarClock} title='Nessun evento recente' description='I log business compariranno qui dopo le prime operazioni.' />
              ) : (
                <div className='space-y-2'>
                  {events.map((event) => (
                    <div key={event.id} className='rounded-2xl bg-slate-50 px-4 py-3 text-sm'>
                      <div className='flex items-center justify-between gap-3'>
                        <span className='font-semibold text-slate-800'>{event.event_type}</span>
                        <span className='text-xs text-slate-500'>{formatDateTime(event.created_at)}</span>
                      </div>
                      <p className='mt-1 text-slate-600'>{event.message}</p>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>
          </div>

          <div className='space-y-6'>
            <SectionCard title='Prenotazione manuale' description='Inserisci rapidamente una prenotazione confermata dal pannello admin.'>
              <form className='mt-4 space-y-3' onSubmit={createManualBooking}>
                <input className='text-input' placeholder='Nome' value={manualForm.first_name} onChange={(e) => setManualForm((prev) => ({ ...prev, first_name: e.target.value }))} />
                <input className='text-input' placeholder='Cognome' value={manualForm.last_name} onChange={(e) => setManualForm((prev) => ({ ...prev, last_name: e.target.value }))} />
                <input className='text-input' placeholder='Telefono' value={manualForm.phone} onChange={(e) => setManualForm((prev) => ({ ...prev, phone: e.target.value }))} />
                <input className='text-input' placeholder='Email' value={manualForm.email} onChange={(e) => setManualForm((prev) => ({ ...prev, email: e.target.value }))} />
                <div className='grid grid-cols-2 gap-2'>
                  <input className='text-input' type='date' value={manualForm.booking_date} onChange={(e) => setManualForm((prev) => ({ ...prev, booking_date: e.target.value, slot_id: null }))} />
                  <input className='text-input' type='time' value={manualForm.start_time} onChange={(e) => setManualForm((prev) => ({ ...prev, start_time: e.target.value, slot_id: null }))} />
                </div>
                <select className='text-input' value={manualForm.duration_minutes} onChange={(e) => setManualForm((prev) => ({ ...prev, duration_minutes: Number(e.target.value) }))}>
                  {[60, 90, 120, 150, 180, 210, 240, 270, 300].map((value) => <option key={value} value={value}>{value} minuti</option>)}
                </select>
                {manualMatchingSlots.length > 1 ? (
                  <div className='space-y-1'>
                    <label className='field-label' htmlFor='manual-slot-id'>Occorrenza slot</label>
                    <select
                      id='manual-slot-id'
                      className='text-input'
                      value={manualForm.slot_id || ''}
                      onChange={(e) => setManualForm((prev) => ({ ...prev, slot_id: e.target.value || null }))}
                    >
                      {manualMatchingSlots.map((slot) => (
                        <option key={slot.slot_id} value={slot.slot_id}>{slot.display_start_time} → {slot.display_end_time}</option>
                      ))}
                    </select>
                    <p className='text-xs text-slate-500'>Seleziona l'occorrenza corretta quando l'ora locale compare due volte per il cambio ora.</p>
                  </div>
                ) : null}
                <textarea className='text-input min-h-20' placeholder='Nota interna o dettaglio cliente' value={manualForm.note} onChange={(e) => setManualForm((prev) => ({ ...prev, note: e.target.value }))} />
                <button className='btn-primary w-full' type='submit'>Crea prenotazione</button>
              </form>
            </SectionCard>

            <SectionCard title='Blocca fascia oraria' description='Usa i blackout per manutenzioni, tornei o indisponibilità tecniche.'>
              <form className='mt-4 space-y-3' onSubmit={submitBlackout}>
                <input className='text-input' value={blackoutForm.title} onChange={(e) => setBlackoutForm((prev) => ({ ...prev, title: e.target.value }))} />
                <input className='text-input' value={blackoutForm.reason} onChange={(e) => setBlackoutForm((prev) => ({ ...prev, reason: e.target.value }))} />
                <input className='text-input' type='datetime-local' value={blackoutForm.start_at} onChange={(e) => setBlackoutForm((prev) => ({ ...prev, start_at: e.target.value }))} />
                <input className='text-input' type='datetime-local' value={blackoutForm.end_at} onChange={(e) => setBlackoutForm((prev) => ({ ...prev, end_at: e.target.value }))} />
                <button className='btn-primary w-full' type='submit'>Crea blackout</button>
              </form>
              <div className='mt-4 space-y-2'>
                {blackouts.length === 0 ? (
                  <EmptyState icon={CalendarClock} title='Nessun blackout attivo' description='Le chiusure compariranno qui appena create.' />
                ) : (
                  blackouts.slice(0, 3).map((blackout) => (
                    <div key={blackout.id} className='rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700'>
                      <p className='font-semibold text-slate-900'>{blackout.title}</p>
                      <p className='mt-1'>{formatDateTime(blackout.start_at)} → {formatDateTime(blackout.end_at)}</p>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>

            <SectionCard title='Serie ricorrente' description='Crea una ricorrenza nello stesso anno solare e controlla subito i conflitti.'>
              <form className='mt-4 space-y-3' onSubmit={submitRecurringPreview}>
                <input className='text-input' value={recurringForm.label} onChange={(e) => setRecurringForm((prev) => ({ ...prev, label: e.target.value }))} />
                <div className='grid grid-cols-2 gap-2'>
                  <input className='text-input' type='date' value={recurringForm.start_date} onChange={(e) => setRecurringForm((prev) => ({ ...prev, start_date: e.target.value }))} />
                  <select className='text-input' value={recurringForm.weekday} onChange={(e) => setRecurringForm((prev) => ({ ...prev, weekday: Number(e.target.value) }))}>
                    <option value={0}>Lunedì</option>
                    <option value={1}>Martedì</option>
                    <option value={2}>Mercoledì</option>
                    <option value={3}>Giovedì</option>
                    <option value={4}>Venerdì</option>
                    <option value={5}>Sabato</option>
                    <option value={6}>Domenica</option>
                  </select>
                </div>
                <div className='grid grid-cols-3 gap-2'>
                  <input className='text-input' type='time' value={recurringForm.start_time} onChange={(e) => setRecurringForm((prev) => ({ ...prev, start_time: e.target.value }))} />
                  <select className='text-input' value={recurringForm.duration_minutes} onChange={(e) => setRecurringForm((prev) => ({ ...prev, duration_minutes: Number(e.target.value) }))}>
                    {[60, 90, 120, 150, 180, 210, 240, 270, 300].map((value) => <option key={value} value={value}>{value} min</option>)}
                  </select>
                  <input className='text-input' type='number' min={1} max={52} value={recurringForm.weeks_count} onChange={(e) => setRecurringForm((prev) => ({ ...prev, weeks_count: Number(e.target.value) }))} />
                </div>
                <div className='grid gap-2 sm:grid-cols-2'>
                  <button className='btn-secondary' type='submit'>Preview conflitti</button>
                  <button className='btn-primary' type='button' onClick={() => void createRecurringSeries()}>Crea serie</button>
                </div>
              </form>

              {recurringPreview.length > 0 && (
                <div className='mt-4 space-y-2'>
                  {recurringPreview.map((item) => (
                    <div key={`${item.booking_date}-${item.start_time}`} className={`rounded-2xl px-4 py-3 text-sm ${item.available ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'}`}>
                      {item.booking_date} • {item.display_start_time} → {item.display_end_time} • {item.available ? 'ok' : item.reason}
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>

            <SectionCard title='Regole operative' description='Controlla hold pagamento, soglia rimborso e reminder.'>
              {!settings ? (
                <LoadingBlock label='Sto caricando le impostazioni admin…' />
              ) : (
                <form className='space-y-3' onSubmit={saveSettings}>
                  <div className='grid gap-3 sm:grid-cols-3'>
                    <div>
                      <label className='field-label'>Hold pagamento</label>
                      <input className='text-input' type='number' min={5} max={120} value={settings.booking_hold_minutes} onChange={(e) => setSettings((prev) => prev ? { ...prev, booking_hold_minutes: Number(e.target.value) } : prev)} />
                    </div>
                    <div>
                      <label className='field-label'>Soglia rimborso annullamento</label>
                      <input className='text-input' type='number' min={1} max={168} value={settings.cancellation_window_hours} onChange={(e) => setSettings((prev) => prev ? { ...prev, cancellation_window_hours: Number(e.target.value) } : prev)} />
                    </div>
                    <div>
                      <label className='field-label'>Reminder</label>
                      <input className='text-input' type='number' min={1} max={168} value={settings.reminder_window_hours} onChange={(e) => setSettings((prev) => prev ? { ...prev, reminder_window_hours: Number(e.target.value) } : prev)} />
                    </div>
                  </div>
                  <div className='surface-muted'>
                    <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Provider</p>
                    <p className='mt-2 text-sm text-slate-700'>Stripe: <strong>{settings.stripe_enabled ? 'disponibile' : 'non disponibile'}</strong> • PayPal: <strong>{settings.paypal_enabled ? 'disponibile' : 'non disponibile'}</strong></p>
                  </div>
                  <button className='btn-primary w-full' type='submit'>Salva regole</button>
                </form>
              )}
            </SectionCard>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <div className='surface-card'>
      <p className='text-sm text-slate-500'>{title}</p>
      <p className='mt-2 text-3xl font-bold text-slate-950'>{value}</p>
    </div>
  );
}
