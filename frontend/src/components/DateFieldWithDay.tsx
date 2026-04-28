import { formatWeekdayLabel } from '../utils/format';

export function DateFieldWithDay({
  id,
  label,
  value,
  onChange,
  min,
  max,
  showDayPreview = true,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  min?: string;
  max?: string;
  showDayPreview?: boolean;
}) {
  return (
    <div>
      <label className='field-label' htmlFor={id}>{label}</label>
      <input
        id={id}
        className='text-input'
        type='date'
        value={value}
        min={min}
        max={max}
        onChange={(event) => onChange(event.target.value)}
      />
      {showDayPreview ? (
        <div className='mt-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3'>
          <p className='text-sm font-semibold uppercase tracking-[0.16em] text-slate-500'>Giorno</p>
          <p className='mt-2 text-base font-medium text-slate-900'>{formatWeekdayLabel(value)}</p>
        </div>
      ) : null}
    </div>
  );
}