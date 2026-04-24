import { CalendarDays, Clock3, Share2, UserPlus, Users } from 'lucide-react';
import type { PlayMatchSummary } from '../../types';
import { formatDate, formatTimeValue } from '../../utils/format';
import { formatPlayLevel } from '../../utils/play';

export function MatchCard({
  match,
  onPrimaryAction,
  primaryActionLabel = 'Unisciti',
  onShare,
  testId = 'play-match-card',
}: {
  match: PlayMatchSummary;
  onPrimaryAction?: (match: PlayMatchSummary) => void;
  primaryActionLabel?: string;
  onShare?: (match: PlayMatchSummary) => void;
  testId?: string;
}) {
  return (
    <article data-testid={testId} className='surface-card-compact flex h-full flex-col gap-4'>
      <div className='flex flex-wrap items-start justify-between gap-3'>
        <div>
          <p className='text-sm font-semibold uppercase tracking-[0.14em] text-slate-500'>Partita aperta</p>
          <h3 className='mt-2 text-xl font-semibold text-slate-950'>
            {match.court_name || 'Campo del club'}
          </h3>
        </div>

        <div className='flex flex-wrap items-center justify-end gap-2'>
          {match.court_badge_label ? <span className='status-pill status-pill-neutral'>{match.court_badge_label}</span> : null}
          {match.joined_by_current_player ? <span className='status-pill status-pill-confirmed'>Sei dentro</span> : null}
          <span className='status-pill status-pill-pending'>{match.participant_count}/4</span>
        </div>
      </div>

      <div className='grid gap-3 sm:grid-cols-2'>
        <div className='surface-muted'>
          <div className='flex items-center gap-2 text-sm font-semibold text-slate-700'>
            <CalendarDays size={16} className='text-cyan-700' />
            <span>Data</span>
          </div>
          <p className='mt-2 text-base font-medium text-slate-950'>{formatDate(match.start_at)}</p>
        </div>

        <div className='surface-muted'>
          <div className='flex items-center gap-2 text-sm font-semibold text-slate-700'>
            <Clock3 size={16} className='text-cyan-700' />
            <span>Orario</span>
          </div>
          <p className='mt-2 text-base font-medium text-slate-950'>
            {formatTimeValue(match.start_at)} - {formatTimeValue(match.end_at)}
          </p>
        </div>
      </div>

      <div className='grid gap-3 md:grid-cols-2'>
        <div>
          <p className='text-sm font-semibold uppercase tracking-[0.14em] text-slate-500'>Livello</p>
          <p className='mt-2 text-base font-medium text-slate-950'>{formatPlayLevel(match.level_requested)}</p>
        </div>
        <div>
          <p className='text-sm font-semibold uppercase tracking-[0.14em] text-slate-500'>Posti mancanti</p>
          <p className='mt-2 text-base font-medium text-slate-950'>{match.available_spots}</p>
        </div>
      </div>

      <div>
        <p className='text-sm font-semibold uppercase tracking-[0.14em] text-slate-500'>Giocatori attuali</p>
        <div className='mt-3 flex flex-wrap gap-2'>
          {match.participants.map((participant) => (
            <span key={participant.player_id} className='inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700'>
              <Users size={14} className='text-cyan-700' />
              <span>{participant.profile_name}</span>
            </span>
          ))}
        </div>
      </div>

      {match.note ? (
        <div className='rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3'>
          <p className='text-sm font-semibold uppercase tracking-[0.14em] text-slate-500'>Nota</p>
          <p className='mt-2 text-sm leading-6 text-slate-700'>{match.note}</p>
        </div>
      ) : null}

      <div className='mt-auto flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between'>
        <p className='text-sm text-slate-600'>Creata da {match.creator_profile_name || 'community del club'}</p>
        <div className='flex flex-col gap-3 sm:flex-row'>
          {onShare ? (
            <button type='button' className='btn-secondary' onClick={() => onShare(match)}>
              <Share2 size={16} />
              <span>Condividi</span>
            </button>
          ) : null}
          {onPrimaryAction ? (
            <button type='button' className='btn-primary' onClick={() => onPrimaryAction(match)}>
              <UserPlus size={16} />
              <span>{primaryActionLabel}</span>
            </button>
          ) : null}
        </div>
      </div>
    </article>
  );
}