import type { BookingDetail, BookingSource, BookingSummary } from '../types';

type BookingOriginShape = Pick<BookingSummary, 'created_by' | 'source'> | Pick<BookingDetail, 'created_by' | 'source'>;

export type BookingOriginKind = 'PLAY' | 'ADMIN_RECURRING' | 'ADMIN_MANUAL' | 'PUBLIC';

export function isPlayOriginBooking(booking: BookingOriginShape): boolean {
  return booking.source === 'ADMIN_MANUAL' && String(booking.created_by || '').startsWith('play:');
}

export function getBookingOriginKind(booking: BookingOriginShape): BookingOriginKind {
  if (isPlayOriginBooking(booking)) {
    return 'PLAY';
  }
  if (booking.source === 'ADMIN_RECURRING') {
    return 'ADMIN_RECURRING';
  }
  if (booking.source === 'ADMIN_MANUAL') {
    return 'ADMIN_MANUAL';
  }
  return 'PUBLIC';
}

export function getBookingOriginLabel(booking: BookingOriginShape): string {
  switch (getBookingOriginKind(booking)) {
    case 'PLAY':
      return 'Play community';
    case 'ADMIN_RECURRING':
      return 'Admin ricorrente';
    case 'ADMIN_MANUAL':
      return 'Admin manuale';
    case 'PUBLIC':
    default:
      return 'Booking pubblico';
  }
}

export function getPlayMatchIdFromBooking(booking: BookingOriginShape): string | null {
  if (!isPlayOriginBooking(booking)) {
    return null;
  }
  const value = String(booking.created_by || '');
  return value.startsWith('play:') ? value.slice('play:'.length) : null;
}

export function getBookingOriginBadgeClassName(booking: BookingOriginShape): string {
  switch (getBookingOriginKind(booking)) {
    case 'PLAY':
      return 'status-pill-confirmed';
    case 'ADMIN_RECURRING':
      return 'status-pill-neutral';
    case 'ADMIN_MANUAL':
      return 'status-pill-pending';
    case 'PUBLIC':
    default:
      return 'status-pill-neutral';
  }
}

export function countPlayOriginBookings(bookings: BookingSummary[]): number {
  return bookings.filter(isPlayOriginBooking).length;
}