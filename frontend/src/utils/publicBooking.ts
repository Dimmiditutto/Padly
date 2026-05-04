import type { PublicConfig } from '../types';
import { formatCurrency } from './format';

export function hasEnabledPublicBookingDeposit(config: PublicConfig | null) {
  if (!config) {
    return false;
  }

  const enabled = config.public_booking_deposit_enabled ?? true;
  const baseAmount = config.public_booking_base_amount ?? 20;
  const includedMinutes = config.public_booking_included_minutes ?? 90;

  return Boolean(enabled)
    && Number(baseAmount) > 0
    && Number(includedMinutes) > 0;
}

export function buildPublicDepositRuleText(config: PublicConfig | null, currentDepositAmount: number) {
  if (!config || !hasEnabledPublicBookingDeposit(config)) {
    return 'Nessuna caparra online prevista per questo club.';
  }

  const baseAmount = Number(config.public_booking_base_amount ?? 20);
  const includedMinutes = Number(config.public_booking_included_minutes ?? 90);
  const extraAmount = Number(config.public_booking_extra_amount ?? 10);
  const extraStepMinutes = Number(config.public_booking_extra_step_minutes ?? 30);

  if (extraAmount > 0 && extraStepMinutes > 0) {
    return `${formatCurrency(baseAmount)} fino a ${includedMinutes} minuti. Poi si aggiungono ${formatCurrency(extraAmount)} ogni ${extraStepMinutes} minuti successivi. Importo attuale: ${formatCurrency(currentDepositAmount)}.`;
  }

  return `${formatCurrency(baseAmount)} fino a ${includedMinutes} minuti. Nessun extra oltre la soglia configurata dal club.`;
}

export function buildBookingOverviewCards(config: PublicConfig | null, durationMinutes: number, depositRequired: boolean, depositAmount: number) {
  return [
    {
      label: 'Caparra',
      value: depositRequired ? formatCurrency(depositAmount) : 'Non prevista',
      helper: depositRequired ? `${durationMinutes} minuti • pagamento online` : 'Conferma diretta del club',
    },
    {
      label: 'Tesserati',
      value: formatBookingRateValue(calculatePublicPlayerRate(config, durationMinutes, 'member')),
      helper: `${durationMinutes} minuti per giocatore`,
    },
    {
      label: 'Non tesserati',
      value: formatBookingRateValue(calculatePublicPlayerRate(config, durationMinutes, 'non-member')),
      helper: `${durationMinutes} minuti per giocatore`,
    },
  ];
}

export function calculatePublicPlayerRate(config: PublicConfig | null, durationMinutes: number, playerType: 'member' | 'non-member') {
  if (!config) {
    return null;
  }

  const hourlyRate = playerType === 'member' ? config.member_hourly_rate : config.non_member_hourly_rate;
  const ninetyMinuteRate = playerType === 'member' ? config.member_ninety_minute_rate : config.non_member_ninety_minute_rate;

  if (durationMinutes <= 60) {
    return hourlyRate;
  }

  if (durationMinutes === 90) {
    return ninetyMinuteRate;
  }

  const halfHourStepRate = ninetyMinuteRate - hourlyRate;
  const extraHalfHourBlocks = Math.max(0, Math.round((durationMinutes - 90) / 30));
  return ninetyMinuteRate + (extraHalfHourBlocks * halfHourStepRate);
}

export function formatBookingRateValue(rate: number | null) {
  if (rate == null) {
    return 'In aggiornamento';
  }

  return formatCurrency(rate);
}