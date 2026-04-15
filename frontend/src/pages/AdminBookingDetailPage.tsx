import { ArrowLeft, CalendarDays, Mail, Phone, WalletCards } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { EmptyState } from '../components/EmptyState';
import { LoadingBlock } from '../components/LoadingBlock';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/StatusBadge';
import { getAdminBooking, getAdminSession, markAdminBalancePaid, updateAdminBookingStatus } from '../services/adminApi';
import type { BookingDetail } from '../types';
import { formatCurrency, formatDateTime } from '../utils/format';

export function AdminBookingDetailPage() {
  const navigate = useNavigate();
  const { bookingId = '' } = useParams();
  const [booking, setBooking] = useState<BookingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    void bootstrap();
  }, [bookingId]);

  async function bootstrap() {
    setLoading(true);
    setError('');
    try {
      await getAdminSession();
      const detail = await getAdminBooking(bookingId);
      setBooking(detail);
    } catch (requestError: any) {
      if (requestError?.response?.status === 401) {
        navigate('/admin/login');
        return;
      }
      setError(requestError?.response?.data?.detail || 'Non riesco a caricare il dettaglio prenotazione.');
    } finally {
      setLoading(false);
    }
  }

  async function updateStatus(status: 'COMPLETED' | 'NO_SHOW' | 'CANCELLED') {
    if (!booking) return;
    setFeedback('');
    try {
      const updated = await updateAdminBookingStatus(booking.id, { status });
      setBooking(updated);
      setFeedback(`Stato aggiornato a ${status}.`);
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Aggiornamento stato non riuscito.');
    }
  }

  async function markBalance() {
    if (!booking) return;
    setFeedback('');
    try {
      const updated = await markAdminBalancePaid(booking.id);
      setBooking(updated);
      setFeedback('Saldo segnato come pagato al campo.');
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Marcatura saldo non riuscita.');
    }
  }

  return (
    <div className='min-h-screen px-4 py-6 sm:px-6 lg:px-8'>
      <div className='page-shell space-y-6'>
        <div className='flex items-center justify-between gap-3'>
          <Link to='/admin' className='btn-secondary'>
            <ArrowLeft size={16} /> Torna alla dashboard
          </Link>
        </div>

        {feedback ? <AlertBanner tone='success'>{feedback}</AlertBanner> : null}
        {error ? <AlertBanner tone='error'>{error}</AlertBanner> : null}

        {loading ? (
          <LoadingBlock label='Sto caricando il dettaglio della prenotazione…' />
        ) : !booking ? (
          <EmptyState icon={CalendarDays} title='Prenotazione non trovata' description='Il dettaglio richiesto non è disponibile o non è più accessibile.' />
        ) : (
          <div className='grid gap-6 xl:grid-cols-[1fr_320px]'>
            <SectionCard
              title='Dettaglio prenotazione'
              description='Controlla dati cliente, stato e riferimenti pagamento.'
              actions={<StatusBadge status={booking.status} />}
              elevated
            >
              <div className='grid gap-4 sm:grid-cols-2'>
                <InfoItem label='Riferimento' value={booking.public_reference} />
                <InfoItem label='Durata' value={`${booking.duration_minutes} minuti`} />
                <InfoItem label='Inizio' value={formatDateTime(booking.start_at)} />
                <InfoItem label='Fine' value={formatDateTime(booking.end_at)} />
                <InfoItem label='Caparra' value={formatCurrency(booking.deposit_amount)} />
                <InfoItem label='Pagamento' value={`${booking.payment_provider} • ${booking.payment_status}`} />
                <InfoItem label='Cliente' value={booking.customer_name || 'Cliente non disponibile'} />
                <InfoItem label='Creata da' value={booking.created_by} />
              </div>
              <div className='mt-5 grid gap-3 sm:grid-cols-2'>
                <ContactItem icon={Mail} label='Email' value={booking.customer_email || '—'} />
                <ContactItem icon={Phone} label='Telefono' value={booking.customer_phone || '—'} />
              </div>
              <div className='mt-5 rounded-[24px] border border-slate-200 bg-slate-50 p-4'>
                <p className='text-sm font-semibold text-slate-900'>Note e riferimenti</p>
                <p className='mt-2 text-sm text-slate-600'>{booking.note || 'Nessuna nota inserita.'}</p>
                <p className='mt-3 text-xs text-slate-500'>Riferimento pagamento: {booking.payment_reference || 'non ancora disponibile'}</p>
              </div>
            </SectionCard>

            <div className='space-y-6'>
              <SectionCard title='Azioni rapide' description='Aggiorna lo stato operativo direttamente da qui.'>
                <div className='space-y-3'>
                  <button className='btn-primary w-full' onClick={() => void markBalance()}>
                    <WalletCards size={16} /> Segna saldo al campo
                  </button>
                  <button className='btn-secondary w-full' onClick={() => void updateStatus('COMPLETED')}>Segna completed</button>
                  <button className='btn-secondary w-full' onClick={() => void updateStatus('NO_SHOW')}>Segna no-show</button>
                  <button className='btn-secondary w-full' onClick={() => void updateStatus('CANCELLED')}>Annulla prenotazione</button>
                </div>
              </SectionCard>

              <SectionCard title='Audit rapido' description='Timestamp principali della prenotazione.'>
                <div className='space-y-3 text-sm text-slate-600'>
                  <p>Creata: <strong>{formatDateTime(booking.created_at)}</strong></p>
                  <p>Saldo al campo: <strong>{booking.balance_paid_at ? formatDateTime(booking.balance_paid_at) : 'non segnato'}</strong></p>
                  <p>Completed: <strong>{booking.completed_at ? formatDateTime(booking.completed_at) : 'non segnato'}</strong></p>
                  <p>No-show: <strong>{booking.no_show_at ? formatDateTime(booking.no_show_at) : 'non segnato'}</strong></p>
                  <p>Annullata: <strong>{booking.cancelled_at ? formatDateTime(booking.cancelled_at) : 'non annullata'}</strong></p>
                </div>
              </SectionCard>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className='surface-muted'>
      <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>{label}</p>
      <p className='mt-2 text-sm font-medium text-slate-900'>{value}</p>
    </div>
  );
}

function ContactItem({ icon: Icon, label, value }: { icon: typeof Mail; label: string; value: string }) {
  return (
    <div className='flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3'>
      <div className='flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-600'>
        <Icon size={16} />
      </div>
      <div>
        <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>{label}</p>
        <p className='text-sm font-medium text-slate-900'>{value}</p>
      </div>
    </div>
  );
}