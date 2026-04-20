import { CalendarDays, ChevronDown, ChevronUp, ClipboardList } from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AdminBookingCard } from '../components/AdminBookingCard';
import { AdminNav } from '../components/AdminNav';
import { AlertBanner } from '../components/AlertBanner';
import { EmptyState } from '../components/EmptyState';
import { LoadingBlock } from '../components/LoadingBlock';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/StatusBadge';
import {
  cancelRecurringOccurrences,
  cancelRecurringSeries,
  getAdminSession,
  listAdminBookings,
  markAdminBalancePaid,
  updateAdminBookingStatus,
} from '../services/adminApi';
import type { AdminDashboardFilters, BookingSummary } from '../types';
import { canCancelBooking } from '../utils/adminBookingActions';
import { formatDateTime, toDateInputValue } from '../utils/format';

const today = toDateInputValue(new Date());

function getRequestStatus(error: any) {
  return error?.response?.status;
}

function getRequestMessage(error: any, fallback: string) {
  return error?.response?.data?.detail || fallback;
}

export function AdminBookingsPage() {
  const navigate = useNavigate();
  const [bookings, setBookings] = useState<BookingSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ tone: 'error' | 'success'; message: string } | null>(null);
  const [filters, setFilters] = useState<AdminDashboardFilters>({
    start_date: today,
    end_date: '',
    status: '',
    payment_provider: '',
    query: '',
  });
  const [expandedSeries, setExpandedSeries] = useState<Record<string, boolean>>({});
  const [selectedOccurrences, setSelectedOccurrences] = useState<Record<string, string[]>>({});

  useEffect(() => {
    void bootstrap();
  }, []);

  async function bootstrap() {
    setLoading(true);
    setFeedback(null);

    try {
      await getAdminSession();
      await loadBookings();
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate('/admin/login');
        return;
      }

      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Non riesco a caricare le prenotazioni admin in questo momento.') });
    } finally {
      setLoading(false);
    }
  }

  async function loadBookings(nextFilters = filters) {
    const response = await listAdminBookings(nextFilters);
    setBookings(response.items);
  }

  async function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    try {
      await loadBookings();
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate('/admin/login');
        return;
      }
      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Applicazione filtri non riuscita.') });
    }
  }

  async function refreshBookings(message = 'Aggiornamento prenotazioni non riuscito.') {
    setFeedback(null);
    try {
      await loadBookings(filters);
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate('/admin/login');
        return;
      }
      setFeedback({ tone: 'error', message: getRequestMessage(error, message) });
    }
  }

  async function markBookingState(bookingId: string, status: 'CONFIRMED' | 'COMPLETED' | 'NO_SHOW' | 'CANCELLED') {
    setFeedback(null);
    try {
      await updateAdminBookingStatus(bookingId, { status });
      setFeedback({ tone: 'success', message: 'Stato prenotazione aggiornato.' });
      await loadBookings();
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
      setFeedback({ tone: 'success', message: 'Saldo segnato come pagato al campo.' });
      await loadBookings();
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate('/admin/login');
        return;
      }
      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Marcatura saldo non riuscita.') });
    }
  }

  async function handleCancelOccurrences(seriesId: string, bookingIds: string[], scopeLabel: string) {
    if (bookingIds.length === 0) {
      return;
    }

    if (!window.confirm(`Confermi l'annullamento ${scopeLabel}?`)) {
      return;
    }

    setFeedback(null);

    try {
      const response = await cancelRecurringOccurrences(bookingIds);
      setSelectedOccurrences((prev) => ({ ...prev, [seriesId]: [] }));
      setFeedback({
        tone: 'success',
        message: `Occorrenze aggiornate: ${response.cancelled_count} annullate, ${response.skipped_count} saltate.`,
      });
      await loadBookings();
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate('/admin/login');
        return;
      }
      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Aggiornamento occorrenze ricorrenti non riuscito.') });
    }
  }

  async function handleCancelSeries(seriesId: string, seriesLabel: string) {
    if (!window.confirm(`Confermi l'annullamento di tutte le occorrenze future della serie "${seriesLabel}"?`)) {
      return;
    }

    setFeedback(null);

    try {
      const response = await cancelRecurringSeries(seriesId);
      setSelectedOccurrences((prev) => ({ ...prev, [seriesId]: [] }));
      setFeedback({
        tone: 'success',
        message: `Serie aggiornata: ${response.cancelled_count} occorrenze future annullate, ${response.skipped_count} saltate.`,
      });
      await loadBookings();
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate('/admin/login');
        return;
      }
      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Aggiornamento serie ricorrente non riuscito.') });
    }
  }

  const entries = useMemo(() => buildBookingEntries(bookings), [bookings]);

  return (
    <div className='min-h-screen px-4 py-6 sm:px-6 lg:px-8'>
      <div className='page-shell space-y-6'>
        <div className='space-y-4 rounded-[28px] border border-cyan-400/20 bg-slate-950/80 p-5 text-white shadow-soft'>
          <div className='flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between'>
            <div>
              <p className='text-2xl font-semibold text-cyan-100'>Elenco prenotazioni</p>
              <h1 className='text-3xl font-bold'>Ricerca avanzata e gestione ricorrenze</h1>
              <p className='mt-2 max-w-2xl text-sm text-slate-300'>Usa l’elenco per filtri avanzati, ricerca libera e azioni sulle occorrenze. Per la vista rapida della settimana usa Prenotazioni Attuali.</p>
            </div>
            <div className='flex flex-wrap gap-3'>
              <Link to='/admin/prenotazioni-attuali' className='btn-secondary'>Prenotazioni Attuali</Link>
              <button className='btn-secondary' onClick={() => void refreshBookings()}>Aggiorna</button>
            </div>
          </div>
          <AdminNav />
        </div>

        {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

        <SectionCard title='Filtri' description='Definisci il periodo e restringi il risultato per stato, pagamento o ricerca libera.' elevated>
          <form className='grid gap-3 lg:grid-cols-6' onSubmit={applyFilters}>
            <div>
              <label className='field-label' htmlFor='booking-start-date'>Data inizio</label>
              <input
                id='booking-start-date'
                className='text-input'
                type='date'
                value={filters.start_date || ''}
                onChange={(event) => setFilters((prev) => ({ ...prev, start_date: event.target.value }))}
              />
            </div>
            <div>
              <label className='field-label' htmlFor='booking-end-date'>Data fine</label>
              <input
                id='booking-end-date'
                className='text-input'
                type='date'
                value={filters.end_date || ''}
                onChange={(event) => setFilters((prev) => ({ ...prev, end_date: event.target.value }))}
              />
            </div>
            <div>
              <label className='field-label' htmlFor='booking-status'>Stato</label>
              <select
                id='booking-status'
                className='text-input'
                value={filters.status}
                onChange={(event) => setFilters((prev) => ({ ...prev, status: event.target.value }))}
              >
                <option value=''>Tutti gli stati</option>
                <option value='PENDING_PAYMENT'>PENDING_PAYMENT</option>
                <option value='CONFIRMED'>CONFIRMED</option>
                <option value='CANCELLED'>CANCELLED</option>
                <option value='COMPLETED'>COMPLETED</option>
                <option value='NO_SHOW'>NO_SHOW</option>
                <option value='EXPIRED'>EXPIRED</option>
              </select>
            </div>
            <div>
              <label className='field-label' htmlFor='booking-payment-provider'>Pagamento</label>
              <select
                id='booking-payment-provider'
                className='text-input'
                value={filters.payment_provider}
                onChange={(event) => setFilters((prev) => ({ ...prev, payment_provider: event.target.value }))}
              >
                <option value=''>Tutti i pagamenti</option>
                <option value='STRIPE'>STRIPE</option>
                <option value='PAYPAL'>PAYPAL</option>
                <option value='NONE'>NONE</option>
              </select>
            </div>
            <div className='lg:col-span-2'>
              <label className='field-label' htmlFor='booking-query'>Cliente o serie</label>
              <input
                id='booking-query'
                className='text-input'
                placeholder='Nome cliente, riferimento o label serie'
                value={filters.query || ''}
                onChange={(event) => setFilters((prev) => ({ ...prev, query: event.target.value }))}
              />
            </div>
            <div className='flex flex-wrap gap-3 lg:col-span-6'>
              <button className='btn-primary' type='submit'>Applica filtri</button>
              <button
                className='btn-secondary'
                type='button'
                onClick={() => {
                  const resetFilters = { start_date: today, end_date: '', status: '', payment_provider: '', query: '' };
                  setFilters(resetFilters);
                  void loadBookings(resetFilters);
                }}
              >
                Ripristina filtri
              </button>
            </div>
          </form>
        </SectionCard>

        {loading ? <LoadingBlock label='Sto caricando l’elenco prenotazioni…' /> : null}

        {!loading ? (
          entries.length === 0 ? (
            <EmptyState icon={ClipboardList} title='Nessuna prenotazione per questi filtri' description='Allarga il periodo o modifica la ricerca per vedere gli slot occupati.' />
          ) : (
            <div className='space-y-4'>
              {entries.map((entry) => entry.kind === 'single' ? (
                <AdminBookingCard
                  key={entry.booking.id}
                  booking={entry.booking}
                  onMarkBalancePaid={markBalancePaid}
                  onUpdateStatus={markBookingState}
                />
              ) : (
                <SectionCard
                  key={entry.seriesId}
                  title={entry.label}
                  description={`${entry.items.length} occorrenze • ${entry.items[0].booking_date_local} → ${entry.items[entry.items.length - 1].booking_date_local}`}
                  actions={
                    <div className='flex flex-wrap gap-2'>
                      <button
                        className='btn-secondary'
                        type='button'
                        onClick={() => setExpandedSeries((prev) => ({ ...prev, [entry.seriesId]: !prev[entry.seriesId] }))}
                      >
                        {expandedSeries[entry.seriesId] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        {expandedSeries[entry.seriesId] ? 'Comprimi' : 'Espandi'}
                      </button>
                      <button
                        className='btn-secondary'
                        type='button'
                        disabled={(selectedOccurrences[entry.seriesId] || []).length === 0}
                        onClick={() => void handleCancelOccurrences(
                          entry.seriesId,
                          selectedOccurrences[entry.seriesId] || [],
                          'delle occorrenze selezionate'
                        )}
                      >
                        Annulla selezionate
                      </button>
                      <button className='btn-secondary' type='button' onClick={() => void handleCancelSeries(entry.seriesId, entry.label)}>
                        Annulla tutta la serie
                      </button>
                    </div>
                  }
                  elevated
                >
                  {expandedSeries[entry.seriesId] ? (
                    <div className='space-y-3'>
                      {entry.items.map((booking) => {
                        const isSelectable = canCancelBooking(booking.status);
                        const isChecked = (selectedOccurrences[entry.seriesId] || []).includes(booking.id);

                        return (
                          <div key={booking.id} className='rounded-[24px] border border-slate-200 bg-white px-4 py-4 shadow-sm'>
                            <div className='flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between'>
                              <div className='flex items-start gap-3'>
                                <input
                                  type='checkbox'
                                  className='mt-1 h-4 w-4 rounded border-slate-300'
                                  checked={isChecked}
                                  disabled={!isSelectable}
                                  onChange={(event) => {
                                    setSelectedOccurrences((prev) => {
                                      const current = prev[entry.seriesId] || [];
                                      if (event.target.checked) {
                                        return { ...prev, [entry.seriesId]: [...current, booking.id] };
                                      }

                                      return { ...prev, [entry.seriesId]: current.filter((value) => value !== booking.id) };
                                    });
                                  }}
                                />
                                <div className='space-y-2'>
                                  <div className='flex flex-wrap items-center gap-2'>
                                    <p className='font-semibold text-slate-950'>{booking.customer_name || 'Occorrenza ricorrente'}</p>
                                    <StatusBadge status={booking.status} />
                                  </div>
                                  <div className='flex flex-wrap gap-3 text-sm text-slate-600'>
                                    <span className='inline-flex items-center gap-1'><CalendarDays size={14} /> {formatDateTime(booking.start_at)}</span>
                                    <span>{booking.duration_minutes} min</span>
                                  </div>
                                  <p className='text-sm text-slate-600'>{booking.note || 'Serie ricorrente senza note aggiuntive.'}</p>
                                </div>
                              </div>
                              <div className='flex flex-wrap gap-2'>
                                <Link to={`/admin/bookings/${booking.id}`} className='btn-ghost'>Dettaglio</Link>
                                {isSelectable ? (
                                  <button
                                    className='btn-secondary'
                                    type='button'
                                    onClick={() => void handleCancelOccurrences(entry.seriesId, [booking.id], 'della singola occorrenza')}
                                  >
                                    Annulla singola
                                  </button>
                                ) : null}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : null}
                </SectionCard>
              ))}
            </div>
          )
        ) : null}
      </div>
    </div>
  );
}

function buildBookingEntries(bookings: BookingSummary[]) {
  const recurringSeriesMap = new Map<string, { kind: 'series'; seriesId: string; label: string; items: BookingSummary[]; sortKey: number }>();
  const entries: Array<
    { kind: 'single'; booking: BookingSummary; sortKey: number } |
    { kind: 'series'; seriesId: string; label: string; items: BookingSummary[]; sortKey: number }
  > = [];

  const sortedBookings = [...bookings].sort((left, right) => new Date(left.start_at).getTime() - new Date(right.start_at).getTime());

  for (const booking of sortedBookings) {
    if (booking.source === 'ADMIN_RECURRING' && booking.recurring_series_id) {
      const existingGroup = recurringSeriesMap.get(booking.recurring_series_id);

      if (existingGroup) {
        existingGroup.items.push(booking);
        continue;
      }

      recurringSeriesMap.set(booking.recurring_series_id, {
        kind: 'series',
        seriesId: booking.recurring_series_id,
        label: booking.recurring_series_label || 'Serie ricorrente',
        items: [booking],
        sortKey: new Date(booking.start_at).getTime(),
      });
      continue;
    }

    entries.push({ kind: 'single', booking, sortKey: new Date(booking.start_at).getTime() });
  }

  entries.push(...Array.from(recurringSeriesMap.values()));
  return entries.sort((left, right) => left.sortKey - right.sortKey);
}