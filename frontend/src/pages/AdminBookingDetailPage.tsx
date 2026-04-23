import { ArrowLeft, CalendarDays, Mail, Phone, WalletCards } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { AdminTimeSlotPicker } from '../components/AdminTimeSlotPicker';
import { AlertBanner } from '../components/AlertBanner';
import { DateFieldWithDay } from '../components/DateFieldWithDay';
import { EmptyState } from '../components/EmptyState';
import { LoadingBlock } from '../components/LoadingBlock';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/StatusBadge';
import { cancelRecurringSeries, getAdminBooking, getAdminSession, listAdminCourts, markAdminBalancePaid, updateAdminBooking, updateAdminBookingStatus, updateRecurringSeries } from '../services/adminApi';
import type { AdminBookingUpdatePayload, AdminSession, BookingDetail, CourtSummary, RecurringSeriesPayload } from '../types';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';
import { canCancelBooking, canMarkBalancePaid, canMarkBookingCompleted, canMarkBookingNoShow, canRestoreBookingConfirmed } from '../utils/adminBookingActions';
import { formatCurrency, formatDateTime, formatTimeValue, formatWeekdayLabel } from '../utils/format';

const DURATIONS = [60, 90, 120, 150, 180, 210, 240, 270, 300];

export function AdminBookingDetailPage() {
  const navigate = useNavigate();
  const { bookingId = '' } = useParams();
  const [searchParams] = useSearchParams();
  const tenantSlug = getTenantSlugFromSearchParams(searchParams);
  const [session, setSession] = useState<AdminSession | null>(null);
  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [courts, setCourts] = useState<CourtSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);
  const [savingSeries, setSavingSeries] = useState(false);
  const [editingSeries, setEditingSeries] = useState(false);
  const [savingSeriesEdit, setSavingSeriesEdit] = useState(false);
  const [editForm, setEditForm] = useState<AdminBookingUpdatePayload>({
    booking_date: '',
    court_id: null,
    start_time: '18:00',
    slot_id: null,
    duration_minutes: 90,
    note: '',
  });
  const [seriesForm, setSeriesForm] = useState<RecurringSeriesPayload>({
    label: '',
    court_id: null,
    weekday: 0,
    start_date: '',
    end_date: '',
    start_time: '18:00',
    slot_id: null,
    duration_minutes: 90,
  });
  const editableBooking = booking ? canEditBooking(booking) : false;

  useEffect(() => {
    void bootstrap();
  }, [bookingId, tenantSlug]);

  async function bootstrap() {
    setLoading(true);
    setError('');
    try {
      const sessionResponse = await getAdminSession(tenantSlug);
      setSession(sessionResponse);
      const [detail, courtsResponse] = await Promise.all([
        getAdminBooking(bookingId),
        loadCourtsSafely(),
      ]);
      setBooking(detail);
      setCourts(courtsResponse.items);
      setEditForm(buildEditForm(detail, sessionResponse.timezone));
      setSeriesForm(buildRecurringSeriesForm(detail, sessionResponse.timezone));
      setEditing(false);
      setEditingSeries(false);
    } catch (requestError: any) {
      if (requestError?.response?.status === 401) {
        navigate(withTenantPath('/admin/login', tenantSlug));
        return;
      }
      setError(requestError?.response?.data?.detail || 'Non riesco a caricare il dettaglio prenotazione.');
    } finally {
      setLoading(false);
    }
  }

  async function loadCourtsSafely() {
    try {
      return await listAdminCourts();
    } catch {
      return { items: [] };
    }
  }

  async function updateStatus(status: 'CONFIRMED' | 'COMPLETED' | 'NO_SHOW' | 'CANCELLED') {
    if (!booking) return;
    setFeedback('');
    setError('');
    try {
      const updated = await updateAdminBookingStatus(booking.id, { status });
      setBooking(updated);
      setEditForm(buildEditForm(updated, session?.timezone));
      setSeriesForm(buildRecurringSeriesForm(updated, session?.timezone));
      setEditing(false);
      setEditingSeries(false);
      setError('');
      setFeedback(`Stato aggiornato a ${status}.`);
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Aggiornamento stato non riuscito.');
    }
  }

  async function markBalance() {
    if (!booking) return;
    setFeedback('');
    setError('');
    try {
      const updated = await markAdminBalancePaid(booking.id);
      setBooking(updated);
      setEditForm(buildEditForm(updated, session?.timezone));
      setSeriesForm(buildRecurringSeriesForm(updated, session?.timezone));
      setError('');
      setFeedback('Saldo segnato come pagato al campo.');
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Marcatura saldo non riuscita.');
    }
  }

  async function saveEdit() {
    if (!booking) return;
    if (!editForm.slot_id || !editForm.start_time) {
      setError('Seleziona un orario disponibile prima di salvare la modifica.');
      return;
    }
    setSavingEdit(true);
    setFeedback('');
    setError('');
    try {
      const updated = await updateAdminBooking(booking.id, editForm);
      setBooking(updated);
      setEditForm(buildEditForm(updated, session?.timezone));
      setSeriesForm(buildRecurringSeriesForm(updated, session?.timezone));
      setEditing(false);
      setFeedback('Prenotazione aggiornata con successo.');
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Salvataggio modifica non riuscito.');
    } finally {
      setSavingEdit(false);
    }
  }

  async function cancelSeries() {
    if (!booking?.recurring_series_id) {
      return;
    }

    const label = booking.recurring_series_label || booking.public_reference;
    if (!window.confirm(`Confermi l'annullamento di tutte le occorrenze future della serie "${label}"?`)) {
      return;
    }

    setSavingSeries(true);
    setFeedback('');
    setError('');

    try {
      const response = await cancelRecurringSeries(booking.recurring_series_id);
      const detail = await getAdminBooking(booking.id);
      setBooking(detail);
      setEditForm(buildEditForm(detail, session?.timezone));
      setSeriesForm(buildRecurringSeriesForm(detail, session?.timezone));
      setEditingSeries(false);
      setFeedback(`Serie aggiornata: ${response.cancelled_count} occorrenze future annullate, ${response.skipped_count} saltate.`);
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Aggiornamento serie ricorrente non riuscito.');
    } finally {
      setSavingSeries(false);
    }
  }

  async function saveSeriesEdit() {
    if (!booking?.recurring_series_id) {
      return;
    }

    if (!seriesForm.slot_id || !seriesForm.start_time) {
      setError('Seleziona un orario disponibile prima di salvare la serie ricorrente.');
      return;
    }

    if (seriesForm.end_date < seriesForm.start_date) {
      setError('La data fine serie deve essere uguale o successiva alla data di partenza.');
      return;
    }

    setSavingSeriesEdit(true);
    setFeedback('');
    setError('');

    try {
      const response = await updateRecurringSeries(booking.recurring_series_id, seriesForm);
      const detail = await getAdminBooking(booking.id);
      setBooking(detail);
      setEditForm(buildEditForm(detail, session?.timezone));
      setSeriesForm(buildRecurringSeriesForm(detail, session?.timezone));
      setEditingSeries(false);
      setFeedback(`Serie aggiornata. Nuove occorrenze create: ${response.created_count}. Saltate: ${response.skipped_count}.`);
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Modifica serie ricorrente non riuscita.');
    } finally {
      setSavingSeriesEdit(false);
    }
  }

  const isRecurring = booking ? booking.source === 'ADMIN_RECURRING' || booking.deposit_amount === 0 : false;

  return (
    <div className='min-h-screen px-4 py-6 sm:px-6 lg:px-8'>
      <div className='page-shell space-y-6'>
        <div className='flex items-center justify-between gap-3'>
          <Link to={withTenantPath('/admin/prenotazioni', tenantSlug)} className='btn-secondary'>
            <ArrowLeft size={16} /> Torna alle prenotazioni
          </Link>
        </div>

        {feedback ? <AlertBanner tone='success'>{feedback}</AlertBanner> : null}
        {error ? <AlertBanner tone='error'>{error}</AlertBanner> : null}

        {loading ? (
          <LoadingBlock label='Sto caricando il dettaglio della prenotazione…' />
        ) : !booking ? (
          <EmptyState icon={CalendarDays} title='Prenotazione non trovata' description='Il dettaglio richiesto non è disponibile o non è più accessibile.' />
        ) : (
          <div className='grid gap-6 xl:grid-cols-[1fr_320px]'>
            <SectionCard
              title='Dettaglio prenotazione'
              description={isRecurring ? 'Controlla dati cliente, stato e dettagli della serie ricorrente.' : 'Controlla dati cliente, stato e riferimenti pagamento.'}
              actions={<StatusBadge status={booking.status} />}
              elevated
            >
              <div className='grid gap-4 sm:grid-cols-2'>
                <InfoItem label='Riferimento' value={booking.public_reference} />
                <InfoItem label='Durata' value={`${booking.duration_minutes} minuti`} />
                <InfoItem label='Campo' value={booking.court_name || 'Campo non disponibile'} />
                <InfoItem label='Inizio' value={formatDateTime(booking.start_at, session?.timezone)} />
                <InfoItem label='Fine' value={formatDateTime(booking.end_at, session?.timezone)} />
                {booking.recurring_series_label ? <InfoItem label='Serie ricorrente' value={booking.recurring_series_label} /> : null}
                {!isRecurring ? <InfoItem label='Caparra' value={formatCurrency(booking.deposit_amount)} /> : null}
                {!isRecurring ? <InfoItem label='Pagamento' value={`${booking.payment_provider} • ${booking.payment_status}`} /> : null}
                <InfoItem label='Cliente' value={booking.customer_name || 'Cliente non disponibile'} />
                <InfoItem label='Creata da' value={booking.created_by} />
              </div>
              <div className='mt-5 grid gap-3 sm:grid-cols-2'>
                <ContactItem icon={Mail} label='Email' value={booking.customer_email || '—'} />
                <ContactItem icon={Phone} label='Telefono' value={booking.customer_phone || '—'} />
              </div>
              <div className='mt-5 rounded-[24px] border border-slate-200 bg-slate-50 p-4'>
                <p className='text-sm font-semibold text-slate-900'>Note e riferimenti</p>
                <p className='mt-2 text-sm text-slate-600'>{booking.note || 'Nessuna nota inserita.'}</p>
                {!isRecurring ? <p className='mt-3 text-xs text-slate-500'>Riferimento pagamento: {booking.payment_reference || 'non ancora disponibile'}</p> : null}
                {isRecurring ? <p className='mt-3 text-xs text-slate-500'>Le prenotazioni ricorrenti non richiedono caparra online o saldo al campo.</p> : null}
              </div>
            </SectionCard>

            <div className='space-y-6'>
              <SectionCard title='Modifica slot' description='Aggiorna data, orario, durata e nota senza ricreare la prenotazione.'>
                {editing ? (
                  <div className='space-y-4'>
                    {courts.length > 0 ? (
                      <div>
                        <label className='field-label' htmlFor='admin-edit-court'>Campo</label>
                        <select
                          id='admin-edit-court'
                          className='text-input'
                          value={editForm.court_id || ''}
                          onChange={(event) => setEditForm((prev) => ({ ...prev, court_id: event.target.value || null, start_time: '', slot_id: null }))}
                        >
                          {courts.map((court) => (
                            <option key={court.id} value={court.id}>{court.name}</option>
                          ))}
                        </select>
                      </div>
                    ) : null}
                    <div className='grid gap-4 sm:grid-cols-[1fr_220px]'>
                      <DateFieldWithDay
                        id='admin-edit-date'
                        label='Data'
                        value={editForm.booking_date}
                        onChange={(value) => setEditForm((prev) => ({ ...prev, booking_date: value, start_time: '', slot_id: null }))}
                      />
                      <div>
                        <label className='field-label' htmlFor='admin-edit-duration'>Durata</label>
                        <select
                          id='admin-edit-duration'
                          className='text-input'
                          value={editForm.duration_minutes}
                          onChange={(event) => setEditForm((prev) => ({ ...prev, duration_minutes: Number(event.target.value), start_time: '', slot_id: null }))}
                        >
                          {DURATIONS.map((minutes) => (
                            <option key={minutes} value={minutes}>{minutes} minuti</option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <div>
                      <p className='field-label'>Orario</p>
                      <AdminTimeSlotPicker
                        bookingDate={editForm.booking_date}
                        courtId={editForm.court_id}
                        durationMinutes={editForm.duration_minutes}
                        selectedSlotId={editForm.slot_id || ''}
                        tenantSlug={tenantSlug}
                        includeSelectedUnavailable
                        onSelect={(slot) => setEditForm((prev) => ({ ...prev, start_time: slot.start_time, slot_id: slot.slot_id }))}
                      />
                    </div>
                    <div className='grid gap-3 sm:grid-cols-2'>
                      <div>
                        <label className='field-label' htmlFor='admin-edit-note'>Nota</label>
                        <textarea
                          id='admin-edit-note'
                          className='text-input min-h-24'
                          value={editForm.note}
                          onChange={(event) => setEditForm((prev) => ({ ...prev, note: event.target.value }))}
                        />
                      </div>
                    </div>
                    <div className='flex flex-wrap gap-3'>
                      <button className='btn-primary' type='button' disabled={savingEdit} onClick={() => void saveEdit()}>
                        {savingEdit ? 'Salvataggio in corso…' : 'Salva modifica'}
                      </button>
                      <button className='btn-secondary' type='button' disabled={savingEdit} onClick={() => {
                        setEditing(false);
                        setEditForm(buildEditForm(booking, session?.timezone));
                      }}>
                        Annulla
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className='space-y-3'>
                    <div className='rounded-[24px] border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600'>
                      <p><strong className='text-slate-900'>Slot attuale:</strong> {formatDateTime(booking.start_at, session?.timezone)} → {formatDateTime(booking.end_at, session?.timezone)}</p>
                      <p className='mt-2'><strong className='text-slate-900'>Nota attuale:</strong> {booking.note || 'Nessuna nota inserita.'}</p>
                      {isRecurring ? <p className='mt-2 text-xs text-slate-500'>Questa modifica aggiorna solo l&apos;occorrenza selezionata. Per modificare o annullare l&apos;intera serie usa la sezione dedicata qui sotto.</p> : null}
                    </div>
                    <button className='btn-secondary w-full disabled:cursor-not-allowed disabled:opacity-50' type='button' disabled={!editableBooking} onClick={() => setEditing(true)}>
                      Modifica data e orario
                    </button>
                    {booking.status !== 'CONFIRMED' ? <p className='text-xs text-slate-500'>La modifica e disponibile solo per prenotazioni confermate.</p> : null}
                    {booking.status === 'CONFIRMED' && !editableBooking ? <p className='text-xs text-slate-500'>La modifica e disponibile solo per prenotazioni future.</p> : null}
                  </div>
                )}
              </SectionCard>

              {isRecurring && booking.recurring_series_id ? (
                <SectionCard title='Modifica intera serie' description='Sostituisce le occorrenze future con una nuova pianificazione ricorrente.'>
                  {editingSeries ? (
                    <div className='space-y-4'>
                      {courts.length > 0 ? (
                        <div>
                          <label className='field-label' htmlFor='admin-series-court'>Campo</label>
                          <select
                            id='admin-series-court'
                            className='text-input'
                            value={seriesForm.court_id || ''}
                            onChange={(event) => setSeriesForm((prev) => ({ ...prev, court_id: event.target.value || null, start_time: '', slot_id: null }))}
                          >
                            {courts.map((court) => (
                              <option key={court.id} value={court.id}>{court.name}</option>
                            ))}
                          </select>
                        </div>
                      ) : null}
                      <div>
                        <label className='field-label' htmlFor='admin-series-label'>Nome serie ricorrente</label>
                        <input
                          id='admin-series-label'
                          className='text-input'
                          value={seriesForm.label}
                          onChange={(event) => setSeriesForm((prev) => ({ ...prev, label: event.target.value }))}
                        />
                      </div>
                      <div className='grid gap-4 sm:grid-cols-2'>
                        <DateFieldWithDay
                          id='admin-series-start-date'
                          label='Data di partenza'
                          value={seriesForm.start_date}
                          onChange={(value) => setSeriesForm((prev) => ({
                            ...prev,
                            start_date: value,
                            end_date: prev.end_date < value ? value : prev.end_date,
                            weekday: getRecurringWeekday(value),
                            start_time: '',
                            slot_id: null,
                          }))}
                        />
                        <DateFieldWithDay
                          id='admin-series-end-date'
                          label='Fino al'
                          value={seriesForm.end_date}
                          min={seriesForm.start_date}
                          onChange={(value) => setSeriesForm((prev) => ({ ...prev, end_date: value }))}
                        />
                      </div>
                      <div className='grid gap-3 sm:grid-cols-2'>
                        <div>
                          <label className='field-label' htmlFor='admin-series-duration'>Durata</label>
                          <select
                            id='admin-series-duration'
                            className='text-input'
                            value={seriesForm.duration_minutes}
                            onChange={(event) => setSeriesForm((prev) => ({ ...prev, duration_minutes: Number(event.target.value), start_time: '', slot_id: null }))}
                          >
                            {DURATIONS.map((minutes) => (
                              <option key={minutes} value={minutes}>{minutes} minuti</option>
                            ))}
                          </select>
                        </div>
                        <div className='surface-muted self-end'>
                          <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>Giorno serie</p>
                          <p className='mt-2 text-base font-medium text-slate-900'>{formatWeekdayLabel(seriesForm.start_date)}</p>
                        </div>
                      </div>
                      <div>
                        <p className='field-label'>Orario della serie</p>
                        <AdminTimeSlotPicker
                          bookingDate={seriesForm.start_date}
                          courtId={seriesForm.court_id}
                          durationMinutes={seriesForm.duration_minutes}
                          selectedSlotId={seriesForm.slot_id || ''}
                          tenantSlug={tenantSlug}
                          includeSelectedUnavailable
                          onSelect={(slot) => setSeriesForm((prev) => ({ ...prev, start_time: slot.start_time, slot_id: slot.slot_id }))}
                        />
                      </div>
                      <div className='flex flex-wrap gap-3'>
                        <button className='btn-primary' type='button' disabled={savingSeriesEdit} onClick={() => void saveSeriesEdit()}>
                          {savingSeriesEdit ? 'Salvataggio serie in corso…' : 'Salva serie'}
                        </button>
                        <button className='btn-secondary' type='button' disabled={savingSeriesEdit} onClick={() => {
                          setEditingSeries(false);
                          setSeriesForm(buildRecurringSeriesForm(booking, session?.timezone));
                        }}>
                          Annulla
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className='space-y-3'>
                      <div className='rounded-[24px] border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600'>
                        <p><strong className='text-slate-900'>Serie:</strong> {booking.recurring_series_label || 'Serie ricorrente'}</p>
                        <p className='mt-2'><strong className='text-slate-900'>Partenza nuova pianificazione:</strong> {seriesForm.start_date}</p>
                        <p className='mt-2'><strong className='text-slate-900'>Fino al:</strong> {booking.recurring_series_end_date || seriesForm.end_date}</p>
                        <p className='mt-2 text-xs text-slate-500'>L&apos;aggiornamento sostituisce le occorrenze future della serie. Le partite gia giocate restano nello storico.</p>
                      </div>
                      <button className='btn-secondary w-full disabled:cursor-not-allowed disabled:opacity-50' type='button' disabled={!editableBooking} onClick={() => setEditingSeries(true)}>
                        Modifica intera serie
                      </button>
                      {booking.status !== 'CONFIRMED' ? <p className='text-xs text-slate-500'>La modifica serie e disponibile solo da una prenotazione confermata.</p> : null}
                      {booking.status === 'CONFIRMED' && !editableBooking ? <p className='text-xs text-slate-500'>La modifica serie e disponibile solo per prenotazioni future.</p> : null}
                    </div>
                  )}
                </SectionCard>
              ) : null}

              <SectionCard title='Azioni rapide' description='Aggiorna lo stato operativo direttamente da qui.'>
                <div className='space-y-3'>
                  {!isRecurring ? (
                    <button className='btn-primary w-full disabled:cursor-not-allowed disabled:opacity-50' type='button' disabled={!canMarkBalancePaid(booking.status, booking.balance_paid_at, booking.start_at)} onClick={() => void markBalance()}>
                      <WalletCards size={16} /> Segna saldo al campo
                    </button>
                  ) : null}
                  <button className='btn-soft-success w-full' type='button' disabled={!canMarkBookingCompleted(booking.status, booking.end_at)} onClick={() => void updateStatus('COMPLETED')}>Segna completed</button>
                  <button className='btn-soft-warning w-full' type='button' disabled={!canMarkBookingNoShow(booking.status, booking.start_at)} onClick={() => void updateStatus('NO_SHOW')}>Segna no-show</button>
                  <button className='btn-soft-danger w-full' type='button' disabled={!canCancelBooking(booking.status)} onClick={() => void updateStatus('CANCELLED')}>Annulla prenotazione</button>
                  {isRecurring && booking.recurring_series_id ? (
                    <button className='btn-soft-danger w-full' type='button' disabled={savingSeries} onClick={() => void cancelSeries()}>
                      {savingSeries ? 'Aggiornamento serie in corso…' : 'Annulla intera serie'}
                    </button>
                  ) : null}
                  {canRestoreBookingConfirmed(booking.status) ? (
                    <button className='btn-secondary w-full' type='button' onClick={() => void updateStatus('CONFIRMED')}>Ripristina confermata</button>
                  ) : null}
                </div>
              </SectionCard>

              <SectionCard title='Audit rapido' description='Timestamp principali della prenotazione.'>
                <div className='space-y-3 text-sm text-slate-600'>
                  <p>Creata: <strong>{formatDateTime(booking.created_at, session?.timezone)}</strong></p>
                  {!isRecurring ? <p>Saldo al campo: <strong>{booking.balance_paid_at ? formatDateTime(booking.balance_paid_at, session?.timezone) : 'non segnato'}</strong></p> : null}
                  <p>Completed: <strong>{booking.completed_at ? formatDateTime(booking.completed_at, session?.timezone) : 'non segnato'}</strong></p>
                  <p>No-show: <strong>{booking.no_show_at ? formatDateTime(booking.no_show_at, session?.timezone) : 'non segnato'}</strong></p>
                  <p>Annullata: <strong>{booking.cancelled_at ? formatDateTime(booking.cancelled_at, session?.timezone) : 'non annullata'}</strong></p>
                </div>
              </SectionCard>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function buildEditForm(booking: Pick<BookingDetail, 'booking_date_local' | 'court_id' | 'start_at' | 'duration_minutes' | 'note'>, timezone?: string | null): AdminBookingUpdatePayload {
  return {
    booking_date: booking.booking_date_local,
    court_id: booking.court_id || null,
    start_time: formatTimeValue(booking.start_at, timezone),
    slot_id: booking.start_at,
    duration_minutes: booking.duration_minutes,
    note: booking.note || '',
  };
}

function buildRecurringSeriesForm(
  booking: Pick<BookingDetail, 'booking_date_local' | 'court_id' | 'start_at' | 'duration_minutes' | 'recurring_series_label' | 'recurring_series_end_date' | 'recurring_series_weekday'>,
  timezone?: string | null,
): RecurringSeriesPayload {
  return {
    label: booking.recurring_series_label || 'Serie ricorrente',
    court_id: booking.court_id || null,
    weekday: typeof booking.recurring_series_weekday === 'number' ? booking.recurring_series_weekday : getRecurringWeekday(booking.booking_date_local),
    start_date: booking.booking_date_local,
    end_date: booking.recurring_series_end_date || booking.booking_date_local,
    start_time: formatTimeValue(booking.start_at, timezone),
    slot_id: booking.start_at,
    duration_minutes: booking.duration_minutes,
  };
}

function canEditBooking(booking: Pick<BookingDetail, 'status' | 'start_at'>) {
  return booking.status === 'CONFIRMED' && new Date(booking.start_at).getTime() > Date.now();
}

function getRecurringWeekday(dateValue: string) {
  const [year, month, day] = dateValue.split('-').map(Number);
  if (!year || !month || !day) {
    return 0;
  }

  const normalizedDate = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
  return (normalizedDate.getUTCDay() + 6) % 7;
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className='surface-muted'>
      <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>{label}</p>
      <p className='mt-2 text-sm font-medium text-slate-900'>{value}</p>
    </div>
  );
}

function ContactItem({ icon: Icon, label, value }: { icon: typeof Mail; label: string; value: string }) {
  return (
    <div className='flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3'>
      <div className='flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-600'>
        <Icon size={16} />
      </div>
      <div>
        <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>{label}</p>
        <p className='text-sm font-medium text-slate-900'>{value}</p>
      </div>
    </div>
  );
}