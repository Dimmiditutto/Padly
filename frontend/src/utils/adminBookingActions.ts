import type { BookingStatus } from '../types';

function hasStarted(startAt: string, now: Date) {
  return new Date(startAt).getTime() <= now.getTime();
}

function hasEnded(endAt: string, now: Date) {
  return new Date(endAt).getTime() <= now.getTime();
}

export function canCancelBooking(status: BookingStatus) {
  return status === 'PENDING_PAYMENT' || status === 'CONFIRMED';
}

export function canMarkBookingCompleted(status: BookingStatus, endAt: string, now = new Date()) {
  return status === 'CONFIRMED' && hasEnded(endAt, now);
}

export function canMarkBookingNoShow(status: BookingStatus, startAt: string, now = new Date()) {
  return status === 'CONFIRMED' && hasStarted(startAt, now);
}

export function canRestoreBookingConfirmed(status: BookingStatus) {
  return status === 'COMPLETED' || status === 'NO_SHOW';
}

export function canMarkBalancePaid(status: BookingStatus, balancePaidAt: string | null | undefined, startAt: string, now = new Date()) {
  return !balancePaidAt && (status === 'CONFIRMED' || status === 'COMPLETED') && hasStarted(startAt, now);
}