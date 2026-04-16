import { describe, expect, it } from 'vitest';
import { canMarkBalancePaid, canMarkBookingCompleted, canMarkBookingNoShow } from './adminBookingActions';

const now = new Date('2026-04-16T12:00:00Z');

describe('admin booking action guards', () => {
  it('blocks temporal actions before the slot progresses', () => {
    expect(canMarkBookingCompleted('CONFIRMED', '2026-04-16T13:30:00Z', now)).toBe(false);
    expect(canMarkBookingNoShow('CONFIRMED', '2026-04-16T12:30:00Z', now)).toBe(false);
    expect(canMarkBalancePaid('CONFIRMED', null, '2026-04-16T12:30:00Z', now)).toBe(false);
  });

  it('allows temporal actions once the slot has started or ended', () => {
    expect(canMarkBookingCompleted('CONFIRMED', '2026-04-16T11:30:00Z', now)).toBe(true);
    expect(canMarkBookingNoShow('CONFIRMED', '2026-04-16T11:00:00Z', now)).toBe(true);
    expect(canMarkBalancePaid('COMPLETED', null, '2026-04-16T11:00:00Z', now)).toBe(true);
    expect(canMarkBalancePaid('COMPLETED', '2026-04-16T11:05:00Z', '2026-04-16T11:00:00Z', now)).toBe(false);
  });
});