import { FormEvent, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type { BookingSummary, ReportResponse } from '../types';

const today = new Date().toISOString().slice(0, 10);

export function AdminDashboardPage() {
  const navigate = useNavigate();
  const [bookings, setBookings] = useState<BookingSummary[]>([]);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [events, setEvents] = useState<Array<{ id: string; event_type: string; actor: string; message: string; created_at: string }>>([]);
  const [feedback, setFeedback] = useState('');
  const [filters, setFilters] = useState({ booking_date: '', status: '', customer: '' });
  const [manualForm, setManualForm] = useState({
    first_name: 'Mario',
    last_name: 'Rossi',
    phone: '3331234567',
    email: 'mario@example.com',
    note: '',
    booking_date: today,
    start_time: '18:00',
    duration_minutes: 90,
    payment_provider: 'NONE',
  });
  const [blackoutForm, setBlackoutForm] = useState({
    title: 'Manutenzione ordinaria',
    reason: 'Pulizia e controllo rete',
    start_at: `${today}T12:00`,
    end_at: `${today}T13:30`,
  });
  const [recurringForm, setRecurringForm] = useState({ label: 'Allenamento fisso', weekday: 2, start_date: today, weeks_count: 6, start_time: '20:00', duration_minutes: 90 });
  const [recurringPreview, setRecurringPreview] = useState<Array<{ booking_date: string; start_time: string; end_time: string; available: boolean; reason?: string | null }>>([]);

  useEffect(() => {
    void bootstrap();
  }, []);

  async function bootstrap() {
    try {
      await api.get('/admin/auth/me');
      await Promise.all([loadBookings(), loadReport(), loadEvents()]);
    } catch {
      navigate('/admin/login');
    }
  }

  async function loadBookings() {
    const response = await api.get<{ items: BookingSummary[] }>('/admin/bookings', { params: filters });
    setBookings(response.data.items);
  }

  async function loadReport() {
    const response = await api.get<ReportResponse>('/admin/reports/summary');
    setReport(response.data);
  }

  async function loadEvents() {
    const response = await api.get<Array<{ id: string; event_type: string; actor: string; message: string; created_at: string }>>('/admin/events');
    setEvents(response.data);
  }

  async function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await loadBookings();
  }

  async function createManualBooking(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback('');
    try {
      await api.post('/admin/bookings', manualForm);
      setFeedback('Prenotazione manuale creata con successo.');
      await Promise.all([loadBookings(), loadReport(), loadEvents()]);
    } catch (error: any) {
      setFeedback(error?.response?.data?.detail || 'Creazione prenotazione non riuscita.');
    }
  }

  async function createBlackout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback('');
    try {
      await api.post('/admin/blackouts', blackoutForm);
      setFeedback('Blackout creato correttamente.');
      await Promise.all([loadBookings(), loadEvents()]);
    } catch (error: any) {
      setFeedback(error?.response?.data?.detail || 'Creazione blackout non riuscita.');
    }
  }

  async function previewRecurring(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const response = await api.post<{ occurrences: Array<{ booking_date: string; start_time: string; end_time: string; available: boolean; reason?: string | null }> }>('/admin/recurring/preview', recurringForm);
      setRecurringPreview(response.data.occurrences);
    } catch (error: any) {
      setFeedback(error?.response?.data?.detail || 'Preview ricorrenza non disponibile.');
    }
  }

  async function createRecurringSeries() {
    setFeedback('');
    try {
      const response = await api.post<{ created_count: number; skipped_count: number }>('/admin/recurring', recurringForm);
      setFeedback(`Serie creata. Occorrenze create: ${response.data.created_count}. Saltate: ${response.data.skipped_count}.`);
      await Promise.all([loadBookings(), loadReport(), loadEvents()]);
    } catch (error: any) {
      setFeedback(error?.response?.data?.detail || 'Creazione serie ricorrente non riuscita.');
    }
  }

  async function markBookingState(bookingId: string, status: 'COMPLETED' | 'NO_SHOW' | 'CANCELLED') {
    await api.post(`/admin/bookings/${bookingId}/status`, { status });
    await Promise.all([loadBookings(), loadReport(), loadEvents()]);
  }

  async function markBalancePaid(bookingId: string) {
    await api.post(`/admin/bookings/${bookingId}/balance-paid`);
    await Promise.all([loadBookings(), loadEvents()]);
  }

  async function logout() {
    await api.post('/admin/auth/logout');
    navigate('/admin/login');
  }

  return (
    <div className='min-h-screen px-4 py-6 sm:px-6 lg:px-8'>
      <div className='mx-auto max-w-7xl space-y-6'>
        <div className='flex flex-col gap-3 rounded-[28px] border border-cyan-400/20 bg-slate-950/80 p-5 text-white shadow-soft sm:flex-row sm:items-center sm:justify-between'>
          <div>
            <p className='text-sm font-semibold text-cyan-200'>Dashboard admin</p>
            <h1 className='text-3xl font-bold'>Controllo prenotazioni e operatività</h1>
          </div>
          <button onClick={logout} className='btn-secondary'>Esci</button>
        </div>

        {feedback && <div className='rounded-2xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm text-cyan-800'>{feedback}</div>}

        <div className='grid gap-4 md:grid-cols-4'>
          <StatCard title='Prenotazioni totali' value={String(report?.total_bookings ?? 0)} />
          <StatCard title='Confermate' value={String(report?.confirmed_bookings ?? 0)} />
          <StatCard title='In attesa' value={String(report?.pending_bookings ?? 0)} />
          <StatCard title='Caparre incassate' value={`€${report?.collected_deposits ?? 0}`} />
        </div>

        <div className='grid gap-6 xl:grid-cols-[1.2fr_0.8fr]'>
          <div className='space-y-6'>
            <div className='surface-card'>
              <div className='mb-4 flex items-center justify-between'>
                <h2 className='section-title'>Prenotazioni</h2>
                <button className='btn-secondary' onClick={() => void loadBookings()}>Aggiorna</button>
              </div>

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
                <input className='text-input' placeholder='Cliente o riferimento' value={filters.customer} onChange={(e) => setFilters((prev) => ({ ...prev, customer: e.target.value }))} />
                <button className='btn-primary' type='submit'>Filtra</button>
              </form>

              <div className='space-y-3'>
                {bookings.map((booking) => (
                  <div key={booking.id} className='rounded-2xl border border-slate-200 p-4'>
                    <div className='flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between'>
                      <div>
                        <div className='flex items-center gap-2'>
                          <p className='font-semibold text-slate-950'>{booking.public_reference}</p>
                          <StatusBadge status={booking.status} />
                        </div>
                        <p className='mt-1 text-sm text-slate-600'>{booking.customer_name || 'Cliente non associato'} • {booking.customer_phone || '—'}</p>
                        <p className='text-sm text-slate-600'>{booking.booking_date_local} • {booking.duration_minutes} min • Caparra €{booking.deposit_amount}</p>
                      </div>
                      <div className='flex flex-wrap gap-2'>
                        <button className='btn-secondary' onClick={() => void markBalancePaid(booking.id)}>Saldo al campo</button>
                        <button className='btn-secondary' onClick={() => void markBookingState(booking.id, 'COMPLETED')}>Completed</button>
                        <button className='btn-secondary' onClick={() => void markBookingState(booking.id, 'NO_SHOW')}>No-show</button>
                        <button className='btn-secondary' onClick={() => void markBookingState(booking.id, 'CANCELLED')}>Annulla</button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className='surface-card'>
              <h2 className='section-title'>Log essenziali</h2>
              <div className='mt-4 space-y-2'>
                {events.map((event) => (
                  <div key={event.id} className='rounded-2xl bg-slate-50 px-4 py-3 text-sm'>
                    <div className='flex items-center justify-between gap-3'>
                      <span className='font-semibold text-slate-800'>{event.event_type}</span>
                      <span className='text-xs text-slate-500'>{new Date(event.created_at).toLocaleString('it-IT')}</span>
                    </div>
                    <p className='mt-1 text-slate-600'>{event.message}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className='space-y-6'>
            <div className='surface-card'>
              <h2 className='section-title'>Prenotazione manuale</h2>
              <form className='mt-4 space-y-3' onSubmit={createManualBooking}>
                <input className='text-input' placeholder='Nome' value={manualForm.first_name} onChange={(e) => setManualForm((prev) => ({ ...prev, first_name: e.target.value }))} />
                <input className='text-input' placeholder='Cognome' value={manualForm.last_name} onChange={(e) => setManualForm((prev) => ({ ...prev, last_name: e.target.value }))} />
                <input className='text-input' placeholder='Telefono' value={manualForm.phone} onChange={(e) => setManualForm((prev) => ({ ...prev, phone: e.target.value }))} />
                <input className='text-input' placeholder='Email' value={manualForm.email} onChange={(e) => setManualForm((prev) => ({ ...prev, email: e.target.value }))} />
                <div className='grid grid-cols-2 gap-2'>
                  <input className='text-input' type='date' value={manualForm.booking_date} onChange={(e) => setManualForm((prev) => ({ ...prev, booking_date: e.target.value }))} />
                  <input className='text-input' type='time' value={manualForm.start_time} onChange={(e) => setManualForm((prev) => ({ ...prev, start_time: e.target.value }))} />
                </div>
                <select className='text-input' value={manualForm.duration_minutes} onChange={(e) => setManualForm((prev) => ({ ...prev, duration_minutes: Number(e.target.value) }))}>
                  {[60, 90, 120, 150, 180, 210, 240, 270, 300].map((value) => <option key={value} value={value}>{value} minuti</option>)}
                </select>
                <button className='btn-primary w-full' type='submit'>Crea prenotazione</button>
              </form>
            </div>

            <div className='surface-card'>
              <h2 className='section-title'>Blocca fascia oraria</h2>
              <form className='mt-4 space-y-3' onSubmit={createBlackout}>
                <input className='text-input' value={blackoutForm.title} onChange={(e) => setBlackoutForm((prev) => ({ ...prev, title: e.target.value }))} />
                <input className='text-input' value={blackoutForm.reason} onChange={(e) => setBlackoutForm((prev) => ({ ...prev, reason: e.target.value }))} />
                <input className='text-input' type='datetime-local' value={blackoutForm.start_at} onChange={(e) => setBlackoutForm((prev) => ({ ...prev, start_at: e.target.value }))} />
                <input className='text-input' type='datetime-local' value={blackoutForm.end_at} onChange={(e) => setBlackoutForm((prev) => ({ ...prev, end_at: e.target.value }))} />
                <button className='btn-primary w-full' type='submit'>Crea blackout</button>
              </form>
            </div>

            <div className='surface-card'>
              <h2 className='section-title'>Serie ricorrente</h2>
              <form className='mt-4 space-y-3' onSubmit={previewRecurring}>
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
                    {[60, 90, 120, 150].map((value) => <option key={value} value={value}>{value} min</option>)}
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
                      {item.booking_date} • {item.start_time} → {item.end_time} • {item.available ? 'ok' : item.reason}
                    </div>
                  ))}
                </div>
              )}
            </div>
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
