import { useState, type FormEvent } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { AppBrand } from '../components/AppBrand';
import { acceptCommunityInvite } from '../services/playApi';
import type { CommunityInviteAcceptPayload, PlayPlayerSummary } from '../types';
import { getTenantSlugFromSearchParams, normalizeTenantSlug } from '../utils/tenantContext';
import { PLAY_LEVEL_OPTIONS, buildClubPlayPath } from '../utils/play';

export function InviteAcceptPage() {
  const { clubSlug, token } = useParams();
  const [searchParams] = useSearchParams();
  const tenantSlug = normalizeTenantSlug(clubSlug) || getTenantSlugFromSearchParams(searchParams) || null;
  const [formData, setFormData] = useState<CommunityInviteAcceptPayload>({
    declared_level: 'NO_PREFERENCE',
    privacy_accepted: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: 'success' | 'error'; message: string } | null>(null);
  const [player, setPlayer] = useState<PlayPlayerSummary | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tenantSlug || !token) {
      setFeedback({ tone: 'error', message: 'Link invito non valido per il club corrente.' });
      return;
    }

    if (!formData.privacy_accepted) {
      setFeedback({ tone: 'error', message: 'Per entrare nella community devi accettare la privacy.' });
      return;
    }

    setSubmitting(true);
    setFeedback(null);

    try {
      const response = await acceptCommunityInvite(token, formData, tenantSlug);
      setPlayer(response.player);
      setFeedback({ tone: 'success', message: response.message });
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Non riesco a completare l ingresso community da questo invito.' });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='page-shell max-w-3xl'>
        <div className='rounded-[28px] border border-cyan-400/20 bg-slate-950/80 p-6 text-white shadow-soft'>
          <AppBrand light label='Invite accept' />
          <h1 className='mt-4 text-3xl font-bold tracking-tight text-white'>Ingresso community del club</h1>
          <p className='mt-3 text-sm leading-6 text-slate-300'>Questo link arriva dall invito del club. Qui raccogli il tuo livello dichiarato e il consenso privacy prima di entrare davvero nel modulo `/play`.</p>
        </div>

        <section className='surface-card mt-6'>
          <h2 className='section-title'>Completa il tuo ingresso</h2>
          <p className='mt-2 helper-text'>Nome profilo e telefono arrivano dal token di community gia emesso dal club. In questa fase scegli solo il livello iniziale e confermi la privacy.</p>

          <form className='mt-6 space-y-4' onSubmit={handleSubmit}>
            <div>
              <label className='field-label' htmlFor='invite-declared-level'>Livello dichiarato</label>
              <select
                id='invite-declared-level'
                className='text-input'
                value={formData.declared_level}
                onChange={(event) => setFormData((current) => ({ ...current, declared_level: event.target.value as CommunityInviteAcceptPayload['declared_level'] }))}
              >
                {PLAY_LEVEL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </div>

            <label className='flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700'>
              <input
                className='mt-1 h-4 w-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500'
                type='checkbox'
                checked={formData.privacy_accepted}
                onChange={(event) => setFormData((current) => ({ ...current, privacy_accepted: event.target.checked }))}
              />
              <span>Accetto la privacy per entrare nella community del club e conservare il mio profilo play.</span>
            </label>

            {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

            {player && tenantSlug ? (
              <AlertBanner tone='success'>
                Profilo attivo per <strong>{player.profile_name}</strong>. Ora puoi aprire la bacheca play del club.
              </AlertBanner>
            ) : null}

            <div className='flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between'>
              {tenantSlug ? (
                <Link className='btn-secondary' to={buildClubPlayPath(tenantSlug)}>Vai alla bacheca play</Link>
              ) : null}
              <button type='submit' className='btn-primary' disabled={submitting}>
                {submitting ? 'Conferma in corso…' : 'Entra nella community'}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}