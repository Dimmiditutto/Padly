import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { AlertBanner } from '../AlertBanner';
import { DateFieldWithDay } from '../DateFieldWithDay';
import { LoadingBlock } from '../LoadingBlock';
import { getAvailability } from '../../services/publicApi';
import type { AvailabilityResponse, CourtAvailability, PlayLevel, TimeSlot } from '../../types';
import { toDateInputValue } from '../../utils/format';
import { PLAY_LEVEL_OPTIONS, formatPlayLevel } from '../../utils/play';

const PLAY_CREATE_DURATIONS = [90];
const today = toDateInputValue(new Date());

export interface PlayCreateIntent {
  bookingDate: string;
  durationMinutes: number;
  courtId: string;
  courtName: string;
  slotId: string;
  startTime: string;
  levelRequested: PlayLevel;
  note: string;
}

function normalizeCourtGroups(response: AvailabilityResponse): CourtAvailability[] {
  if (response.courts && response.courts.length > 0) {
    return response.courts
      .map((group) => ({
        ...group,
        slots: group.slots.filter((slot) => slot.available),
      }))
      .filter((group) => group.slots.length > 0);
  }

  const availableSlots = response.slots.filter((slot) => slot.available);
  if (availableSlots.length === 0) {
    return [];
  }

  return [{
    court_id: availableSlots[0].court_id || 'default-court',
    court_name: availableSlots[0].court_name || 'Campo del club',
    badge_label: availableSlots[0].court_badge_label || null,
    slots: availableSlots,
  }];
}

export function CreateMatchForm({
  tenantSlug,
  onCreateIntent,
}: {
  tenantSlug: string;
  onCreateIntent: (intent: PlayCreateIntent) => void;
}) {
  const [bookingDate, setBookingDate] = useState(today);
  const [durationMinutes, setDurationMinutes] = useState(90);
  const [courtGroups, setCourtGroups] = useState<CourtAvailability[]>([]);
  const [selectedCourtId, setSelectedCourtId] = useState('');
  const [selectedSlotId, setSelectedSlotId] = useState('');
  const [levelRequested, setLevelRequested] = useState<PlayLevel>('NO_PREFERENCE');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    void loadAvailability();
  }, [bookingDate, durationMinutes, tenantSlug]);

  const selectedCourt = useMemo(
    () => courtGroups.find((group) => group.court_id === selectedCourtId) || null,
    [courtGroups, selectedCourtId]
  );
  const selectedSlot = useMemo(
    () => selectedCourt?.slots.find((slot) => slot.slot_id === selectedSlotId) || null,
    [selectedCourt, selectedSlotId]
  );

  async function loadAvailability() {
    setLoading(true);
    setFeedback(null);

    try {
      const response = await getAvailability(bookingDate, durationMinutes, tenantSlug);
      const normalizedCourtGroups = normalizeCourtGroups(response);
      setCourtGroups(normalizedCourtGroups);
      setSelectedCourtId(normalizedCourtGroups[0]?.court_id || '');
      setSelectedSlotId(normalizedCourtGroups[0]?.slots[0]?.slot_id || '');
    } catch {
      setCourtGroups([]);
      setSelectedCourtId('');
      setSelectedSlotId('');
      setFeedback('Non riesco a leggere gli slot disponibili per preparare una nuova partita.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!selectedCourt) {
      setSelectedSlotId('');
      return;
    }

    const stillAvailable = selectedCourt.slots.some((slot) => slot.slot_id === selectedSlotId);
    if (!stillAvailable) {
      setSelectedSlotId(selectedCourt.slots[0]?.slot_id || '');
    }
  }, [selectedCourt, selectedSlotId]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    if (!selectedCourt || !selectedSlot) {
      setFeedback('Seleziona prima un campo e uno slot libero per la nuova partita.');
      return;
    }

    onCreateIntent({
      bookingDate,
      durationMinutes,
      courtId: selectedCourt.court_id,
      courtName: selectedCourt.court_name,
      slotId: selectedSlot.slot_id,
      startTime: selectedSlot.start_time,
      levelRequested,
      note: note.trim(),
    });
  }

  return (
    <form className='space-y-4' onSubmit={handleSubmit}>
      <div className='grid gap-4 lg:grid-cols-2'>
        <DateFieldWithDay id='play-create-date' label='Giorno' value={bookingDate} min={today} onChange={setBookingDate} />

        <div>
          <label className='field-label' htmlFor='play-create-duration'>Durata</label>
          <select
            id='play-create-duration'
            className='text-input'
            value={durationMinutes}
            onChange={(event) => setDurationMinutes(Number(event.target.value))}
          >
            {PLAY_CREATE_DURATIONS.map((duration) => (
              <option key={duration} value={duration}>{duration} minuti</option>
            ))}
          </select>
          <p className='mt-2 text-sm text-slate-600'>In Phase 3 le partite play restano fissate a 90 minuti per chiudere il match nello slot reale del club.</p>
        </div>
      </div>

      {loading ? <LoadingBlock label='Carico gli slot liberi del club…' /> : null}
      {feedback ? <AlertBanner tone='error'>{feedback}</AlertBanner> : null}

      {!loading && courtGroups.length === 0 ? (
        <AlertBanner tone='info'>Non ci sono slot liberi utilizzabili per creare una nuova partita nella selezione corrente.</AlertBanner>
      ) : null}

      {!loading && courtGroups.length > 0 ? (
        <>
          <div className='grid gap-4 lg:grid-cols-2'>
            <div>
              <label className='field-label' htmlFor='play-create-court'>Campo</label>
              <select
                id='play-create-court'
                className='text-input'
                value={selectedCourtId}
                onChange={(event) => setSelectedCourtId(event.target.value)}
              >
                {courtGroups.map((group) => (
                  <option key={group.court_id} value={group.court_id}>
                    {group.court_name}{group.badge_label ? ` • ${group.badge_label}` : ''}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className='field-label' htmlFor='play-create-slot'>Slot libero reale</label>
              <select
                id='play-create-slot'
                className='text-input'
                value={selectedSlotId}
                onChange={(event) => setSelectedSlotId(event.target.value)}
              >
                {(selectedCourt?.slots || []).map((slot: TimeSlot) => (
                  <option key={slot.slot_id} value={slot.slot_id}>
                    {slot.display_start_time} - {slot.display_end_time}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className='grid gap-4 lg:grid-cols-2'>
            <div>
              <label className='field-label' htmlFor='play-create-level'>Livello partita</label>
              <select
                id='play-create-level'
                className='text-input'
                value={levelRequested}
                onChange={(event) => setLevelRequested(event.target.value as PlayLevel)}
              >
                {PLAY_LEVEL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>

            <div className='rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3'>
              <p className='text-sm font-semibold uppercase tracking-[0.14em] text-slate-500'>Riepilogo</p>
              <p className='mt-2 text-sm text-slate-700'>
                {selectedCourt?.court_name || 'Campo'} • {selectedSlot?.display_start_time || '--:--'} • {formatPlayLevel(levelRequested)}
              </p>
            </div>
          </div>

          <div>
            <label className='field-label' htmlFor='play-create-note'>Nota opzionale</label>
            <textarea
              id='play-create-note'
              className='text-input min-h-[112px] resize-y'
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder='Es. partita amichevole, ritmo alto, cerco ultimo giocatore per completare il gruppo.'
            />
          </div>

          <button type='submit' className='btn-primary w-full sm:w-auto'>Crea nuova partita</button>
        </>
      ) : null}
    </form>
  );
}