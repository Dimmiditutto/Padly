import { ArrowLeft } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { PageBrandBar } from '../components/PageBrandBar';
import { loginAdmin, requestAdminPasswordReset } from '../services/adminApi';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';

export function AdminLoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const tenantSlug = getTenantSlugFromSearchParams(searchParams);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'success'; message: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [requestingReset, setRequestingReset] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();
    setLoading(true);
    setError('');
    setFeedback(null);
    try {
      await loginAdmin(normalizedEmail, password, tenantSlug);
      navigate(withTenantPath('/admin', tenantSlug));
    } catch (requestError: any) {
      if (!requestError?.response) {
        setError('Backend non raggiungibile. Avvia il server e riprova.');
      } else {
        setError(requestError?.response?.data?.detail || 'Credenziali non valide.');
      }
    } finally {
      setLoading(false);
    }
  }

  async function handlePasswordResetRequest() {
    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail) {
      setFeedback(null);
      setError("Inserisci l'email admin per ricevere il link di reset.");
      return;
    }

    setRequestingReset(true);
    setError('');
    setFeedback(null);

    try {
      const response = await requestAdminPasswordReset(normalizedEmail, tenantSlug);
      setFeedback({ tone: 'info', message: response.message });
    } catch (requestError: any) {
      if (!requestError?.response) {
        setError('Backend non raggiungibile. Avvia il server e riprova.');
      } else {
        setError(requestError?.response?.data?.detail || 'Non riesco ad avviare il recupero password.');
      }
    } finally {
      setRequestingReset(false);
    }
  }

  return (
    <div className='flex min-h-screen items-center justify-center px-4 py-10'>
      <div className='surface-card w-full max-w-md'>
        <PageBrandBar
          className='mb-5'
          actions={(
            <>
              <Link to={withTenantPath('/booking', tenantSlug)} className='btn-secondary inline-flex'>
                <ArrowLeft size={16} /> Torna alla prenotazione
              </Link>
              <Link to='/' className='btn-secondary inline-flex'>Torna alla home</Link>
            </>
          )}
        />
        <p className='mt-5 text-sm font-semibold text-cyan-700'>Area admin</p>
        <h1 className='mt-2 text-3xl font-bold text-slate-950'>Accesso riservato</h1>

        <form className='mt-6 space-y-4' onSubmit={handleSubmit}>
          <div>
            <label className='field-label' htmlFor='admin-email'>Email</label>
            <input id='admin-email' className='text-input' type='email' value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className='field-label' htmlFor='admin-password'>Password</label>
            <input id='admin-password' className='text-input' type='password' value={password} onChange={(e) => setPassword(e.target.value)} required />
            <div className='surface-muted mt-4 space-y-3'>
              <p className='text-sm text-slate-500'>Usa l'email admin per ricevere un link di reset.</p>
              <button
                type='button'
                onClick={() => void handlePasswordResetRequest()}
                className='btn-secondary w-full justify-center disabled:cursor-not-allowed disabled:opacity-60'
                disabled={loading || requestingReset}
              >
                {requestingReset ? 'Invio link…' : 'Password dimenticata?'}
              </button>
            </div>
          </div>

          {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}
          {error ? <AlertBanner tone='error'>{error}</AlertBanner> : null}
          <button type='submit' className='btn-primary w-full' disabled={loading}>{loading ? 'Accesso in corso…' : 'Entra nella dashboard'}</button>
        </form>
      </div>
    </div>
  );
}
