import { describe, expect, it } from 'vitest';
import { formatCurrency, toDateInputValue } from './format';

describe('format utilities', () => {
  it('formats euro amounts for Italian locale', () => {
    expect(formatCurrency(20)).toBe('20 €');
  });

  it('builds an input-friendly date string', () => {
    expect(toDateInputValue(new Date('2026-04-16T10:30:00Z'))).toBe('2026-04-16');
  });
});