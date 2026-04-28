import { useParams } from 'react-router-dom';
import { PlayAccessPage } from './PlayAccessPage';

export function InviteAcceptPage() {
  const { token } = useParams();
  return <PlayAccessPage inviteToken={token || null} />;
}