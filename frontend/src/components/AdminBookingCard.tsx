import { ArrowRight, CalendarDays, Clock3, WalletCards } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { BookingSummary } from '../types';
import { StatusBadge } from './StatusBadge';

export function AdminBookingCard({
  booking,
  onMarkBalancePaid,
  onUpdateStatus,
}: {
  booking: BookingSummary;
  onMarkBalancePaid: (bookingId: string) => Promise<void>;
  onUpdateStatus: (bookingId: string, status: 'COMPLETED' | 'NO_SHOW' | 'CANCELLED') => Promise<void>;
}) {
  return (
    <article className='rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm'>
      <div className='flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between'>
        <div className='space-y-2'>
          <div className='flex flex-wrap items-center gap-2'>
            <p className='font-semibold text-slate-950'>{booking.public_reference}</p>
            <StatusBadge status={booking.status} />
          </div>
          <p className='text-sm text-slate-600'>{booking.customer_name || 'Cliente non associato'} • {booking.customer_phone || '—'}</p>
          <div className='flex flex-wrap gap-3 text-sm text-slate-600'>
            <span className='inline-flex items-center gap-1'><CalendarDays size={14} /> {booking.booking_date_local}</span>
            <span className='inline-flex items-center gap-1'><Clock3 size={14} /> {booking.duration_minutes} min</span>
            <span className='inline-flex items-center gap-1'><WalletCards size={14} /> Caparra €{booking.deposit_amount}</span>
          </div>
        </div>
        <Link to={`/admin/bookings/${booking.id}`} className='btn-ghost'>Dettaglio <ArrowRight size={16} /></Link>
      </div>
      <div className='mt-4 flex flex-wrap gap-2'>
        <button className='btn-secondary' onClick={() => void onMarkBalancePaid(booking.id)}>Saldo al campo</button>
        <button className='btn-secondary' onClick={() => void onUpdateStatus(booking.id, 'COMPLETED')}>Completed</button>
        <button className='btn-secondary' onClick={() => void onUpdateStatus(booking.id, 'NO_SHOW')}>No-show</button>
        <button className='btn-secondary' onClick={() => void onUpdateStatus(booking.id, 'CANCELLED')}>Annulla</button>
      </div>
    </article>
  );
}