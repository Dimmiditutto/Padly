export function formatCurrency(amount: number) {
  return new Intl.NumberFormat('it-IT', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatDate(dateValue: string) {
  return new Date(dateValue).toLocaleDateString('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export function formatDateTime(dateValue: string) {
  return new Date(dateValue).toLocaleString('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatRomeWeekdayLabel(value: string) {
  const [year, month, day] = value.split('-').map(Number);
  if (!year || !month || !day) {
    return '';
  }

  const normalizedDate = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
  const label = new Intl.DateTimeFormat('it-IT', {
    weekday: 'long',
    timeZone: 'Europe/Rome',
  }).format(normalizedDate);

  return label.charAt(0).toUpperCase() + label.slice(1);
}

export function toDateInputValue(value: Date) {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, '0');
  const day = `${value.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}