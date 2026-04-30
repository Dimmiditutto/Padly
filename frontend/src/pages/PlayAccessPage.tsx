import { ArrowLeft, KeyRound, Mail, ShieldCheck, UserRound, UsersRound } from 'lucide-react';
import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { LoadingBlock } from '../components/LoadingBlock';
import { PageBrandBar } from '../components/PageBrandBar';
import { CommunityMatchinnBrand } from '../components/play/CommunityMatchinnBrand';
import { getPublicConfig } from '../services/publicApi';
import { getPlaySession, resendPlayAccessOtp, startPlayAccessOtp, verifyPlayAccessOtp } from '../services/playApi';
import type { PlayAccessPurpose, PlayAccessStartPayload, PlayAccessStartResponse, PlayPlayerSummary, PublicConfig } from '../types';
import { getTenantSlugFromSearchParams, normalizeTenantSlug, withTenantPath } from '../utils/tenantContext';
import { buildClubPlayPath, buildPlayAccessPath, PLAY_LEVEL_OPTIONS, rememberClubPublicName, resolveClubDisplayName } from '../utils/play';

type FeedbackTone = 'success' | 'error' | 'warning' | 'info';
type FeedbackState = { tone: FeedbackTone; message: string } | null;
type AccessFormState = {
  profile_name: string;
  phone: string;
  email: string;
  declared_level: PlayAccessStartPayload['declared_level'];
  privacy_accepted: boolean;
};

const defaultFormState: AccessFormState = {
  profile_name: '',
  phone: '',
  email: '',
  declared_level: 'NO_PREFERENCE',
  privacy_accepted: false,
};

function resolveSafeRedirect(candidate: string | null, fallbackPath: string) {
  if (candidate && candidate.startsWith('/')) {
    return candidate;
  }
  return fallbackPath;
}

function formatExpiryLabel(value: string) {
  return new Date(value).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
}

