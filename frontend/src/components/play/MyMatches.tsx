import { CalendarCheck2 } from 'lucide-react';
import { EmptyState } from '../EmptyState';
import type { PlayMatchSummary } from '../../types';
import { MatchCard } from './MatchCard';

export function MyMatches({
  matches,
  currentPlayerId,
  onOpen,
  onShare,
  onLeave,
  onEdit,
  onCancel,
}: {
  matches: PlayMatchSummary[];
  currentPlayerId: string;
  onOpen: (match: PlayMatchSummary) => void;
  onShare: (match: PlayMatchSummary) => void;
  onLeave: (match: PlayMatchSummary) => void;
  onEdit: (match: PlayMatchSummary) => void;
  onCancel: (match: PlayMatchSummary) => void;
}) {
  if (matches.length === 0) {
    return (
      <EmptyState
        icon={CalendarCheck2}
        title='Nessuna partita personale attiva'
        description='Dopo il riconoscimento vedrai qui le partite future che hai creato o a cui partecipi.'
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

          if (canManageOpenMatch && match.joined_by_current_player) {
            extraActions.push({ label: 'Lascia', onClick: onLeave });
          }
          if (canManageOpenMatch && isCreator) {
            extraActions.push({ label: 'Modifica', onClick: onEdit });
            extraActions.push({ label: 'Annulla match', onClick: onCancel, tone: 'danger' as const });
          }

          return (
        <MatchCard
          key={match.id}
          match={match}
          onPrimaryAction={onOpen}
          primaryActionLabel='Apri pagina condivisa'
          onShare={onShare}
          extraActions={extraActions}
          testId='play-my-match-card'
        />
          );
        })()
      ))}
    </div>
  );
}