import { ChevronDown, ChevronUp } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { getAvailability } from '../services/publicApi';
import type { TimeSlot } from '../types';
import { AlertBanner } from './AlertBanner';
import { LoadingBlock } from './LoadingBlock';
import { SlotGrid } from './SlotGrid';

const INITIAL_VISIBLE_SLOTS = 6;

export function AdminTimeSlotPicker({
  bookingDate,
  durationMinutes,
  selectedSlotId,
  onSelect,
  includeSelectedUnavailable = false,
}: {
  bookingDate: string;
  durationMinutes: number;
  selectedSlotId: string;
  onSelect: (slot: TimeSlot) => void;
  includeSelectedUnavailable?: boolean;
}) {
  const [slots, setSlots] = useState<TimeSlot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let ignore = false;

    async function loadSlots() {
      setLoading(true);
      setError('');
      setExpanded(false);

      try {
        const response = await getAvailability(bookingDate, durationMinutes);
        if (!ignore) {
          setSlots(response.slots);
        }
      } catch {
        if (!ignore) {
          setSlots([]);
          setError('Non riesco a caricare gli orari disponibili in questo momento.');
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    void loadSlots();

    return () => {
      ignore = true;
    };
  }, [bookingDate, durationMinutes]);

  const selectedSlot = useMemo(
    () => slots.find((slot) => slot.slot_id === selectedSlotId),
    [selectedSlotId, slots]
  );

  const candidateSlots = useMemo(() => {
    const availableSlots = slots.filter((slot) => slot.available);
    if (!includeSelectedUnavailable || !selectedSlot || selectedSlot.available) {
      return availableSlots;
    }

    if (availableSlots.some((slot) => slot.slot_id === selectedSlot.slot_id)) {
      return availableSlots;
    }

    return [selectedSlot, ...availableSlots];
  }, [includeSelectedUnavailable, selectedSlot, slots]);

  const displayedSlots = useMemo(() => {
    if (expanded || candidateSlots.length <= INITIAL_VISIBLE_SLOTS) {
      return candidateSlots;
    }

    const initialSlots = candidateSlots.slice(0, INITIAL_VISIBLE_SLOTS);
    if (!selectedSlotId || initialSlots.some((slot) => slot.slot_id === selectedSlotId)) {
      return initialSlots;
    }

    const selectedCandidate = candidateSlots.find((slot) => slot.slot_id === selectedSlotId);
    return selectedCandidate ? [...initialSlots, selectedCandidate] : initialSlots;
  }, [candidateSlots, expanded, selectedSlotId]);

  return (
    <div className='space-y-3'>
      {error ? <AlertBanner tone='error'>{error}</AlertBanner> : null}
      {loading ? <LoadingBlock label='Sto caricando gli orari disponibili…' /> : null}
      {!loading ? (
        <SlotGrid
          slots={displayedSlots}
          selectedSlotId={selectedSlotId}
          onSelect={(slotId) => {
            const selected = slots.find((slot) => slot.slot_id === slotId);
            if (selected) {
              onSelect(selected);
            }
          }}
        />
      ) : null}
      {candidateSlots.length > INITIAL_VISIBLE_SLOTS ? (
        <button className='btn-secondary' type='button' onClick={() => setExpanded((prev) => !prev)}>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          {expanded ? 'Mostra solo i primi 6 orari' : 'Mostra tutti gli orari'}
        </button>
      ) : null}
      {selectedSlot ? (
        <p className='text-sm font-medium text-cyan-800'>Selezionato: {selectedSlot.display_start_time} → {selectedSlot.display_end_time}</p>
      ) : null}
    </div>
  );
}