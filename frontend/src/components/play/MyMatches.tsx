import { CalendarCheck2 } from 'lucide-react';
import { EmptyState } from '../EmptyState';
import type { PlayMatchSummary } from '../../types';
import { MatchCard } from './MatchCard';

export function MyMatches({
  matches,
  onOpen,
  onShare,
}: {
  matches: PlayMatchSummary[];
  onOpen: (match: PlayMatchSummary) => void;
  onShare: (match: PlayMatchSummary) => void;
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
        <MatchCard
          key={match.id}
          match={match}
          onPrimaryAction={onOpen}
          primaryActionLabel='Apri pagina condivisa'
          onShare={onShare}
          testId='play-my-match-card'
        />
      ))}
    </div>
  );
}