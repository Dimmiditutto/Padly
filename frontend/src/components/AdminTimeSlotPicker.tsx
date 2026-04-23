import { ChevronDown, ChevronUp } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { getAvailability } from '../services/publicApi';
import type { AvailabilityResponse, CourtAvailability, TimeSlot } from '../types';
import { AlertBanner } from './AlertBanner';
import { LoadingBlock } from './LoadingBlock';
import { SlotGrid } from './SlotGrid';

const INITIAL_VISIBLE_SLOTS = 6;

export function AdminTimeSlotPicker({
  bookingDate,
  durationMinutes,
  courtId,
  selectedSlotId,
  onSelect,
  includeSelectedUnavailable = false,
  tenantSlug,
}: {
  bookingDate: string;
  durationMinutes: number;
  courtId?: string | null;
  selectedSlotId: string;
  onSelect: (slot: TimeSlot) => void;
  includeSelectedUnavailable?: boolean;
  tenantSlug?: string | null;
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
        const response = await getAvailability(bookingDate, durationMinutes, tenantSlug);
        const courtGroups = normalizeCourtGroups(response);
        const activeCourt = courtId ? courtGroups.find((group) => group.court_id === courtId) : courtGroups[0];
        if (!ignore) {
          setSlots(activeCourt?.slots || []);
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
  }, [bookingDate, courtId, durationMinutes, tenantSlug]);

  const selectedSlot = useMemo(
    () => slots.find((slot) => slot.slot_id === selectedSlotId && (!courtId || slot.court_id === courtId)),
    [courtId, selectedSlotId, slots]
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

  const highlightedSlotIds = useMemo(
    () => buildHighlightedSlotIds(candidateSlots, selectedSlotId, durationMinutes),
    [candidateSlots, durationMinutes, selectedSlotId]
  );

  return (
    <div className='space-y-3'>
      {error ? <AlertBanner tone='error'>{error}</AlertBanner> : null}
      {loading ? <LoadingBlock label='Sto caricando gli orari disponibili…' /> : null}
      {!loading ? (
        <SlotGrid
          slots={displayedSlots}
          selectedSlotId={selectedSlotId}
          highlightedSlotIds={highlightedSlotIds}
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

function buildHighlightedSlotIds(slots: TimeSlot[], selectedSlotId: string, durationMinutes: number) {
  if (!selectedSlotId) {
    return [];
  }

  const selectedStart = new Date(selectedSlotId).getTime();
  if (Number.isNaN(selectedStart)) {
    return [];
  }

  const coveredStartTimes = new Set<number>();
  const slotCount = Math.max(1, durationMinutes / 30);
  for (let index = 0; index < slotCount; index += 1) {
    coveredStartTimes.add(selectedStart + (index * 30 * 60 * 1000));
  }

  return slots
    .filter((slot) => coveredStartTimes.has(new Date(slot.slot_id).getTime()))
    .map((slot) => slot.slot_id);
}

function normalizeCourtGroups(response: AvailabilityResponse): CourtAvailability[] {
  if (response.courts && response.courts.length > 0) {
    return response.courts;
  }

  if (response.slots.length === 0) {
    return [];
  }

  const fallbackCourtId = response.slots[0].court_id || 'default-court';
  const fallbackCourtName = response.slots[0].court_name || 'Campo 1';

  return [{
    court_id: fallbackCourtId,
    court_name: fallbackCourtName,
    slots: response.slots.map((slot) => ({
      ...slot,
      court_id: slot.court_id || fallbackCourtId,
      court_name: slot.court_name || fallbackCourtName,
    })),
  }];
}