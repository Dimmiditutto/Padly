import type { TimeSlot } from '../types';
import { EmptyState } from './EmptyState';
import { Clock3 } from 'lucide-react';

export function SlotGrid({
  slots,
  selectedTime,
  onSelect,
}: {
  slots: TimeSlot[];
  selectedTime: string;
  onSelect: (time: string) => void;
}) {
  const visibleSlots = slots.filter((slot) => slot.available);

  if (slots.length === 0) {
    return <EmptyState icon={Clock3} title='Nessuno slot disponibile' description='Cambia data o durata per trovare una fascia libera.' />;
  }

  return (
    <>
      <div className='grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5'>
        {slots.map((slot) => (
          <button
            key={`${slot.start_time}-${slot.end_time}`}
            type='button'
            onClick={() => slot.available && onSelect(slot.start_time)}
            disabled={!slot.available}
            className={`rounded-2xl border px-3 py-3 text-sm font-medium transition ${
              selectedTime === slot.start_time
                ? 'border-cyan-600 bg-cyan-50 text-cyan-800'
                : slot.available
                  ? 'border-slate-200 bg-white text-slate-700 hover:border-slate-400'
                  : 'cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400'
            }`}
          >
            {slot.start_time}
          </button>
        ))}
      </div>
      {visibleSlots.length === 0 ? (
        <div className='mt-4'>
          <EmptyState icon={Clock3} title='Fasce piene per questa selezione' description='Il campo è occupato o bloccato. Prova un altro orario o una durata diversa.' />
        </div>
      ) : null}
    </>
  );
}