import { CalendarClock, ChevronDown, ChevronUp } from 'lucide-react';
import { FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { AdminNav } from '../components/AdminNav';
import { AdminTimeSlotPicker } from '../components/AdminTimeSlotPicker';
import { AlertBanner } from '../components/AlertBanner';
import { AppBrand } from '../components/AppBrand';
import { DateFieldWithDay } from '../components/DateFieldWithDay';
import { EmptyState } from '../components/EmptyState';
import { LoadingBlock } from '../components/LoadingBlock';
import { SectionCard } from '../components/SectionCard';
import {
  createAdminBooking,
  createBlackout,
  createRecurring,
  getAdminReport,
  getAdminSession,
  getAdminSettings,
  getSubscriptionStatus,
  listBlackouts,
  logoutAdmin,
  previewRecurring,
  updateAdminSettings,
} from '../services/adminApi';
import type { AdminManualBookingPayload, AdminSession, AdminSettings, BlackoutItem, RecurringOccurrence, RecurringSeriesPayload, ReportResponse, SubscriptionStatusBanner } from '../types';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';
import { formatCurrency, formatDate, formatDateTime, formatWeekdayLabel, toDateInputValue } from '../utils/format';

const today = toDateInputValue(new Date());
const DURATIONS = [60, 90, 120, 150, 180, 210, 240, 270, 300];
const SUBTLE_LINK_CLASS = 'inline-flex min-h-10 items-center justify-center gap-2 rounded-full px-3 py-2 text-sm font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-cyan-100';

function getRequestStatus(error: any) {
  return error?.response?.status;
}

function getRequestMessage(error: any, fallback: string) {
  return error?.response?.data?.detail || fallback;
}

function getRecurringWeekday(dateValue: string) {
  const [year, month, day] = dateValue.split('-').map(Number);
  if (!year || !month || !day) {
    return 0;
  }

  const normalizedDate = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
  return (normalizedDate.getUTCDay() + 6) % 7;
}

function addWeeksToDateInput(dateValue: string, weeksToAdd: number) {
  const [year, month, day] = dateValue.split('-').map(Number);
  if (!year || !month || !day) {
    return dateValue;
  }

  const normalizedDate = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
  normalizedDate.setUTCDate(normalizedDate.getUTCDate() + (weeksToAdd * 7));
  return normalizedDate.toISOString().slice(0, 10);
}

export function AdminDashboardPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const tenantSlug = getTenantSlugFromSearchParams(searchParams);
  const [session, setSession] = useState<AdminSession | null>(null);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [blackouts, setBlackouts] = useState<BlackoutItem[]>([]);
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionStatusBanner | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ tone: 'error' | 'success'; message: string } | null>(null);
  const [manualForm, setManualForm] = useState<AdminManualBookingPayload>({
    first_name: 'Mario',
    last_name: 'Rossi',
    phone: '3331234567',
    email: 'mario@example.com',
    note: '',
    booking_date: today,
    start_time: '',
    slot_id: null,
    duration_minutes: 90,
    payment_provider: 'NONE',
  });
  const [blackoutForm, setBlackoutForm] = useState({
    title: 'Manutenzione ordinaria',
    reason: 'Pulizia e controllo rete',
    start_at: `${today}T12:00`,
    end_at: `${today}T13:30`,
  });
  const [recurringForm, setRecurringForm] = useState<RecurringSeriesPayload>({
    label: 'Allenamento fisso',
    weekday: getRecurringWeekday(today),
    start_date: today,
    end_date: addWeeksToDateInput(today, 5),
    start_time: '',
    slot_id: null,
    duration_minutes: 90,
  });
  const [recurringPreview, setRecurringPreview] = useState<RecurringOccurrence[]>([]);
  const adminTimezone = settings?.timezone || session?.timezone || null;

  useEffect(() => {
    void bootstrap();
  }, [tenantSlug]);

  function redirectToLogin() {
    navigate(withTenantPath('/admin/login', tenantSlug));
  }

  async function bootstrap() {
    setLoading(true);
    setFeedback(null);
    try {
      const sessionResponse = await getAdminSession(tenantSlug);
      setSession(sessionResponse);
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        redirectToLogin();
        return;
      }
      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Non riesco a verificare la sessione admin in questo momento.') });
      setLoading(false);
      return;
    }

    try {
      const results = await Promise.allSettled([loadReport(), loadBlackouts(), loadSettings(), loadSubscription()]);
      const unauthorized = results.find((result) => result.status === 'rejected' && getRequestStatus(result.reason) === 401);
      if (unauthorized) {
        redirectToLogin();
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

  async function loadReport() {
    const response = await getAdminReport();
    setReport(response);
  }

  async function loadBlackouts() {
    const response = await listBlackouts();
    setBlackouts(response);
  }

  async function loadSettings() {
    const response = await getAdminSettings();
    setSettings(response);
  }

  async function loadSubscription() {
    try {
      const response = await getSubscriptionStatus(tenantSlug);
      setSubscription(response);
    } catch {
      // Subscription non critica: non blocca la dashboard
    }
  }

  async function refreshDashboard() {
    setFeedback(null);
    try {
      await Promise.all([loadReport(), loadBlackouts(), loadSettings()]);
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        redirectToLogin();
        return;
      }
      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Aggiornamento dashboard non riuscito.') });
    }
  }

  async function createManualBooking(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!manualForm.slot_id || !manualForm.start_time) {
      setFeedback({ tone: 'error', message: 'Seleziona un orario disponibile per la prenotazione manuale.' });
      return;
    }

    setFeedback(null);
    try {
      await createAdminBooking(manualForm);
      setFeedback({ tone: 'success', message: 'Prenotazione manuale creata con successo.' });
      await loadReport();
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
      await loadBlackouts();
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Creazione blackout non riuscita.' });
    }
  }

  async function submitRecurringPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!recurringForm.start_time || !recurringForm.slot_id) {
      setFeedback({ tone: 'error', message: 'Seleziona un orario disponibile per la serie ricorrente.' });
      return;
    }

    if (recurringForm.end_date < recurringForm.start_date) {
      setFeedback({ tone: 'error', message: 'La data fine serie deve essere uguale o successiva alla data di partenza.' });
      return;
    }

    try {
      const response = await previewRecurring(recurringForm);
      setRecurringPreview(response.occurrences);
      setFeedback(null);
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Preview ricorrenza non disponibile.' });
    }
  }

  async function createRecurringSeries() {
    if (!recurringForm.start_time || !recurringForm.slot_id) {
      setFeedback({ tone: 'error', message: 'Seleziona un orario disponibile per la serie ricorrente.' });
      return;
    }

    if (recurringForm.end_date < recurringForm.start_date) {
      setFeedback({ tone: 'error', message: 'La data fine serie deve essere uguale o successiva alla data di partenza.' });
      return;
    }

    setFeedback(null);
    try {
      const response = await createRecurring(recurringForm);
      setFeedback({ tone: 'success', message: `Serie creata. Occorrenze create: ${response.created_count}. Saltate: ${response.skipped_count}.` });
      await loadReport();
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Creazione serie ricorrente non riuscita.' });
    }
  }

  async function saveSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!settings) return;
    setFeedback(null);
    try {
      const response = await updateAdminSettings({
        public_name: settings.public_name,
        notification_email: settings.notification_email,
        support_email: settings.support_email || null,
        support_phone: settings.support_phone || null,
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
    await logoutAdmin(tenantSlug);
    redirectToLogin();
  }

  return (
    <div className='min-h-screen px-4 py-6 sm:px-6 lg:px-8'>
      <div className='page-shell space-y-6'>
        <div className='admin-hero-panel relative space-y-4'>
          <div className='lg:pr-72'>
            <div className='admin-hero-copy'>
              <AppBrand light label='Padly' />
              <p className='admin-hero-kicker mt-4'>Dashboard admin</p>
              <h1 className='admin-hero-heading'>Prenotazioni e operatività</h1>
              <p className='admin-hero-description'>La dashboard resta focalizzata su creazione rapida, serie ricorrenti, blackout e regole operative.</p>
            </div>
          </div>
          <div className='admin-hero-actions lg:absolute lg:right-5 lg:top-5 lg:w-auto'>
            <button onClick={() => void refreshDashboard()} className='admin-hero-button-primary'>Aggiorna pagina</button>
            <button onClick={logout} className='admin-hero-button-secondary'>Esci</button>
          </div>
          <AdminNav session={session} notificationEmail={settings?.notification_email || null} />
        </div>

        {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

        {subscription ? <SubscriptionBanner subscription={subscription} /> : null}

        {loading ? <LoadingBlock label='Sto sincronizzando dashboard, blackout e regole operative…' /> : null}

        <div className='grid gap-6 xl:grid-cols-[1.05fr_0.95fr]'>
          <div className='space-y-6'>
            <SectionCard title='Prenotazione manuale' description='Inserisci rapidamente una prenotazione confermata dal pannello admin.' collapsible defaultExpanded={false}>
              <form className='mt-4 space-y-4' onSubmit={createManualBooking}>
                <div className='grid gap-3 sm:grid-cols-2'>
                  <div>
                    <label className='field-label' htmlFor='admin-manual-first-name'>Nome</label>
                    <input id='admin-manual-first-name' className='text-input' value={manualForm.first_name} onChange={(event) => setManualForm((prev) => ({ ...prev, first_name: event.target.value }))} />
                  </div>
                  <div>
                    <label className='field-label' htmlFor='admin-manual-last-name'>Cognome</label>
                    <input id='admin-manual-last-name' className='text-input' value={manualForm.last_name} onChange={(event) => setManualForm((prev) => ({ ...prev, last_name: event.target.value }))} />
                  </div>
                  <div>
                    <label className='field-label' htmlFor='admin-manual-phone'>Telefono</label>
                    <input id='admin-manual-phone' className='text-input' value={manualForm.phone} onChange={(event) => setManualForm((prev) => ({ ...prev, phone: event.target.value }))} />
                  </div>
                  <div>
                    <label className='field-label' htmlFor='admin-manual-email'>Email</label>
                    <input id='admin-manual-email' className='text-input' type='email' value={manualForm.email} onChange={(event) => setManualForm((prev) => ({ ...prev, email: event.target.value }))} />
                  </div>
                </div>

                <div className='grid gap-4 sm:grid-cols-[1fr_220px]'>
                  <DateFieldWithDay
                    id='admin-manual-date'
                    label='Data prenotazione'
                    value={manualForm.booking_date}
                    min={today}
                    onChange={(value) => setManualForm((prev) => ({ ...prev, booking_date: value, start_time: '', slot_id: null }))}
                  />
                  <div>
                    <label className='field-label' htmlFor='admin-manual-duration'>Durata</label>
                    <select
                      id='admin-manual-duration'
                      className='text-input'
                      value={manualForm.duration_minutes}
                      onChange={(event) => setManualForm((prev) => ({ ...prev, duration_minutes: Number(event.target.value), start_time: '', slot_id: null }))}
                    >
                      {DURATIONS.map((value) => <option key={value} value={value}>{value} minuti</option>)}
                    </select>
                  </div>
                </div>

                <div>
                  <p className='field-label'>Orario</p>
                  <AdminTimeSlotPicker
                    bookingDate={manualForm.booking_date}
                    durationMinutes={manualForm.duration_minutes}
                    selectedSlotId={manualForm.slot_id || ''}
                    onSelect={(slot) => setManualForm((prev) => ({ ...prev, start_time: slot.start_time, slot_id: slot.slot_id }))}
                  />
                </div>

                <div>
                  <label className='field-label' htmlFor='admin-manual-note'>Nota interna</label>
                  <textarea id='admin-manual-note' className='text-input min-h-24' value={manualForm.note} onChange={(event) => setManualForm((prev) => ({ ...prev, note: event.target.value }))} />
                </div>

                <button className='btn-primary w-full' type='submit'>Crea prenotazione</button>
              </form>
            </SectionCard>

            <SectionCard title='Serie ricorrente' description='Crea una ricorrenza fino a una data finale e controlla subito eventuali conflitti.' collapsible defaultExpanded={false}>
              <form className='mt-4 space-y-4' onSubmit={submitRecurringPreview}>
                <div>
                  <label className='field-label' htmlFor='admin-recurring-label'>Nome serie ricorrente</label>
                  <input id='admin-recurring-label' className='text-input' value={recurringForm.label} onChange={(event) => setRecurringForm((prev) => ({ ...prev, label: event.target.value }))} />
                </div>

                <div className='grid gap-4 sm:grid-cols-2'>
                  <DateFieldWithDay
                    id='admin-recurring-date'
                    label='Data di partenza'
                    value={recurringForm.start_date}
                    min={today}
                    showDayPreview={false}
                    onChange={(value) => {
                      setRecurringForm((prev) => ({
                        ...prev,
                        start_date: value,
                        end_date: prev.end_date < value ? value : prev.end_date,
                        weekday: getRecurringWeekday(value),
                        start_time: '',
                        slot_id: null,
                      }));
                    }}
                  />
                  <DateFieldWithDay
                    id='admin-recurring-end-date'
                    label='Fino al'
                    value={recurringForm.end_date}
                    min={recurringForm.start_date}
                    showDayPreview={false}
                    onChange={(value) => setRecurringForm((prev) => ({ ...prev, end_date: value }))}
                  />
                </div>

                <div className='grid gap-4 sm:grid-cols-[1fr_220px]'>
                  <div className='surface-muted self-start'>
                    <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Giorno serie</p>
                    <p className='mt-2 text-base font-medium text-slate-900'>{formatWeekdayLabel(recurringForm.start_date)}</p>
                  </div>
                  <div className='surface-muted self-start'>
                    <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Ultima ricorrenza</p>
                    <p className='mt-2 text-base font-medium text-slate-900'>{formatWeekdayLabel(recurringForm.end_date)} {formatDate(recurringForm.end_date)}</p>
                  </div>
                </div>

                <div className='grid gap-3 sm:grid-cols-1'>
                  <div>
                    <label className='field-label' htmlFor='admin-recurring-duration'>Durata</label>
                    <select
                      id='admin-recurring-duration'
                      className='text-input'
                      value={recurringForm.duration_minutes}
                      onChange={(event) => {
                        setRecurringForm((prev) => ({ ...prev, duration_minutes: Number(event.target.value), start_time: '', slot_id: null }));
                      }}
                    >
                      {DURATIONS.map((value) => <option key={value} value={value}>{value} minuti</option>)}
                    </select>
                  </div>
                </div>

                <div>
                  <p className='field-label'>Orario della serie</p>
                  <AdminTimeSlotPicker
                    bookingDate={recurringForm.start_date}
                    durationMinutes={recurringForm.duration_minutes}
                    selectedSlotId={recurringForm.slot_id || ''}
                    onSelect={(slot) => {
                      setRecurringForm((prev) => ({ ...prev, start_time: slot.start_time, slot_id: slot.slot_id }));
                    }}
                  />
                </div>

                <div className='grid gap-2 sm:grid-cols-2'>
                  <button className='btn-secondary' type='submit'>Preview conflitti</button>
                  <button className='btn-primary' type='button' onClick={() => void createRecurringSeries()}>Crea serie</button>
                </div>
              </form>

              {recurringPreview.length > 0 ? (
                <div className='mt-4 space-y-2'>
                  {recurringPreview.map((item) => (
                    <div key={`${item.booking_date}-${item.start_time}`} className={item.available ? 'alert-success' : 'alert-warning'}>
                      {item.booking_date} • {item.display_start_time} → {item.display_end_time} • {item.available ? 'ok' : item.reason}
                    </div>
                  ))}
                </div>
              ) : null}
            </SectionCard>
          </div>

          <div className='space-y-6'>
            <SectionCard title='Blocca fascia oraria' description='Usa i blackout per manutenzioni, tornei o indisponibilità tecniche.' collapsible defaultExpanded={false}>
              <form className='mt-4 space-y-3' onSubmit={submitBlackout}>
                <div>
                  <label className='field-label' htmlFor='admin-blackout-title'>Titolo blackout</label>
                  <input id='admin-blackout-title' className='text-input' value={blackoutForm.title} onChange={(event) => setBlackoutForm((prev) => ({ ...prev, title: event.target.value }))} />
                </div>
                <div>
                  <label className='field-label' htmlFor='admin-blackout-reason'>Descrizione</label>
                  <input id='admin-blackout-reason' className='text-input' value={blackoutForm.reason} onChange={(event) => setBlackoutForm((prev) => ({ ...prev, reason: event.target.value }))} />
                </div>
                <div className='grid gap-3 sm:grid-cols-2'>
                  <DateFieldWithDay
                    id='admin-blackout-start-date'
                    label='Data inizio'
                    value={getLocalDatePart(blackoutForm.start_at)}
                    min={today}
                    onChange={(value) => setBlackoutForm((prev) => ({ ...prev, start_at: updateLocalDateTimePart(prev.start_at, 'date', value, today, '12:00') }))}
                  />
                  <div>
                    <label className='field-label' htmlFor='admin-blackout-start-time'>Ora inizio</label>
                    <input id='admin-blackout-start-time' className='text-input' type='time' value={getLocalTimePart(blackoutForm.start_at)} onChange={(event) => setBlackoutForm((prev) => ({ ...prev, start_at: updateLocalDateTimePart(prev.start_at, 'time', event.target.value, today, '12:00') }))} />
                  </div>
                </div>
                <div className='grid gap-3 sm:grid-cols-2'>
                  <DateFieldWithDay
                    id='admin-blackout-end-date'
                    label='Data fine'
                    value={getLocalDatePart(blackoutForm.end_at)}
                    min={getLocalDatePart(blackoutForm.start_at) || today}
                    onChange={(value) => setBlackoutForm((prev) => ({ ...prev, end_at: updateLocalDateTimePart(prev.end_at, 'date', value, getLocalDatePart(prev.start_at) || today, '13:30') }))}
                  />
                  <div>
                    <label className='field-label' htmlFor='admin-blackout-end-time'>Ora fine</label>
                    <input id='admin-blackout-end-time' className='text-input' type='time' value={getLocalTimePart(blackoutForm.end_at)} onChange={(event) => setBlackoutForm((prev) => ({ ...prev, end_at: updateLocalDateTimePart(prev.end_at, 'time', event.target.value, getLocalDatePart(prev.start_at) || today, '13:30') }))} />
                  </div>
                </div>
                <p className='text-xs text-slate-500'>Il blackout usa il fuso configurato{adminTimezone ? ` (${adminTimezone})` : ''}. Durante il ritorno all&apos;ora solare gli orari ambigui vengono rifiutati con un errore esplicito.</p>
                <button className='btn-primary w-full' type='submit'>Crea blackout</button>
              </form>
              <div className='mt-4 space-y-2'>
                {blackouts.length === 0 ? (
                  <EmptyState icon={CalendarClock} title='Nessun blackout attivo' description='Le chiusure compariranno qui appena create.' />
                ) : (
                  blackouts.slice(0, 3).map((blackout) => (
                    <div key={blackout.id} className='rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700'>
                      <p className='font-semibold text-slate-900'>{blackout.title}</p>
                      <p className='mt-1'>{formatDateTime(blackout.start_at, adminTimezone)} → {formatDateTime(blackout.end_at, adminTimezone)}</p>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>

            <SectionCard title='Profilo tenant e regole operative' description='Aggiorna nome pubblico, contatti operativi e regole del tenant attivo.' collapsible defaultExpanded={false}>
              {!settings ? (
                <LoadingBlock label='Sto caricando le impostazioni admin…' />
              ) : (
                <form className='space-y-3' onSubmit={saveSettings}>
                  <div className='grid gap-3 sm:grid-cols-2'>
                    <div>
                      <label className='field-label' htmlFor='admin-settings-public-name'>Nome pubblico tenant</label>
                      <input id='admin-settings-public-name' className='text-input' value={settings.public_name} onChange={(event) => setSettings((prev) => prev ? { ...prev, public_name: event.target.value } : prev)} />
                    </div>
                    <div>
                      <label className='field-label' htmlFor='admin-settings-notification-email'>Email notifiche operative</label>
                      <input id='admin-settings-notification-email' className='text-input' type='email' value={settings.notification_email} onChange={(event) => setSettings((prev) => prev ? { ...prev, notification_email: event.target.value } : prev)} />
                    </div>
                    <div>
                      <label className='field-label' htmlFor='admin-settings-support-email'>Email supporto pubblico</label>
                      <input id='admin-settings-support-email' className='text-input' type='email' value={settings.support_email || ''} onChange={(event) => setSettings((prev) => prev ? { ...prev, support_email: event.target.value || null } : prev)} />
                    </div>
                    <div>
                      <label className='field-label' htmlFor='admin-settings-support-phone'>Telefono supporto pubblico</label>
                      <input id='admin-settings-support-phone' className='text-input' value={settings.support_phone || ''} onChange={(event) => setSettings((prev) => prev ? { ...prev, support_phone: event.target.value || null } : prev)} />
                    </div>
                  </div>
                  <div className='grid gap-3 sm:grid-cols-3'>
                    <div>
                      <label className='field-label'>Hold pagamento</label>
                      <input className='text-input' type='number' min={5} max={120} value={settings.booking_hold_minutes} onChange={(event) => setSettings((prev) => prev ? { ...prev, booking_hold_minutes: Number(event.target.value) } : prev)} />
                    </div>
                    <div>
                      <label className='field-label'>Soglia rimborso annullamento</label>
                      <input className='text-input' type='number' min={1} max={168} value={settings.cancellation_window_hours} onChange={(event) => setSettings((prev) => prev ? { ...prev, cancellation_window_hours: Number(event.target.value) } : prev)} />
                    </div>
                    <div>
                      <label className='field-label'>Reminder</label>
                      <input className='text-input' type='number' min={1} max={168} value={settings.reminder_window_hours} onChange={(event) => setSettings((prev) => prev ? { ...prev, reminder_window_hours: Number(event.target.value) } : prev)} />
                    </div>
                  </div>
                  <div className='grid gap-3 sm:grid-cols-3'>
                    <div className='surface-muted'>
                      <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Slug tenant</p>
                      <p className='mt-2 text-sm font-medium text-slate-900'>{settings.club_slug}</p>
                    </div>
                    <div className='surface-muted'>
                      <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Timezone</p>
                      <p className='mt-2 text-sm font-medium text-slate-900'>{settings.timezone}</p>
                    </div>
                    <div className='surface-muted'>
                      <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Valuta</p>
                      <p className='mt-2 text-sm font-medium text-slate-900'>{settings.currency}</p>
                    </div>
                  </div>
                  <div className='surface-muted'>
                    <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Provider</p>
                    <p className='mt-2 text-sm text-slate-700'>Stripe: <strong>{settings.stripe_enabled ? 'disponibile' : 'non disponibile'}</strong> • PayPal: <strong>{settings.paypal_enabled ? 'disponibile' : 'non disponibile'}</strong></p>
                  </div>
                  <button className='btn-primary w-full' type='submit'>Salva impostazioni tenant</button>
                </form>
              )}
            </SectionCard>
          </div>
        </div>

      </div>
    </div>
  );
}

function getLocalDatePart(value: string) {
  return value.split('T')[0] || '';
}

function getLocalTimePart(value: string) {
  return value.split('T')[1]?.slice(0, 5) || '';
}

function updateLocalDateTimePart(
  value: string,
  part: 'date' | 'time',
  nextValue: string,
  fallbackDate: string,
  fallbackTime: string,
) {
  const currentDate = getLocalDatePart(value) || fallbackDate;
  const currentTime = getLocalTimePart(value) || fallbackTime;
  const nextDate = part === 'date' ? nextValue : currentDate;
  const nextTime = part === 'time' ? nextValue : currentTime;
  return `${nextDate}T${nextTime}`;
}

function StatCard({ title, value }: { title: string; value: string }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <section className='surface-card overflow-hidden p-0'>
      <button
        type='button'
        aria-expanded={expanded}
        aria-label={`${expanded ? 'Comprimi' : 'Espandi'} ${title}`}
        className='flex w-full items-center justify-between gap-3 px-5 py-4 text-left transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-cyan-100'
        onClick={() => setExpanded((prev) => !prev)}
      >
        <span className='text-sm font-medium text-slate-600'>{title}</span>
        <span className='flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-600'>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </span>
      </button>
      {expanded ? (
        <div className='border-t border-slate-100 px-5 pb-5 pt-3'>
          <p className='text-3xl font-bold text-slate-950'>{value}</p>
        </div>
      ) : null}
    </section>
  );
}

function SubscriptionBanner({ subscription }: { subscription: SubscriptionStatusBanner }) {
  const { status, plan_name, trial_ends_at, is_access_blocked } = subscription;

  const tone = is_access_blocked ? 'error' : status === 'PAST_DUE' ? 'error' : status === 'TRIALING' ? 'warning' : null;
  if (!tone) return null;

  let message = '';
  if (status === 'TRIALING' && trial_ends_at) {
    const ends = new Date(trial_ends_at).toLocaleDateString('it-IT', { day: '2-digit', month: 'long', year: 'numeric' });
    message = `Piano: ${plan_name} — periodo di prova attivo fino al ${ends}.`;
  } else if (status === 'PAST_DUE') {
    message = `Piano: ${plan_name} — pagamento in sospeso. Aggiorna il metodo di pagamento per evitare la sospensione.`;
  } else if (is_access_blocked) {
    message = `Account sospeso o abbonamento scaduto (piano: ${plan_name}). Contatta il supporto.`;
  }

  if (!message) return null;

  return <AlertBanner tone={tone === 'warning' ? 'error' : tone}>{message}</AlertBanner>;
}
