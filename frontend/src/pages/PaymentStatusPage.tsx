import { AlertTriangle, CircleX, LoaderCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import type { BookingSummary } from '../types';

export function PaymentStatusPage({ variant }: { variant: 'success' | 'cancelled' | 'error' }) {
  const [searchParams] = useSearchParams();
  const bookingRef = searchParams.get('booking');
  const [booking, setBooking] = useState<BookingSummary | null>(null);
  const [loading, setLoading] = useState(Boolean(bookingRef));

  useEffect(() => {
    if (!bookingRef) return;

    let mounted = true;
    const fetchStatus = async () => {
      try {
        const response = await api.get<{ booking: BookingSummary }>(`/public/bookings/${bookingRef}/status`);
        if (mounted) {
          setBooking(response.data.booking);
          setLoading(false);
        }
      } catch {
        if (mounted) setLoading(false);
      }
    };

    void fetchStatus();
    const interval = window.setInterval(fetchStatus, 3000);
    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, [bookingRef]);

  return (
    <div className='flex min-h-screen items-center justify-center px-4 py-10'>
      <div className='surface-card max-w-xl text-center'>
        {loading ? (
          <div className='space-y-4'>
            <LoaderCircle className='mx-auto animate-spin text-cyan-600' size={40} />
            <h1 className='text-2xl font-bold text-slate-950'>Sto verificando il pagamento</h1>
            <p className='text-sm text-slate-600'>Attendi qualche secondo, sto aggiornando lo stato della prenotazione.</p>
          </div>
        ) : variant === 'success' ? (
          <div className='space-y-4'>
            <div className='mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-700'>
              <AlertTriangle size={26} />
            </div>
            <h1 className='text-2xl font-bold text-slate-950'>Pagamento ricevuto</h1>
            <p className='text-sm text-slate-600'>La conferma finale arriva appena il sistema chiude il controllo sullo slot.</p>
            {booking && (
              <div className='rounded-2xl bg-slate-50 p-4 text-left'>
                <div className='flex items-center justify-between'>
                  <span className='text-sm font-medium text-slate-700'>{booking.public_reference}</span>
                  <StatusBadge status={booking.status} />
                </div>
                <p className='mt-2 text-sm text-slate-600'>Durata: {booking.duration_minutes} minuti</p>
                <p className='text-sm text-slate-600'>Caparra: €{booking.deposit_amount}</p>
              </div>
            )}
          </div>
        ) : variant === 'cancelled' ? (
          <div className='space-y-4'>
            <div className='mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-amber-700'>
              <CircleX size={26} />
            </div>
            <h1 className='text-2xl font-bold text-slate-950'>Pagamento annullato</h1>
            <p className='text-sm text-slate-600'>Nessun addebito confermato. Puoi tornare indietro e riprovare quando vuoi.</p>
          </div>
        ) : (
          <div className='space-y-4'>
            <div className='mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-rose-100 text-rose-700'>
              <AlertTriangle size={26} />
            </div>
            <h1 className='text-2xl font-bold text-slate-950'>Si è verificato un problema</h1>
            <p className='text-sm text-slate-600'>Il flusso non è andato a buon fine. Riprova tra poco o contatta il campo.</p>
          </div>
        )}

        <div className='mt-6'>
          <Link to='/' className='btn-primary'>Torna alla prenotazione</Link>
        </div>
      </div>
    </div>
  );
}
