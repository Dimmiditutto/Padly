import { ArrowLeft, ArrowRight, CalendarDays, Clock3 } from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { AdminNav } from '../components/AdminNav';
import { AlertBanner } from '../components/AlertBanner';
import { EmptyState } from '../components/EmptyState';
import { LoadingBlock } from '../components/LoadingBlock';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/StatusBadge';
import { cancelRecurringSeries, getAdminSession, listAdminBookings, logoutAdmin, updateAdminBookingStatus } from '../services/adminApi';
import type { AdminDashboardFilters, AdminSession, BookingSummary } from '../types';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';
import { canCancelBooking } from '../utils/adminBookingActions';
import { formatTimeValue, toDateInputValue } from '../utils/format';

const MONTH_LABELS = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'];

function getRequestStatus(error: any) {
  return error?.response?.status;
}

function getRequestMessage(error: any, fallback: string) {
  return error?.response?.data?.detail || fallback;
}

function normalizeDate(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate(), 12, 0, 0, 0);
}

function createDate(year: number, monthIndex: number, day: number) {
  return new Date(year, monthIndex, day, 12, 0, 0, 0);
}

function addDays(value: Date, days: number) {
  const next = normalizeDate(value);
  next.setDate(next.getDate() + days);
  return next;
}

function addWeeks(value: Date, weeks: number) {
  return addDays(value, weeks * 7);
}

function getStartOfWeek(value: Date) {
  const normalized = normalizeDate(value);
  const weekday = (normalized.getDay() + 6) % 7;
  return addDays(normalized, -weekday);
}

function compareDates(left: Date, right: Date) {
  return normalizeDate(left).getTime() - normalizeDate(right).getTime();
}

function isSameDate(left: Date, right: Date) {
  return compareDates(left, right) === 0;
}

function capitalize(label: string) {
  return label.charAt(0).toUpperCase() + label.slice(1);
}

function formatWeekdayLabel(value: Date) {
  return capitalize(new Intl.DateTimeFormat('it-IT', { weekday: 'short' }).format(value).replace('.', ''));
}

function formatDayMonthLabel(value: Date) {
  return capitalize(new Intl.DateTimeFormat('it-IT', { day: '2-digit', month: 'short' }).format(value));
}

function formatRangeLabel(startDate: Date) {
  const endDate = addDays(startDate, 6);
  return `${formatDayMonthLabel(startDate)} - ${formatDayMonthLabel(endDate)}`;
}

function getMonthWeekOptions(year: number, month: number) {
  const lastDayOfMonth = createDate(year, month, 0).getDate();
  const anchors = [1, 8, 15, 22, 29];
  const options: Array<{ value: number; label: string; weekStart: Date }> = [];

  anchors.forEach((anchor) => {
    const targetDay = Math.min(anchor, lastDayOfMonth);
    const weekStart = getStartOfWeek(createDate(year, month - 1, targetDay));
    if (!options.some((option) => isSameDate(option.weekStart, weekStart))) {
      const value = options.length + 1;
      options.push({
        value,
        label: `${value}a settimana`,
        weekStart,
      });
    }
  });

  return options;
}

function getWeekPickerSelection(weekStart: Date) {
  const representativeDay = addDays(weekStart, 4);
  const year = representativeDay.getFullYear();
  const month = representativeDay.getMonth() + 1;
  const options = getMonthWeekOptions(year, month);
  const selected = options.find((option) => isSameDate(option.weekStart, weekStart)) || options[options.length - 1];

  return {
    year,
    month,
    week: selected?.value ?? 1,
  };
}

function buildBookingFilters(weekStart: Date): AdminDashboardFilters {
  return {
    start_date: toDateInputValue(weekStart),
    end_date: toDateInputValue(addDays(weekStart, 6)),
    status: '',
    payment_provider: '',
    query: '',
  };
}

