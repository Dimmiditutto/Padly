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

const STATUS_CLASS_NAMES: Record<BookingStatus, string> = {
  CONFIRMED: 'status-pill-confirmed',
  PENDING_PAYMENT: 'status-pill-pending',
  COMPLETED: 'status-pill-completed',
  NO_SHOW: 'status-pill-danger',
  CANCELLED: 'status-pill-neutral',
  EXPIRED: 'status-pill-neutral',
};

export function StatusBadge({ status }: { status: BookingStatus }) {
  return (
    <span
      className={clsx(
        'status-pill',
        STATUS_CLASS_NAMES[status]
      )}
    >
      {LABELS[status]}
    </span>
  );
}
