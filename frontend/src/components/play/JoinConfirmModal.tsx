import { X } from 'lucide-react';
import { type FormEvent, useEffect, useState } from 'react';
import { AlertBanner } from '../AlertBanner';
import { identifyPlayPlayer } from '../../services/playApi';
import type { PlayIdentifyPayload, PlayPlayerSummary } from '../../types';
import { PLAY_LEVEL_OPTIONS } from '../../utils/play';

export function JoinConfirmModal({
  open,
  tenantSlug,
  title,
  description,
  onClose,
  onSuccess,
}: {
  open: boolean;
  tenantSlug: string;
  title: string;
  description: string;
  onClose: () => void;
  onSuccess: (player: PlayPlayerSummary) => void;
}) {
  const [formData, setFormData] = useState<PlayIdentifyPayload>({
    profile_name: '',
    phone: '',
    declared_level: 'NO_PREFERENCE',
    privacy_accepted: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    setSubmitting(false);
    setFeedback(null);
    setFormData({
      profile_name: '',
      phone: '',
      declared_level: 'NO_PREFERENCE',
      privacy_accepted: false,
    });
  }, [open]);

  if (!open) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setFeedback(null);

    try {
      const response = await identifyPlayPlayer(formData, tenantSlug);
      onSuccess(response.player);
    } catch (error: any) {
      setFeedback(error?.response?.data?.detail || 'Non riesco a completare il riconoscimento del profilo play.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className='fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm'>
      <div className='surface-card w-full max-w-xl'>
        <div className='flex items-start justify-between gap-4'>
          <div>
            <p className='text-sm font-semibold uppercase tracking-[0.16em] text-slate-500'>Profilo play</p>
            <h2 className='mt-2 text-2xl font-bold text-slate-950'>{title}</h2>
            <p className='mt-2 text-sm leading-6 text-slate-600'>{description}</p>
          </div>
          <button type='button' className='btn-pill-secondary' aria-label='Chiudi riconoscimento play' onClick={onClose}>
            <X size={16} />
            <span>Chiudi</span>
          </button>
        </div>

        <form className='mt-6 space-y-4' onSubmit={handleSubmit}>
          <div className='grid gap-4 md:grid-cols-2'>
            <div>
              <label className='field-label' htmlFor='play-profile-name'>Nome profilo</label>
              <input
                id='play-profile-name'
                className='text-input'
                type='text'
                value={formData.profile_name}
                onChange={(event) => setFormData((current) => ({ ...current, profile_name: event.target.value }))}
                placeholder='Es. Luca Smash'
                required
              />
            </div>

            <div>
              <label className='field-label' htmlFor='play-profile-phone'>Telefono</label>
              <input
                id='play-profile-phone'
                className='text-input'
                type='tel'
                value={formData.phone}
                onChange={(event) => setFormData((current) => ({ ...current, phone: event.target.value }))}
                placeholder='Es. +39 333 1234567'
                required
              />
            </div>
          </div>

          <div>
            <label className='field-label' htmlFor='play-profile-level'>Livello</label>
            <select
              id='play-profile-level'
              className='text-input'
              value={formData.declared_level}
              onChange={(event) => setFormData((current) => ({ ...current, declared_level: event.target.value as PlayIdentifyPayload['declared_level'] }))}
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
            <span>Accetto la privacy per essere riconosciuto nel club e usare il modulo play.</span>
          </label>

          {feedback ? <AlertBanner tone='error'>{feedback}</AlertBanner> : null}

          <div className='flex flex-col gap-3 sm:flex-row sm:justify-end'>
            <button type='button' className='btn-secondary' onClick={onClose}>Annulla</button>
            <button type='submit' className='btn-primary' disabled={submitting}>
              {submitting ? 'Salvataggio profilo…' : 'Conferma profilo'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}