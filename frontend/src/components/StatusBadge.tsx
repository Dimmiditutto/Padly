import clsx from 'clsx';
import type { BookingStatus } from '../types';

const LABELS: Record<BookingStatus, string> = {
  PENDING_PAYMENT: 'In attesa pagamento',
  CONFIRMED: 'Confermata',
  CANCELLED: 'Annullata',
  COMPLETED: 'Completata',
  NO_SHOW: 'No-show',
  EXPIRED: 'Scaduta',
};

export function StatusBadge({ status }: { status: BookingStatus }) {
  return (
    <span
      className={clsx(
        'inline-flex rounded-full px-2.5 py-1 text-xs font-semibold',
        status === 'CONFIRMED' && 'bg-emerald-100 text-emerald-700',
        status === 'PENDING_PAYMENT' && 'bg-amber-100 text-amber-700',
        status === 'COMPLETED' && 'bg-cyan-100 text-cyan-700',
        status === 'NO_SHOW' && 'bg-rose-100 text-rose-700',
        (status === 'CANCELLED' || status === 'EXPIRED') && 'bg-slate-200 text-slate-700'
      )}
    >
      {LABELS[status]}
    </span>
  );
}
