import { ExternalLink, MessageCircle, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { AlertBanner } from '../AlertBanner';

type ShareDialogFeedback = { tone: 'info' | 'success' | 'error'; message: string } | null;

export function PlayShareDialog({
  open,
  title,
  description,
  shareUrl,
  shareText,
  whatsAppUrl,
  onClose,
}: {
  open: boolean;
  title: string;
  description: string;
  shareUrl: string;
  shareText: string;
  whatsAppUrl: string;
  onClose: () => void;
}) {
  const [feedback, setFeedback] = useState<ShareDialogFeedback>(null);
  const whatsAppLinkLabel = whatsAppUrl.includes('web.whatsapp.com') ? 'Apri WhatsApp Web' : 'Apri link WhatsApp';

  useEffect(() => {
    if (open) {
      setFeedback(null);
    }
  }, [open, shareText, shareUrl, whatsAppUrl]);

  if (!open) {
    return null;
  }

  async function handleCopyLink() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setFeedback({ tone: 'success', message: 'Link partita copiato negli appunti.' });
    } catch {
      setFeedback({ tone: 'info', message: 'Copia manualmente il link qui sotto.' });
    }
  }

  function handleOpenWhatsApp() {
    if (typeof window !== 'undefined') {
      window.open(whatsAppUrl, '_blank', 'noopener,noreferrer');
    }
    setFeedback({ tone: 'info', message: 'WhatsApp aperto con il testo gia pronto.' });
  }

  return (
    <div
      className='fixed inset-0 z-50 flex items-end justify-center bg-slate-950/55 p-4 sm:items-center'
      role='presentation'
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        role='dialog'
        aria-modal='true'
        aria-label={title}
        className='w-full max-w-2xl rounded-[28px] border border-slate-200 bg-white p-5 shadow-soft sm:p-6'
      >
        <div className='flex items-start justify-between gap-4'>
          <div>
            <p className='text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700'>Condivisione match</p>
            <h2 className='mt-2 text-2xl font-semibold text-slate-950'>{title}</h2>
            <p className='mt-2 text-sm leading-6 text-slate-600'>{description}</p>
          </div>
          <button type='button' className='btn-secondary sm:w-auto' onClick={onClose} aria-label='Chiudi condivisione match'>
            <X size={16} />
          </button>
        </div>

        <div className='mt-5 space-y-4'>
          {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

          <div className='grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-end'>
            <div>
              <label className='field-label' htmlFor='play-share-dialog-link'>Link partita</label>
              <input id='play-share-dialog-link' className='text-input' readOnly value={shareUrl} />
            </div>
            <button type='button' className='btn-secondary sm:w-auto' onClick={() => void handleCopyLink()}>
              Copia link
            </button>
            <button type='button' className='btn-primary sm:w-auto' onClick={handleOpenWhatsApp}>
              <MessageCircle size={16} />
              <span>Apri WhatsApp</span>
            </button>
          </div>

          <div>
            <label className='field-label' htmlFor='play-share-dialog-text'>Testo WhatsApp</label>
            <textarea
              id='play-share-dialog-text'
              className='text-input min-h-40 resize-y'
              readOnly
              value={shareText}
            />
          </div>

          <div className='flex justify-end'>
            <a className='btn-secondary sm:w-auto' href={whatsAppUrl} target='_blank' rel='noreferrer'>
              <ExternalLink size={16} />
              <span>{whatsAppLinkLabel}</span>
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}