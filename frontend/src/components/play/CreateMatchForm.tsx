import { ChevronDown, ChevronUp } from 'lucide-react';
import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { AlertBanner } from '../AlertBanner';
import { DateFieldWithDay } from '../DateFieldWithDay';
import { LoadingBlock } from '../LoadingBlock';
import { SlotGrid } from '../SlotGrid';
import { getAvailability } from '../../services/publicApi';
import type { AvailabilityResponse, CourtAvailability, PlayLevel, TimeSlot } from '../../types';
import { toDateInputValue } from '../../utils/format';
import { PLAY_LEVEL_OPTIONS, formatPlayLevel } from '../../utils/play';

const PLAY_CREATE_DURATIONS = [90];
const COLLAPSED_COURT_SLOT_COUNT = 8;
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
    return response.courts.map((group) => ({
      ...group,
      slots: group.slots.map((slot) => ({
        ...slot,
        court_id: slot.court_id || group.court_id,
        court_name: slot.court_name || group.court_name,
        court_badge_label: slot.court_badge_label || group.badge_label || null,
      })),
    }));
  }

  if (response.slots.length === 0) {
    return [];
  }

  return [{
    court_id: response.slots[0].court_id || 'default-court',
    court_name: response.slots[0].court_name || 'Campo del club',
    badge_label: response.slots[0].court_badge_label || null,
    slots: response.slots.map((slot) => ({
      ...slot,
      court_id: slot.court_id || response.slots[0].court_id || 'default-court',
      court_name: slot.court_name || response.slots[0].court_name || 'Campo del club',
      court_badge_label: slot.court_badge_label || response.slots[0].court_badge_label || null,
    })),
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
  const [expandedCourtIds, setExpandedCourtIds] = useState<Record<string, boolean>>({});
  const [selectedCourtId, setSelectedCourtId] = useState('');
  const [selectedSlotId, setSelectedSlotId] = useState('');
  const [levelRequested, setLevelRequested] = useState<PlayLevel>('NO_PREFERENCE');
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    void loadAvailability();
  }, [bookingDate, durationMinutes, tenantSlug]);

  const visibleCourtGroups = useMemo(
    () => courtGroups.map((group) => ({ ...group, slots: group.slots.filter(isSlotWithinOpeningHours) })),
    [courtGroups]
  );

  const selectedCourt = useMemo(
    () => visibleCourtGroups.find((group) => group.court_id === selectedCourtId) || null,
    [selectedCourtId, visibleCourtGroups]
  );
  const selectedSlot = useMemo(
    () => selectedCourt?.slots.find((slot) => slot.slot_id === selectedSlotId && slot.available) || null,
    [selectedCourt, selectedSlotId]
  );
  const highlightedSlotIds = useMemo(
    () => buildHighlightedSlotIds(selectedCourt?.slots || [], selectedSlotId, durationMinutes),
    [durationMinutes, selectedCourt, selectedSlotId]
  );

  async function loadAvailability() {
    setLoading(true);
    setFeedback(null);

    try {
      const response = await getAvailability(bookingDate, durationMinutes, tenantSlug);
      const normalizedCourtGroups = normalizeCourtGroups(response);
      setCourtGroups(normalizedCourtGroups);
      setExpandedCourtIds({});

      const initialSelection = findFirstAvailableSelection(normalizedCourtGroups);
      setSelectedCourtId(initialSelection?.courtId || normalizedCourtGroups[0]?.court_id || '');
      setSelectedSlotId(initialSelection?.slotId || '');
    } catch {
      setCourtGroups([]);
      setExpandedCourtIds({});
      setSelectedCourtId('');
      setSelectedSlotId('');
      setFeedback('Non riesco a leggere gli slot disponibili per preparare una nuova partita.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (visibleCourtGroups.length === 0) {
      if (selectedCourtId || selectedSlotId) {
        setSelectedCourtId('');
        setSelectedSlotId('');
      }
      return;
    }

    const currentCourt = visibleCourtGroups.find((group) => group.court_id === selectedCourtId) || null;
    if (!currentCourt) {
      const initialSelection = findFirstAvailableSelection(visibleCourtGroups);
      setSelectedCourtId(initialSelection?.courtId || visibleCourtGroups[0].court_id);
      setSelectedSlotId(initialSelection?.slotId || '');
      return;
    }

    const stillAvailable = currentCourt.slots.some((slot) => slot.slot_id === selectedSlotId && slot.available);
    if (!stillAvailable) {
      setSelectedSlotId(currentCourt.slots.find((slot) => slot.available)?.slot_id || '');
    }
  }, [selectedCourtId, selectedSlotId, visibleCourtGroups]);

  function handleCourtSelection(courtId: string) {
    setSelectedCourtId(courtId);

    const nextCourt = visibleCourtGroups.find((group) => group.court_id === courtId);
    setSelectedSlotId(nextCourt?.slots.find((slot) => slot.available)?.slot_id || '');
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    if (!selectedCourt || !selectedSlot) {
      setFeedback('Seleziona prima un campo e uno slot libero per la nuova partita.');
      setSelectedSlotId('');
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
      {loading ? <LoadingBlock label='Carico gli slot liberi del club…' /> : null}
      {feedback ? <AlertBanner tone='error'>{feedback}</AlertBanner> : null}

      {!loading && visibleCourtGroups.length === 0 ? (
        <AlertBanner tone='info'>Non ci sono slot liberi utilizzabili per creare una nuova partita nella selezione corrente.</AlertBanner>
      ) : null}

      {!loading ? (
        <div className='grid gap-6 xl:grid-cols-[1.1fr_0.9fr]'>
          <div className='space-y-5'>
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
                <div className='mt-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600'>
                  Le partite play restano a 90 minuti per riusare lo stesso motore slot della prenotazione utente.
                </div>
              </div>
            </div>

            {visibleCourtGroups.length > 0 ? (
              <div className='space-y-4'>
                <div className='flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between'>
                  <div>
                    <p className='text-base font-semibold text-slate-900'>Orari disponibili per campo</p>
                    <p className='mt-1 text-sm text-slate-600'>La griglia usa lo stesso stato visivo della home booking: puoi distinguere subito slot liberi e occupati.</p>
                  </div>
                  <div className='flex flex-wrap gap-2 text-xs font-semibold'>
                    <span className='rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-cyan-700'>Slot libero</span>
                    <span className='rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-slate-500'>Slot occupato</span>
                  </div>
                </div>

                <div className='space-y-4'>
                  {visibleCourtGroups.map((group) => {
                    const selectedOnCourt = selectedCourtId === group.court_id;
                    const availableCount = group.slots.filter((slot) => slot.available).length;
                    const occupiedCount = group.slots.length - availableCount;

                    return (
                      <div
                        key={group.court_id}
                        className={`rounded-2xl border p-4 transition ${selectedOnCourt ? 'border-cyan-300 bg-cyan-50/60' : 'border-slate-200 bg-slate-50'}`}
                      >
                        <div className='mb-3 flex items-center justify-between gap-3'>
                          <div>
                            <button
                              type='button'
                              className='text-left'
                              onClick={() => handleCourtSelection(group.court_id)}
                            >
                              <p className='text-sm font-semibold text-slate-900'>{group.court_name}</p>
                              <p className='mt-1 text-xs text-slate-500'>
                                {formatSlotCountLabel(availableCount, 'slot libero', 'slot liberi')} • {formatSlotCountLabel(occupiedCount, 'slot occupato', 'slot occupati')}
                              </p>
                            </button>
                          </div>
                          <div className='flex items-center gap-2'>
                            {group.badge_label ? <span className='rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-600'>{group.badge_label}</span> : null}
                            {group.slots.length > COLLAPSED_COURT_SLOT_COUNT ? (
                              <button
                                type='button'
                                aria-expanded={expandedCourtIds[group.court_id] ? 'true' : 'false'}
                                aria-label={`${expandedCourtIds[group.court_id] ? 'Comprimi' : 'Espandi'} orari di ${group.court_name}`}
                                className='inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:text-slate-900'
                                onClick={() => setExpandedCourtIds((prev) => ({ ...prev, [group.court_id]: !prev[group.court_id] }))}
                              >
                                {expandedCourtIds[group.court_id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                              </button>
                            ) : null}
                          </div>
                        </div>

                        <SlotGrid
                          slots={getDisplayedCourtSlots({
                            slots: group.slots,
                            expanded: Boolean(expandedCourtIds[group.court_id]),
                            selectedSlotId: selectedOnCourt ? selectedSlotId : '',
                            highlightedSlotIds: selectedOnCourt ? highlightedSlotIds : [],
                          })}
                          selectedSlotId={selectedOnCourt ? selectedSlotId : ''}
                          highlightedSlotIds={selectedOnCourt ? highlightedSlotIds : []}
                          unavailableStateContent={buildCollapsedCourtCta({
                            courtId: group.court_id,
                            slots: group.slots,
                            expanded: Boolean(expandedCourtIds[group.court_id]),
                            onExpand: () => setExpandedCourtIds((prev) => ({ ...prev, [group.court_id]: true })),
                          })}
                          onSelect={(slotId) => {
                            setSelectedCourtId(group.court_id);
                            setSelectedSlotId(slotId);
                          }}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </div>

          <div className='space-y-4'>
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

            <div className='rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4'>
              <p className='text-sm font-semibold uppercase tracking-[0.14em] text-slate-500'>Riepilogo</p>
              <p className='mt-3 text-sm text-slate-700'>Campo: <strong>{selectedCourt?.court_name || 'Seleziona il campo dalla griglia'}</strong></p>
              <p className='mt-1 text-sm text-slate-700'>Orario: <strong>{selectedSlot ? `${selectedSlot.display_start_time} - ${selectedSlot.display_end_time}` : 'Seleziona uno slot libero'}</strong></p>
              <p className='mt-1 text-sm text-slate-700'>Livello: <strong>{formatPlayLevel(levelRequested)}</strong></p>
            </div>

            <button type='submit' className='btn-primary w-full sm:w-auto' disabled={!selectedSlot}>
              Crea nuova partita
            </button>
          </div>
        </div>
      ) : null}
    </form>
  );
}

function findFirstAvailableSelection(groups: CourtAvailability[]) {
  const visibleGroups = groups.map((group) => ({ ...group, slots: group.slots.filter(isSlotWithinOpeningHours) }));

  for (const group of visibleGroups) {
    const firstAvailableSlot = group.slots.find((slot) => slot.available);
    if (firstAvailableSlot) {
      return { courtId: group.court_id, slotId: firstAvailableSlot.slot_id };
    }
  }

  return null;
}

function getDisplayedCourtSlots({
  slots,
  expanded,
  selectedSlotId,
  highlightedSlotIds,
}: {
  slots: TimeSlot[];
  expanded: boolean;
  selectedSlotId: string;
  highlightedSlotIds: string[];
}) {
  if (expanded || slots.length <= COLLAPSED_COURT_SLOT_COUNT) {
    return slots;
  }

  const initialSlots = slots.slice(0, COLLAPSED_COURT_SLOT_COUNT);
  const initialSlotIds = new Set(initialSlots.map((slot) => slot.slot_id));
  const pinnedSlotIds = new Set<string>();

  if (selectedSlotId) {
    pinnedSlotIds.add(selectedSlotId);
  }
  for (const slotId of highlightedSlotIds) {
    pinnedSlotIds.add(slotId);
  }

  const pinnedSlots = slots.filter((slot) => pinnedSlotIds.has(slot.slot_id) && !initialSlotIds.has(slot.slot_id));
  return [...initialSlots, ...pinnedSlots];
}

function buildCollapsedCourtCta({
  slots,
  expanded,
  onExpand,
}: {
  courtId: string;
  slots: TimeSlot[];
  expanded: boolean;
  onExpand: () => void;
}) {
  if (expanded || slots.length <= COLLAPSED_COURT_SLOT_COUNT) {
    return null;
  }

  const initialSlots = slots.slice(0, COLLAPSED_COURT_SLOT_COUNT);
  const hasVisibleAvailableSlots = initialSlots.some((slot) => slot.available);
  const hasHiddenSlots = slots.length > initialSlots.length;

  if (!hasHiddenSlots || hasVisibleAvailableSlots) {
    return null;
  }

  return (
    <button
      type='button'
      className='btn-secondary w-full'
      onClick={onExpand}
      aria-label='Vedi tutti gli orari'
    >
      Vedi tutti gli orari
    </button>
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

function isSlotWithinOpeningHours(slot: TimeSlot) {
  if (slot.start_time < '07:00') {
    return false;
  }

  return slot.end_time === '00:00' || slot.end_time > slot.start_time;
}

function formatSlotCountLabel(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`;
}