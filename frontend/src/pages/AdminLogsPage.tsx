import { CalendarClock } from 'lucide-react';
import { useEffect, useState } from 'react';
import { AdminNav } from '../components/AdminNav';
import { AlertBanner } from '../components/AlertBanner';
import { EmptyState } from '../components/EmptyState';
import { LoadingBlock } from '../components/LoadingBlock';
import { PageBrandBar } from '../components/PageBrandBar';
import { SectionCard } from '../components/SectionCard';
import { getAdminSession, listAdminEvents, logoutAdmin } from '../services/adminApi';
import type { AdminEvent, AdminSession } from '../types';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';
import { formatDateTime } from '../utils/format';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

function getRequestStatus(error: any) {
  return error?.response?.status;
}

function getRequestMessage(error: any, fallback: string) {
  return error?.response?.data?.detail || fallback;
}

export function AdminLogsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const tenantSlug = getTenantSlugFromSearchParams(searchParams);
  const [session, setSession] = useState<AdminSession | null>(null);
  const [events, setEvents] = useState<AdminEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ tone: 'error'; message: string } | null>(null);

  useEffect(() => {
    void bootstrap();
  }, [tenantSlug]);

  async function bootstrap() {
    setLoading(true);
    setFeedback(null);

    try {
      const sessionResponse = await getAdminSession(tenantSlug);
      setSession(sessionResponse);
      const response = await listAdminEvents();
      setEvents(response);
    } catch (error: any) {
      if (getRequestStatus(error) === 401) {
        navigate(withTenantPath('/admin/login', tenantSlug));
        return;
      }
      setFeedback({ tone: 'error', message: getRequestMessage(error, 'Non riesco a caricare il log admin in questo momento.') });
    } finally {
      setLoading(false);
    }
  }

  async function logout() {
    await logoutAdmin(tenantSlug);
    navigate(withTenantPath('/admin/login', tenantSlug));
  }

  return (
    <div className='min-h-screen px-4 py-6 sm:px-6 lg:px-8'>
      <div className='page-shell space-y-6'>
        <div className='admin-hero-panel space-y-4'>
          <PageBrandBar
            className='mb-2'
            actions={<Link className='admin-hero-button-secondary' to='/'>Torna alla home</Link>}
          />
          <div className='flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between'>
            <div>
              <p className='text-2xl font-semibold text-cyan-100'>Log admin</p>
              <h1 className='text-3xl font-bold'>Traccia operativa recente</h1>
              <p className='mt-2 max-w-2xl text-sm text-slate-300'>Qui trovi gli eventi business recenti di prenotazioni, pagamenti e operazioni amministrative.</p>
            </div>
            <div className='admin-hero-actions'>
              <button className='admin-hero-button-primary' type='button' onClick={() => void bootstrap()}>Aggiorna dashboard</button>
              <button className='admin-hero-button-secondary' type='button' onClick={() => void logout()}>Esci</button>
            </div>
          </div>
          <AdminNav session={session} />
        </div>

        {feedback ? <AlertBanner tone={feedback.tone}>{feedback.message}</AlertBanner> : null}

        <SectionCard title='Eventi recenti' description='Ultimi 100 eventi business registrati dal backend.' elevated>
          {loading ? <LoadingBlock label='Sto caricando il log admin…' /> : null}
          {!loading ? (
            events.length === 0 ? (
              <EmptyState icon={CalendarClock} title='Nessun evento recente' description='I log business compariranno qui dopo le prime operazioni.' />
            ) : (
              <div className='space-y-2'>
                {events.map((event) => (
                  <div key={event.id} className='rounded-2xl bg-slate-50 px-4 py-3 text-sm'>
                    <div className='flex items-center justify-between gap-3'>
                      <span className='font-semibold text-slate-800'>{event.event_type}</span>
                      <span className='text-xs text-slate-500'>{formatDateTime(event.created_at, session?.timezone)}</span>
                    </div>
                    <p className='mt-1 text-slate-600'>{event.message}</p>
                  </div>
                ))}
              </div>
            )
          ) : null}
        </SectionCard>
      </div>
    </div>
  );
}