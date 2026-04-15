import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

export function AdminLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('admin@padelbooking.app');
  const [password, setPassword] = useState('ChangeMe123!');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.post('/admin/auth/login', { email, password });
      navigate('/admin');
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Credenziali non valide.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className='flex min-h-screen items-center justify-center px-4 py-10'>
      <div className='surface-card w-full max-w-md'>
        <p className='text-sm font-semibold text-cyan-700'>Area admin</p>
        <h1 className='mt-2 text-3xl font-bold text-slate-950'>Accesso riservato</h1>
        <p className='mt-2 text-sm text-slate-600'>Gestisci prenotazioni, blackout, ricorrenze e report essenziali.</p>

        <form className='mt-6 space-y-4' onSubmit={handleSubmit}>
          <div>
            <label className='field-label'>Email</label>
            <input className='text-input' type='email' value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className='field-label'>Password</label>
            <input className='text-input' type='password' value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>

          {error && <div className='rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700'>{error}</div>}
          <button type='submit' className='btn-primary w-full' disabled={loading}>{loading ? 'Accesso in corso…' : 'Entra nella dashboard'}</button>
        </form>
      </div>
    </div>
  );
}