export function PlayAccessPage({ inviteToken: inviteTokenProp = null }: { inviteToken?: string | null }) {
  const { clubSlug, groupToken: routeGroupToken } = useParams();
  const [searchParams] = useSearchParams();
  const tenantSlug = normalizeTenantSlug(clubSlug) || getTenantSlugFromSearchParams(searchParams) || null;
  const inviteToken = inviteTokenProp;
  const groupToken = routeGroupToken || null;
  const [mode, setMode] = useState<PlayAccessPurpose>(inviteToken ? 'INVITE' : groupToken ? 'GROUP' : 'RECOVERY');
  const [loading, setLoading] = useState(true);
  const [surfaceError, setSurfaceError] = useState<FeedbackState>(null);
  const [feedback, setFeedback] = useState<FeedbackState>(null);
  const [currentPlayer, setCurrentPlayer] = useState<PlayPlayerSummary | null>(null);
  const [publicConfig, setPublicConfig] = useState<PublicConfig | null>(null);
  const [formState, setFormState] = useState<AccessFormState>(defaultFormState);
  const [challenge, setChallenge] = useState<PlayAccessStartResponse | null>(null);
  const [otpCode, setOtpCode] = useState('');
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [resending, setResending] = useState(false);

  useEffect(() => {
    setMode(inviteToken ? 'INVITE' : groupToken ? 'GROUP' : 'RECOVERY');
    setChallenge(null);
    setOtpCode('');
    setFeedback(null);
  }, [groupToken, inviteToken]);

  useEffect(() => {
    let cancelled = false;

    if (!tenantSlug) {
      setLoading(false);
      setSurfaceError({ tone: 'error', message: 'Club community non valido. Apri la pagina da un club specifico.' });
      return () => {
        cancelled = true;
      };
    }

    setLoading(true);
    setSurfaceError(null);
    setPublicConfig((prev) => prev?.tenant_slug === tenantSlug ? prev : null);

    void Promise.all([
      getPlaySession(tenantSlug).catch(() => ({ player: null, notification_settings: null })),
      getPublicConfig(tenantSlug).catch(() => null),
    ])
      .then(([session, config]) => {
        if (cancelled) {
          return;
        }
        setCurrentPlayer(session.player || null);
        if (config) {
          rememberClubPublicName(tenantSlug, config.public_name);
        }
        setPublicConfig(config);
      })
      .catch(() => {
        if (!cancelled) {
          setSurfaceError({ tone: 'error', message: 'Non riesco a caricare la pagina accesso community del club.' });
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [tenantSlug]);

  const clubDisplayName = useMemo(() => {
    if (!tenantSlug) {
      return null;
    }
    return resolveClubDisplayName(tenantSlug, publicConfig?.public_name);
  }, [publicConfig?.public_name, tenantSlug]);

  const playPath = tenantSlug ? buildClubPlayPath(tenantSlug) : '/play';
  const bookingPath = withTenantPath('/booking', tenantSlug);
  const currentAccessPath = tenantSlug ? buildPlayAccessPath(tenantSlug, groupToken) : '/play/access';
  const redirectPath = resolveSafeRedirect(searchParams.get('redirect'), playPath);
  const isOtpLockout = feedback?.tone === 'warning';
  const isGenericAccess = !inviteToken && !groupToken;
  const title = inviteToken
    ? 'Completa il tuo invito community'
    : groupToken
      ? 'Entra dal link condiviso'
      : 'Entra o rientra nella community';
  const intro = inviteToken
    ? 'Il club ti ha inviato un accesso personale. Conferma la tua email e verifica il codice OTP per attivare il profilo Matchinn.'
    : groupToken
      ? 'Questo link puo essere condiviso in un gruppo. Ogni persona entra con dati individuali e riceve il proprio codice via email.'
      : 'Usa la tua email per rientrare nella community oppure completa il primo accesso con nome, telefono, livello e verifica OTP.';

  async function handleStart(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tenantSlug) {
      setFeedback({ tone: 'error', message: 'Club community non valido.' });
      return;
    }

    if (!formState.email.trim()) {
      setFeedback({ tone: 'error', message: 'Inserisci una email valida per ricevere il codice di accesso.' });
      return;
    }
    if (mode !== 'RECOVERY' && !formState.privacy_accepted) {
      setFeedback({ tone: 'error', message: 'Per entrare nella community devi accettare la privacy.' });
      return;
    }
    if ((mode === 'DIRECT' || mode === 'GROUP') && (!formState.profile_name.trim() || !formState.phone.trim())) {
      setFeedback({ tone: 'error', message: 'Completa nome, telefono ed email prima di continuare.' });
      return;
    }

    const payload: PlayAccessStartPayload = {
      purpose: mode,
      email: formState.email.trim(),
      declared_level: formState.declared_level,
      privacy_accepted: formState.privacy_accepted,
    };

    if (mode === 'DIRECT' || mode === 'GROUP') {
      payload.profile_name = formState.profile_name;
      payload.phone = formState.phone;
    }
    if (mode === 'INVITE') {
      payload.invite_token = inviteToken;
    }
    if (mode === 'GROUP') {
      payload.group_token = groupToken;
    }

    setSending(true);
    setFeedback(null);
    try {
      const response = await startPlayAccessOtp(payload, tenantSlug);
      setChallenge(response);
      setOtpCode('');
      setFeedback({ tone: 'success', message: response.message });
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Non riesco a inviare il codice di accesso in questo momento.' });
    } finally {
      setSending(false);
    }
  }

  async function handleVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tenantSlug || !challenge) {
      setFeedback({ tone: 'error', message: 'Richiesta OTP non valida.' });
      return;
    }

    setVerifying(true);
    setFeedback(null);
    try {
      const response = await verifyPlayAccessOtp({ challenge_id: challenge.challenge_id, otp_code: otpCode }, tenantSlug);
      setCurrentPlayer(response.player);
      setFeedback({ tone: 'success', message: response.message });
      if (typeof window !== 'undefined') {
        window.location.assign(redirectPath);
      }
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      if (detail === 'Troppi tentativi. Richiedi un nuovo codice') {
        setOtpCode('');
        setFeedback({
          tone: 'warning',
          message: 'Hai esaurito i tentativi per questo codice. Richiedine uno nuovo e usa solo l’ultimo OTP ricevuto via email.',
        });
      } else {
        setFeedback({ tone: 'error', message: detail || 'Non riesco a verificare il codice OTP.' });
      }
    } finally {
      setVerifying(false);
    }
  }

  async function handleResend() {
    if (!tenantSlug || !challenge) {
      return;
    }

    setResending(true);
    setFeedback(null);
    try {
      const response = await resendPlayAccessOtp(challenge.challenge_id, tenantSlug);
      setChallenge(response);
      setOtpCode('');
      setFeedback({ tone: 'success', message: response.message });
    } catch (error: any) {
      setFeedback({ tone: 'error', message: error?.response?.data?.detail || 'Non riesco a reinviare il codice OTP.' });
    } finally {
      setResending(false);
    }
  }

  return (
    <div className='min-h-screen text-slate-900'>
      <div className='page-shell max-w-4xl'>
        <header className='product-hero-panel'>
          <PageBrandBar
            className='mb-6'
            actions={(
              <>
                <Link className='hero-action-secondary' to={bookingPath}>
                  <ArrowLeft size={16} />
                  <span>Torna al booking</span>
                </Link>
                <Link className='hero-action-secondary' to='/'>
                  <span>Torna alla home</span>
                </Link>
              </>
            )}
          />
          <div className='product-hero-layout'>
            <div className='product-hero-copy'>
              <CommunityMatchinnBrand clubName={clubDisplayName} />
              <h1 className='mt-4 text-3xl font-bold tracking-tight text-white sm:text-4xl'>{title}</h1>
              <p className='product-hero-description'>{intro}</p>
            </div>

            <div className='product-hero-actions'>
              <Link className='hero-action-secondary' to={currentAccessPath}>
                <KeyRound size={16} />
                <span>Ricomincia accesso</span>
              </Link>
            </div>
          </div>

          <div className='product-info-grid'>
            <div className='product-info-card'>
              <Mail size={16} className='mb-2 text-cyan-200' />
              OTP via email integrata con l’infrastruttura del club.
            </div>
            <div className='product-info-card'>
              <ShieldCheck size={16} className='mb-2 text-cyan-200' />
              La sessione Matchinn nasce solo dopo la verifica del codice.
            </div>
            <div className='product-info-card'>
              <UsersRound size={16} className='mb-2 text-cyan-200' />
              Ogni persona mantiene un accesso individuale anche da link condivisi.
            </div>
          </div>
        </header>

        <div className='mt-6 space-y-6'>
          {surfaceError ? <AlertBanner tone={surfaceError.tone}>{surfaceError.message}</AlertBanner> : null}
          {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

          {loading ? (
            <LoadingBlock label='Carico l’accesso community del club…' labelClassName='text-base' />
          ) : currentPlayer ? (
            <section className='surface-card'>
              <h2 className='section-title'>Profilo gia attivo</h2>
              <div className='mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900'>
                Sei gia dentro come <strong>{currentPlayer.profile_name}</strong>. Puoi tornare subito a Partite aperte oppure rientrare dalla home booking del club.
              </div>
              <div className='mt-6 flex flex-col gap-3 sm:flex-row'>
                <Link className='btn-primary' to={playPath}>Apri Partite aperte</Link>
                <Link className='btn-secondary' to={bookingPath}>Vai alla home prenotazioni</Link>
              </div>
            </section>
          ) : (
            <>
              {isGenericAccess ? (
                <section className='surface-card'>
                  <h2 className='section-title'>Come vuoi entrare?</h2>
                  <div className='mt-4 grid gap-3 sm:grid-cols-2'>
                    <button
                      type='button'
                      className={`${mode === 'RECOVERY' ? 'selection-card selection-card-active' : 'selection-card'} inline-flex w-full items-center justify-center gap-2 font-semibold`}
                      onClick={() => {
                        setMode('RECOVERY');
                        setChallenge(null);
                        setOtpCode('');
                        setFeedback(null);
                      }}
                    >
                      <Mail size={16} />
                      <span>Ho gia un profilo</span>
                    </button>
                    <button
                      type='button'
                      className={`${mode === 'DIRECT' ? 'selection-card selection-card-active' : 'selection-card'} inline-flex w-full items-center justify-center gap-2 font-semibold`}
                      onClick={() => {
                        setMode('DIRECT');
                        setChallenge(null);
                        setOtpCode('');
                        setFeedback(null);
                      }}
                    >
                      <UserRound size={16} />
                      <span>Primo accesso</span>
                    </button>
                  </div>
                </section>
              ) : null}

              <section className='surface-card'>
                <h2 className='section-title'>{challenge ? 'Verifica il codice OTP' : 'Richiedi il codice di accesso'}</h2>
                <p className='mt-2 helper-text'>
                  {challenge
                    ? `Abbiamo inviato il codice a ${challenge.email_hint}. Scade alle ${formatExpiryLabel(challenge.expires_at)}.`
                    : mode === 'RECOVERY'
                      ? 'Inserisci l’email usata in community. Se il profilo esiste sul club corrente, riceverai un codice OTP.'
                      : 'Completa i dati richiesti e ricevi un codice OTP personale via email.'}
                </p>

                {challenge ? (
                  <form className='mt-6 space-y-4' onSubmit={handleVerify}>
                    <div>
                      <label className='field-label' htmlFor='play-access-otp-code'>Codice OTP</label>
                      <input
                        id='play-access-otp-code'
                        className='text-input text-center text-xl tracking-[0.3em]'
                        inputMode='numeric'
                        autoComplete='one-time-code'
                        maxLength={6}
                        value={otpCode}
                        onChange={(event) => setOtpCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                      />
                    </div>

                    <div className='rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700'>
                      {isOtpLockout
                        ? 'Questo codice non e piu valido. Richiedine uno nuovo e inserisci solo l’ultimo OTP ricevuto via email.'
                        : 'Il codice resta valido per pochi minuti e apre la sessione community solo dopo verifica corretta.'}
                    </div>

                    <div className='action-cluster'>
                      <button type='submit' className='btn-primary' disabled={verifying || otpCode.length !== 6}>
                        {verifying ? 'Verifica in corso…' : 'Verifica e accedi'}
                      </button>
                      <button type='button' className='btn-secondary' disabled={resending} onClick={() => void handleResend()}>
                        {resending ? 'Reinvio in corso…' : 'Invia un nuovo codice'}
                      </button>
                      <button
                        type='button'
                        className='btn-secondary'
                        onClick={() => {
                          setChallenge(null);
                          setOtpCode('');
                          setFeedback(null);
                        }}
                      >
                        Cambia email o dati
                      </button>
                    </div>
                  </form>
                ) : (
                  <form className='mt-6 space-y-4' onSubmit={handleStart}>
                    {(mode === 'DIRECT' || mode === 'GROUP') ? (
                      <div className='grid gap-4 sm:grid-cols-2'>
                        <div>
                          <label className='field-label' htmlFor='play-access-name'>Nome profilo</label>
                          <input
                            id='play-access-name'
                            className='text-input'
                            value={formState.profile_name}
                            onChange={(event) => setFormState((current) => ({ ...current, profile_name: event.target.value }))}
                          />
                        </div>
                        <div>
                          <label className='field-label' htmlFor='play-access-phone'>Telefono</label>
                          <input
                            id='play-access-phone'
                            className='text-input'
                            inputMode='tel'
                            value={formState.phone}
                            onChange={(event) => setFormState((current) => ({ ...current, phone: event.target.value }))}
                          />
                        </div>
                      </div>
                    ) : null}

                    <div className='grid gap-4 sm:grid-cols-2'>
                      <div>
                        <label className='field-label' htmlFor='play-access-email'>Email</label>
                        <input
                          id='play-access-email'
                          className='text-input'
                          inputMode='email'
                          autoComplete='email'
                          value={formState.email}
                          onChange={(event) => setFormState((current) => ({ ...current, email: event.target.value }))}
                        />
                      </div>
                      {mode !== 'RECOVERY' ? (
                        <div>
                          <label className='field-label' htmlFor='play-access-level'>Livello dichiarato</label>
                          <select
                            id='play-access-level'
                            className='text-input'
                            value={formState.declared_level}
                            onChange={(event) => setFormState((current) => ({ ...current, declared_level: event.target.value as AccessFormState['declared_level'] }))}
                          >
                            {PLAY_LEVEL_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>{option.label}</option>
                            ))}
                          </select>
                        </div>
                      ) : null}
                    </div>

                    {mode !== 'RECOVERY' ? (
                      <label className='flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700'>
                        <input
                          className='mt-1 h-4 w-4 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500'
                          type='checkbox'
                          checked={formState.privacy_accepted}
                          onChange={(event) => setFormState((current) => ({ ...current, privacy_accepted: event.target.checked }))}
                        />
                        <span>Accetto la privacy per attivare o recuperare il mio profilo community su Matchinn.</span>
                      </label>
                    ) : null}

                    <div className='action-cluster sm:justify-between'>
                      <Link className='btn-secondary' to={playPath}>Vai a Partite aperte</Link>
                      <button type='submit' className='btn-primary' disabled={sending}>
                        {sending ? 'Invio in corso…' : 'Invia codice OTP'}
                      </button>
                    </div>
                  </form>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}