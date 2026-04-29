import { CalendarCheck2 } from 'lucide-react';
import { EmptyState } from '../EmptyState';
import type { PlayMatchSummary } from '../../types';
import { MatchCard } from './MatchCard';

export function MyMatches({
  matches,
  currentPlayerId,
  onOpen,
  onShare,
  onRotateShareToken,
  onRevokeShareToken,
  onLeave,
  onEdit,
  onCancel,
}: {
  matches: PlayMatchSummary[];
  currentPlayerId: string;
  onOpen: (match: PlayMatchSummary) => void;
  onShare: (match: PlayMatchSummary) => void;
  onRotateShareToken: (match: PlayMatchSummary) => void;
  onRevokeShareToken: (match: PlayMatchSummary) => void;
  onLeave: (match: PlayMatchSummary) => void;
  onEdit: (match: PlayMatchSummary) => void;
  onCancel: (match: PlayMatchSummary) => void;
}) {
  if (matches.length === 0) {
    return (
      <EmptyState
        icon={CalendarCheck2}
        title='Nessuna partita personale attiva'
      />
    );
  }

  return (
    <div className='grid gap-4 xl:grid-cols-2'>
      {matches.map((match) => (
        (() => {
          const extraActions = [];
          const isCreator = match.created_by_player_id === currentPlayerId;
          const canManageOpenMatch = match.status === 'OPEN';
          const hasActiveShareToken = Boolean(match.share_token);

          if (canManageOpenMatch && match.joined_by_current_player) {
            extraActions.push({ label: 'Lascia', onClick: onLeave });
          }
          if (canManageOpenMatch && isCreator) {
            extraActions.push({ label: 'Rigenera link', onClick: onRotateShareToken });
            if (hasActiveShareToken) {
              extraActions.push({ label: 'Disattiva link', onClick: onRevokeShareToken, tone: 'danger' as const });
            }
            extraActions.push({ label: 'Modifica', onClick: onEdit });
            extraActions.push({ label: 'Annulla match', onClick: onCancel, tone: 'danger' as const });
          }

          return (
        <MatchCard
          key={match.id}
          match={match}
          onPrimaryAction={hasActiveShareToken ? onOpen : undefined}
          primaryActionLabel='Apri pagina condivisa'
          onShare={hasActiveShareToken ? onShare : undefined}
          extraActions={extraActions}
          testId='play-my-match-card'
        />
          );
        })()
      ))}
    </div>
  );
}