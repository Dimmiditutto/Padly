import { ArrowRight, CalendarDays, Clock3, WalletCards } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import type { BookingSummary } from '../types';
import { canCancelBooking, canMarkBalancePaid, canMarkBookingCompleted, canMarkBookingNoShow, canRestoreBookingConfirmed } from '../utils/adminBookingActions';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';
import { StatusBadge } from './StatusBadge';

export function AdminBookingCard({
  booking,
  onMarkBalancePaid,
  onUpdateStatus,
}: {
  booking: BookingSummary;
  onMarkBalancePaid: (bookingId: string) => Promise<void>;
  onUpdateStatus: (bookingId: string, status: 'CONFIRMED' | 'COMPLETED' | 'NO_SHOW' | 'CANCELLED') => Promise<void>;
}) {
  const location = useLocation();
  const tenantSlug = getTenantSlugFromSearchParams(new URLSearchParams(location.search));
  const isRecurring = booking.source === 'ADMIN_RECURRING' || (booking.deposit_amount ?? 0) === 0;
  const canCancel = canCancelBooking(booking.status);
  const canComplete = canMarkBookingCompleted(booking.status, booking.end_at);
  const canNoShow = canMarkBookingNoShow(booking.status, booking.start_at);
  const canRestore = canRestoreBookingConfirmed(booking.status);
  const canMarkBalance = !isRecurring && canMarkBalancePaid(booking.status, booking.balance_paid_at, booking.start_at);

  return (
    <article className='surface-card-compact shadow-sm'>
      <div className='flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between'>
        <div className='space-y-2'>
          <div className='flex flex-wrap items-center gap-2'>
            <p className='font-semibold text-slate-950'>{booking.public_reference}</p>
            <StatusBadge status={booking.status} />
          </div>
          <p className='text-sm text-slate-600'>{booking.customer_name || 'Cliente non associato'} • {booking.customer_phone || '—'}</p>
          {booking.recurring_series_label ? <p className='text-sm font-medium text-cyan-800'>Serie: {booking.recurring_series_label}</p> : null}
          <div className='flex flex-wrap gap-3 text-sm text-slate-600'>
            <span className='inline-flex items-center gap-1'><CalendarDays size={14} /> {booking.booking_date_local}</span>
            <span className='inline-flex items-center gap-1'><Clock3 size={14} /> {booking.duration_minutes} min</span>
            {!isRecurring ? <span className='inline-flex items-center gap-1'><WalletCards size={14} /> Caparra €{booking.deposit_amount}</span> : null}
          </div>
        </div>
        <Link to={withTenantPath(`/admin/bookings/${booking.id}`, tenantSlug)} className='btn-ghost'>Dettaglio <ArrowRight size={16} /></Link>
      </div>
      <div className='mt-5 flex flex-wrap gap-2.5'>
        {!isRecurring ? <button className='btn-primary disabled:cursor-not-allowed disabled:opacity-50' disabled={!canMarkBalance} onClick={() => void onMarkBalancePaid(booking.id)}>Saldo al campo</button> : null}
        <button className='btn-soft-success' disabled={!canComplete} onClick={() => void onUpdateStatus(booking.id, 'COMPLETED')}>Completed</button>
        <button className='btn-soft-warning' disabled={!canNoShow} onClick={() => void onUpdateStatus(booking.id, 'NO_SHOW')}>No-show</button>
        <button className='btn-soft-danger' disabled={!canCancel} onClick={() => void onUpdateStatus(booking.id, 'CANCELLED')}>Annulla</button>
        {canRestore ? <button className='btn-secondary' onClick={() => void onUpdateStatus(booking.id, 'CONFIRMED')}>Ripristina confermata</button> : null}
      </div>
    </article>
  );
}