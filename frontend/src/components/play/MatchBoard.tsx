import { Users } from 'lucide-react';
import { EmptyState } from '../EmptyState';
import type { PlayMatchSummary } from '../../types';
import { MatchCard } from './MatchCard';

export function MatchBoard({
  matches,
  onJoin,
  onShare,
}: {
  matches: PlayMatchSummary[];
  onJoin: (match: PlayMatchSummary) => void;
  onShare: (match: PlayMatchSummary) => void;
}) {
  if (matches.length === 0) {
    return (
      <EmptyState
        icon={Users}
        title='Nessuna partita aperta in questo momento'
        description=''
      />
    );
  }

  return (
    <div className='grid gap-4 xl:grid-cols-2'>
      {matches.map((match) => (
        <MatchCard key={match.id} match={match} onPrimaryAction={onJoin} onShare={onShare} testId='play-open-match-card' />
      ))}
    </div>
  );
}