export function AdminCurrentBookingsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const tenantSlug = getTenantSlugFromSearchParams(searchParams);
  const today = useMemo(() => normalizeDate(new Date()), []);
  const currentWeekStart = useMemo(() => getStartOfWeek(today), [today]);
  const minArrowWeek = useMemo(() => addWeeks(currentWeekStart, -2), [currentWeekStart]);
  const maxArrowWeek = useMemo(() => addWeeks(currentWeekStart, 4), [currentWeekStart]);
  const initialSelection = useMemo(() => getWeekPickerSelection(currentWeekStart), [currentWeekStart]);
  const [bookings, setBookings] = useState<BookingSummary[]>([]);
  const [session, setSession] = useState<AdminSession | null>(null);
  const [viewWeekStart, setViewWeekStart] = useState(currentWeekStart);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ tone: 'error' | 'success'; message: string } | null>(null);
  const [weekYear, setWeekYear] = useState(String(initialSelection.year));
  const [weekMonth, setWeekMonth] = useState(String(initialSelection.month));
  const [weekIndex, setWeekIndex] = useState(String(initialSelection.week));

  const weekOptions = useMemo(
    () => getMonthWeekOptions(Number(weekYear), Number(weekMonth)),
    [weekMonth, weekYear]
  );

  const weekDays = useMemo(
    () => Array.from({ length: 7 }, (_, index) => addDays(viewWeekStart, index)),
    [viewWeekStart]
  );

  const visibleBookings = useMemo(
    () => bookings
      .filter((booking) => booking.status !== 'CANCELLED' && booking.status !== 'EXPIRED')
      .sort((left, right) => new Date(left.start_at).getTime() - new Date(right.start_at).getTime()),
    [bookings]
  );

  const bookingsByDay = useMemo(() => {
    const grouped: Record<string, BookingSummary[]> = {};
    weekDays.forEach((day) => {
      grouped[toDateInputValue(day)] = [];
    });

    visibleBookings.forEach((booking) => {
      if (grouped[booking.booking_date_local]) {
        grouped[booking.booking_date_local].push(booking);
      }
    });

    return grouped;
  }, [visibleBookings, weekDays]);

  const canGoPrevious = compareDates(addWeeks(viewWeekStart, -1), minArrowWeek) >= 0 && compareDates(addWeeks(viewWeekStart, -1), maxArrowWeek) <= 0;
  const canGoNext = compareDates(addWeeks(viewWeekStart, 1), minArrowWeek) >= 0 && compareDates(addWeeks(viewWeekStart, 1), maxArrowWeek) <= 0;
  const todayKey = toDateInputValue(today);

  useEffect(() => {
    void bootstrap();
  }, [tenantSlug]);

  useEffect(() => {
    setWeekIndex((previous) => {
      if (weekOptions.some((option) => String(option.value) === previous)) {
        return previous;
      }
      return String(weekOptions[weekOptions.length - 1]?.value ?? 1);
    });
  }, [weekOptions]);

  async function bootstrap() {
    setLoading(true);
    setFeedback(null);

    try {
      const sessionResponse = await getAdminSession(tenantSlug);
      setSession(sessionResponse);
      await loadWeek(currentWeekStart, false);
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate(withTenantPath('/admin/login', tenantSlug));
        return;
      }

      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Non riesco a caricare le prenotazioni attuali in questo momento.') });
    } finally {
      setLoading(false);
    }
  }

  async function loadWeek(targetWeekStart: Date, showLoader = true) {
    if (showLoader) {
      setLoading(true);
    }

    try {
      const response = await listAdminBookings(buildBookingFilters(targetWeekStart));
      setBookings(response.items);
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate(withTenantPath('/admin/login', tenantSlug));
        return;
      }

      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Aggiornamento calendario settimanale non riuscito.') });
    } finally {
      if (showLoader) {
        setLoading(false);
      }
    }
  }

  function syncWeekPicker(targetWeekStart: Date) {
    const selection = getWeekPickerSelection(targetWeekStart);
    setWeekYear(String(selection.year));
    setWeekMonth(String(selection.month));
    setWeekIndex(String(selection.week));
  }

  async function goToWeek(targetWeekStart: Date) {
    const normalizedTarget = normalizeDate(targetWeekStart);
    setFeedback(null);
    setViewWeekStart(normalizedTarget);
    syncWeekPicker(normalizedTarget);
    await loadWeek(normalizedTarget);
  }

  async function handleQuickNavigation(direction: -1 | 1) {
    const targetWeek = addWeeks(viewWeekStart, direction);
    if ((direction < 0 && !canGoPrevious) || (direction > 0 && !canGoNext)) {
      return;
    }
    await goToWeek(targetWeek);
  }

  async function submitWeekJump(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const selected = weekOptions.find((option) => String(option.value) === weekIndex) || weekOptions[weekOptions.length - 1];
    if (!selected) {
      return;
    }
    await goToWeek(selected.weekStart);
  }

  async function handleCancelBooking(booking: BookingSummary) {
    if (!canCancelBooking(booking.status)) {
      return;
    }

    if (!window.confirm(`Confermi l'annullamento della prenotazione ${booking.public_reference}?`)) {
      return;
    }

    setFeedback(null);

    try {
      await updateAdminBookingStatus(booking.id, { status: 'CANCELLED' });
      setFeedback({ tone: 'success', message: 'Prenotazione annullata con successo.' });
      await loadWeek(viewWeekStart, false);
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate(withTenantPath('/admin/login', tenantSlug));
        return;
      }

      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Annullamento prenotazione non riuscito.') });
    }
  }

  async function handleCancelSeries(booking: BookingSummary) {
    if (!booking.recurring_series_id) {
      return;
    }

    const seriesLabel = booking.recurring_series_label || booking.public_reference;
    if (!window.confirm(`Confermi l'annullamento di tutte le occorrenze future della serie "${seriesLabel}"?`)) {
      return;
    }

    setFeedback(null);

    try {
      const response = await cancelRecurringSeries(booking.recurring_series_id);
      setFeedback({
        tone: 'success',
        message: `Serie aggiornata: ${response.cancelled_count} occorrenze future annullate, ${response.skipped_count} saltate.`,
      });
      await loadWeek(viewWeekStart, false);
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate(withTenantPath('/admin/login', tenantSlug));
        return;
      }

      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Aggiornamento serie ricorrente non riuscito.') });
    }
  }

  async function logout() {
    await logoutAdmin(tenantSlug);
    navigate(withTenantPath('/admin/login', tenantSlug));
  }

  return (
    <div className='min-h-screen px-4 py-6 sm:px-6 lg:px-8'>
      <div className='page-shell space-y-6'>
        <div className='admin-hero-panel space-y-4'>
          <div className='flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between'>
            <div>
              <p className='text-2xl font-semibold text-cyan-100'>Prenotazioni Attuali</p>
              <h1 className='text-3xl font-bold'>Calendario settimanale prenotazioni</h1>
              <p className='mt-2 max-w-2xl text-sm text-slate-300'>Consulta velocemente le partite della settimana e apri il dettaglio di ogni prenotazione senza rinunciare alla vista elenco avanzata.</p>
            </div>
            <div className='admin-hero-actions'>
              <button className='admin-hero-button-primary' type='button' onClick={() => void loadWeek(viewWeekStart)}>Aggiorna dashboard</button>
              <button className='admin-hero-button-secondary' type='button' onClick={() => void logout()}>Esci</button>
            </div>
          </div>
          <AdminNav session={session} />
        </div>

        {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

        <SectionCard
          title='Navigazione settimana'
          description='Le frecce rapide permettono di vedere fino a due settimane prima e quattro settimane dopo rispetto a quella corrente.'
          actions={<p className='text-sm font-semibold text-cyan-800'>{formatRangeLabel(viewWeekStart)}</p>}
          elevated
        >
          <div className='flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between'>
            <div className='flex flex-wrap gap-3'>
              <button className='btn-secondary disabled:cursor-not-allowed disabled:opacity-50' type='button' onClick={() => void handleQuickNavigation(-1)} disabled={!canGoPrevious || loading}>
                <ArrowLeft size={16} />
                Settimana precedente
              </button>
              <button className='btn-secondary disabled:cursor-not-allowed disabled:opacity-50' type='button' onClick={() => void handleQuickNavigation(1)} disabled={!canGoNext || loading}>
                Settimana successiva
                <ArrowRight size={16} />
              </button>
            </div>

            <form className='grid gap-3 sm:grid-cols-[1fr_1fr_1fr_auto]' onSubmit={submitWeekJump}>
              <div>
                <label className='field-label' htmlFor='current-bookings-year'>Anno</label>
                <select id='current-bookings-year' className='text-input' value={weekYear} onChange={(event) => setWeekYear(event.target.value)}>
                  {[today.getFullYear() - 1, today.getFullYear(), today.getFullYear() + 1].map((value) => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className='field-label' htmlFor='current-bookings-month'>Mese</label>
                <select id='current-bookings-month' className='text-input' value={weekMonth} onChange={(event) => setWeekMonth(event.target.value)}>
                  {MONTH_LABELS.map((label, index) => (
                    <option key={label} value={index + 1}>{label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className='field-label' htmlFor='current-bookings-week'>Settimana del mese</label>
                <select id='current-bookings-week' className='text-input' value={weekIndex} onChange={(event) => setWeekIndex(event.target.value)}>
                  {weekOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>
              <button className='btn-primary self-end' type='submit' disabled={loading}>Vai alla settimana</button>
            </form>
          </div>
        </SectionCard>

        {loading ? <LoadingBlock label='Sto caricando le prenotazioni attuali…' /> : null}

        {!loading ? (
          <SectionCard title='Settimana in calendario' description='Le prenotazioni annullate o scadute restano fuori dalla vista per mantenere leggibile l’occupazione reale degli slot.'>
            <div className='overflow-x-auto'>
              <div className='grid min-w-[980px] grid-cols-7 gap-3'>
                {weekDays.map((day) => {
                  const dayKey = toDateInputValue(day);
                  const dayBookings = bookingsByDay[dayKey] || [];
                  const isToday = dayKey === todayKey;

                  return (
                    <div
                      key={dayKey}
                      className={`rounded-[24px] border p-4 ${isToday ? 'border-cyan-400 bg-cyan-50/70' : 'border-slate-200 bg-slate-50'}`}
                    >
                      <div className='flex items-start justify-between gap-3'>
                        <div>
                          <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>{formatWeekdayLabel(day)}</p>
                          <p className='mt-2 text-lg font-semibold text-slate-950'>{formatDayMonthLabel(day)}</p>
                        </div>
                        {isToday ? <span className='rounded-full bg-cyan-600 px-2.5 py-1 text-xs font-semibold text-white'>Oggi</span> : null}
                      </div>

                      <div className='mt-4 space-y-3'>
                        {dayBookings.length === 0 ? (
                          <div className='rounded-2xl border border-dashed border-slate-300 bg-white px-3 py-4 text-sm text-slate-500'>Nessuna prenotazione</div>
                        ) : (
                          dayBookings.map((booking) => {
                            const label = booking.customer_name || booking.recurring_series_label || booking.public_reference;
                            const showStatus = booking.status !== 'CONFIRMED';
                            const canCancel = canCancelBooking(booking.status);

                            return (
                              <article
                                key={booking.id}
                                className='rounded-2xl border border-slate-200 bg-white px-3 py-3 shadow-sm transition hover:border-cyan-400 hover:shadow-md'
                              >
                                <div className='flex items-start justify-between gap-2'>
                                  <p className='text-sm font-semibold text-slate-950'>{formatTimeValue(booking.start_at, session?.timezone)} - {formatTimeValue(booking.end_at, session?.timezone)}</p>
                                  {showStatus ? <StatusBadge status={booking.status} /> : null}
                                </div>
                                <p className='mt-2 text-sm text-slate-700'>{label}</p>
                                {booking.recurring_series_label ? <p className='mt-1 text-xs font-medium text-cyan-700'>{booking.recurring_series_label}</p> : null}
                                {booking.recurring_series_label ? <p className='mt-2 text-xs font-semibold uppercase tracking-[0.14em] text-cyan-700'>Serie ricorrente</p> : null}
                                <div className='mt-2 flex items-center gap-2 text-xs text-slate-500'>
                                  <CalendarDays size={12} />
                                  <span>{booking.public_reference}</span>
                                  <Clock3 size={12} />
                                  <span>{booking.duration_minutes} min</span>
                                </div>
                                <div className='mt-3 flex flex-wrap gap-2'>
                                  <Link
                                    to={withTenantPath(`/admin/bookings/${booking.id}`, tenantSlug)}
                                    aria-label={`Modifica ${booking.public_reference}`}
                                    className='text-sm font-semibold text-cyan-700 transition hover:text-cyan-900'
                                  >
                                    Modifica
                                  </Link>
                                  {canCancel ? (
                                    <button
                                      type='button'
                                      aria-label={`Annulla ${booking.public_reference}`}
                                      className='text-sm font-semibold text-rose-700 transition hover:text-rose-900'
                                      onClick={() => void handleCancelBooking(booking)}
                                    >
                                      Annulla
                                    </button>
                                  ) : null}
                                  {booking.recurring_series_id ? (
                                    <button
                                      type='button'
                                      aria-label={`Annulla serie ${booking.recurring_series_label || booking.public_reference}`}
                                      className='text-sm font-semibold text-amber-700 transition hover:text-amber-900'
                                      onClick={() => void handleCancelSeries(booking)}
                                    >
                                      Annulla serie
                                    </button>
                                  ) : null}
                                </div>
                              </article>
                            );
                          })
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {visibleBookings.length === 0 ? (
              <div className='mt-4'>
                <EmptyState icon={CalendarDays} title='Nessuna partita per la settimana selezionata' description='Usa le frecce rapide o il salto per mese, settimana e anno per cambiare intervallo.' />
              </div>
            ) : null}
          </SectionCard>
        ) : null}
      </div>
    </div>
  );
}