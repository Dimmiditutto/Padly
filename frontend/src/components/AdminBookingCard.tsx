import { ArrowRight, CalendarDays, Clock3, WalletCards } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import type { BookingSummary } from '../types';
import { canCancelBooking, canDeleteBookingPermanently, canMarkBalancePaid, canMarkBookingCompleted, canMarkBookingNoShow, canRestoreBookingConfirmed } from '../utils/adminBookingActions';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';
import { StatusBadge } from './StatusBadge';

export function AdminBookingCard({
  booking,
  onDelete,
  onMarkBalancePaid,
  onUpdateStatus,
}: {
  booking: BookingSummary;
  onDelete: (bookingId: string) => Promise<void>;
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
  const canDelete = canDeleteBookingPermanently(booking.status);
  const heading = booking.customer_name || 'Prenotazione singola';

  return (
    <article className='surface-card-compact shadow-sm'>
      <div className='flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between'>
        <div className='space-y-2'>
          <div className='flex flex-wrap items-center gap-2'>
            <p className='font-semibold text-slate-950'>{heading}</p>
            <StatusBadge status={booking.status} />
          </div>
          <p className='text-sm text-slate-600'>{booking.customer_phone || 'Telefono non disponibile'}</p>
          <div className='flex flex-wrap gap-3 text-sm text-slate-600'>
            <span className='inline-flex items-center gap-1'><CalendarDays size={14} /> {booking.booking_date_local}</span>
            <span className='inline-flex items-center gap-1'><Clock3 size={14} /> Durata {booking.duration_minutes} minuti</span>
            {!isRecurring ? <span className='inline-flex items-center gap-1'><WalletCards size={14} /> Caparra €{booking.deposit_amount}</span> : null}
          </div>
        </div>
        <Link to={withTenantPath(`/admin/bookings/${booking.id}`, tenantSlug)} className='btn-ghost'>Dettaglio <ArrowRight size={16} /></Link>
      </div>
      <div className='mt-5 flex flex-wrap gap-2.5'>
        {!isRecurring && canMarkBalance ? <button className='btn-primary' onClick={() => void onMarkBalancePaid(booking.id)}>Saldo al campo</button> : null}
        {canComplete ? <button className='btn-soft-success' onClick={() => void onUpdateStatus(booking.id, 'COMPLETED')}>Completed</button> : null}
        {canNoShow ? <button className='btn-soft-warning' onClick={() => void onUpdateStatus(booking.id, 'NO_SHOW')}>No-show</button> : null}
        {canCancel ? <button className='btn-soft-danger' onClick={() => void onUpdateStatus(booking.id, 'CANCELLED')}>Annulla</button> : null}
        {canRestore ? <button className='btn-secondary' onClick={() => void onUpdateStatus(booking.id, 'CONFIRMED')}>Ripristina confermata</button> : null}
        {canDelete ? <button className='btn-secondary' onClick={() => void onDelete(booking.id)}>Elimina</button> : null}
      </div>
    </article>
  );
}