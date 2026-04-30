import { ArrowLeft } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { PageBrandBar } from '../components/PageBrandBar';
import { confirmAdminPasswordReset } from '../services/adminApi';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';

export function AdminPasswordResetPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token')?.trim() || '';
  const tenantSlug = getTenantSlugFromSearchParams(searchParams);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token) {
      setSuccessMessage('');
      setError('Link di reset non valido o mancante.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setSuccessMessage('');
      setError('Le password non coincidono.');
      return;
    }

    setLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      const response = await confirmAdminPasswordReset(token, newPassword, tenantSlug);
      setSuccessMessage(response.message);
      setNewPassword('');
      setConfirmPassword('');
    } catch (requestError: any) {
      if (!requestError?.response) {
        setError('Backend non raggiungibile. Avvia il server e riprova.');
      } else {
        setError(requestError?.response?.data?.detail || 'Non riesco a reimpostare la password.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className='flex min-h-screen items-center justify-center px-4 py-10'>
      <div className='surface-card w-full max-w-md'>
        <PageBrandBar
          className='mb-5'
          actions={(
            <>
              <Link to={withTenantPath('/admin/login', tenantSlug)} className='btn-secondary inline-flex'>
                <ArrowLeft size={16} /> Torna al login
              </Link>
              <Link to='/' className='btn-secondary inline-flex'>Torna alla home</Link>
            </>
          )}
        />
        <p className='mt-5 text-sm font-semibold text-cyan-700'>Reset password</p>
        <h1 className='mt-2 text-3xl font-bold text-slate-950'>Reimposta accesso admin</h1>
        <p className='mt-2 text-sm text-slate-600'>Inserisci una nuova password per l'area admin. Il link ricevuto via email resta valido per un tempo limitato.</p>

        {!token ? <div className='mt-6'><AlertBanner tone='error'>Link di reset non valido o mancante.</AlertBanner></div> : null}

        <form className='mt-6 space-y-4' onSubmit={handleSubmit}>
          <div>
            <label className='field-label' htmlFor='admin-reset-password'>Nuova password</label>
            <input
              id='admin-reset-password'
              className='text-input'
              type='password'
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              minLength={8}
              required
            />
          </div>
          <div>
            <label className='field-label' htmlFor='admin-reset-password-confirm'>Conferma nuova password</label>
            <input
              id='admin-reset-password-confirm'
              className='text-input'
              type='password'
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              minLength={8}
              required
            />
          </div>

          {successMessage ? <AlertBanner tone='success'>{successMessage}</AlertBanner> : null}
          {error ? <AlertBanner tone='error'>{error}</AlertBanner> : null}

          <button className='btn-primary w-full' type='submit' disabled={loading || !token}>
            {loading ? 'Aggiornamento in corso…' : 'Salva nuova password'}
          </button>
        </form>
      </div>
    </div>
  );
}