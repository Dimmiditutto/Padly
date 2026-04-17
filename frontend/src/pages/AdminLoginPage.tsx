import { ArrowLeft } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { AppBrand } from '../components/AppBrand';
import { loginAdmin } from '../services/adminApi';

const forgotPasswordMailTo = `mailto:info@padelsavona.it?subject=${encodeURIComponent('Recupero password area admin')}&body=${encodeURIComponent('Ciao, ho bisogno di recuperare la password dell\'area admin.')}`;

export function AdminLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      await loginAdmin(email, password);
      navigate('/admin');
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

  return (
    <div className='flex min-h-screen items-center justify-center px-4 py-10'>
      <div className='surface-card w-full max-w-md'>
        <Link to='/' className='btn-secondary inline-flex'>
          <ArrowLeft size={16} /> Torna alla prenotazione
        </Link>
        <AppBrand />
        <p className='mt-5 text-sm font-semibold text-cyan-700'>Area admin</p>
        <h1 className='mt-2 text-3xl font-bold text-slate-950'>Accesso riservato</h1>
        <p className='mt-2 text-sm text-slate-600'>Gestisci prenotazioni, blackout, ricorrenze e report essenziali.</p>

        <form className='mt-6 space-y-4' onSubmit={handleSubmit}>
          <div>
            <label className='field-label' htmlFor='admin-email'>Email</label>
            <input id='admin-email' className='text-input' type='email' value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className='field-label' htmlFor='admin-password'>Password</label>
            <input id='admin-password' className='text-input' type='password' value={password} onChange={(e) => setPassword(e.target.value)} required />
            <div className='mt-2 flex items-center justify-between gap-3'>
              <p className='text-sm text-slate-500'>Nessun cambio password obbligatorio al primo accesso.</p>
              <a href={forgotPasswordMailTo} className='text-sm font-semibold text-cyan-700 underline-offset-4 transition hover:text-cyan-800 hover:underline'>
                Password dimenticata?
              </a>
            </div>
          </div>

          {error ? <AlertBanner tone='error'>{error}</AlertBanner> : null}
          <button type='submit' className='btn-primary w-full' disabled={loading}>{loading ? 'Accesso in corso…' : 'Entra nella dashboard'}</button>
        </form>
      </div>
    </div>
  );
}
