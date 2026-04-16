import { AlertTriangle, CheckCircle2, CircleX, LoaderCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { StatusBadge } from '../components/StatusBadge';
import type { PublicBookingSummary } from '../types';
import { getPublicBookingStatus } from '../services/publicApi';
import { formatCurrency } from '../utils/format';

function BookingSnapshot({ booking }: { booking: PublicBookingSummary }) {
  return (
    <div className='rounded-2xl bg-slate-50 p-4 text-left'>
      <div className='flex items-center justify-between'>
        <span className='text-sm font-medium text-slate-700'>{booking.public_reference}</span>
        <StatusBadge status={booking.status} />
      </div>
      <p className='mt-2 text-sm text-slate-600'>Durata: {booking.duration_minutes} minuti</p>
      <p className='text-sm text-slate-600'>Caparra: {formatCurrency(booking.deposit_amount)}</p>
    </div>
  );
}

export function PaymentStatusPage({ variant }: { variant: 'success' | 'cancelled' | 'error' }) {
  const [searchParams] = useSearchParams();
  const bookingRef = searchParams.get('booking');
  const [booking, setBooking] = useState<PublicBookingSummary | null>(null);
  const [loading, setLoading] = useState(Boolean(bookingRef));
  const [statusLookupFailed, setStatusLookupFailed] = useState(false);
  const rejectedAfterSuccess = variant === 'success' && (booking?.status === 'EXPIRED' || booking?.status === 'CANCELLED');
  const successVerificationUnavailable = variant === 'success' && (!bookingRef || statusLookupFailed);
  const cancelledVerificationUnavailable = variant === 'cancelled' && Boolean(bookingRef) && statusLookupFailed;
  const cancelledAlreadyConfirmed = variant === 'cancelled' && booking?.status === 'CONFIRMED';
  const cancelledExpired = variant === 'cancelled' && booking?.status === 'EXPIRED';
  const cancelledBooking = variant === 'cancelled' && booking?.status === 'CANCELLED';

  useEffect(() => {
    if (!bookingRef) return;

    let mounted = true;
    let interval: number | undefined;

    const stopPolling = () => {
      if (interval !== undefined) {
        window.clearInterval(interval);
        interval = undefined;
      }
    };

    const fetchStatus = async () => {
      try {
        const response = await getPublicBookingStatus(bookingRef);
        if (mounted) {
          setBooking(response.booking);
          setStatusLookupFailed(false);
          setLoading(false);
          if (['CONFIRMED', 'EXPIRED', 'CANCELLED'].includes(response.booking.status)) {
            stopPolling();
          }
        }
      } catch {
        if (mounted) {
          setStatusLookupFailed(true);
          setLoading(false);
          stopPolling();
        }
      }
    };

    void fetchStatus();
    interval = window.setInterval(fetchStatus, 3000);
    return () => {
      mounted = false;
      stopPolling();
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
        ) : successVerificationUnavailable ? (
          <div className='space-y-4'>
            <div className='mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-rose-100 text-rose-700'>
              <AlertTriangle size={26} />
            </div>
            <h1 className='text-2xl font-bold text-slate-950'>Verifica pagamento non completata</h1>
            <p className='text-sm text-slate-600'>Non riesco a confermare lo stato reale della prenotazione in questo momento.</p>
            <AlertBanner tone='error'>Ricarica tra poco oppure contatta il campo indicando il riferimento prenotazione.</AlertBanner>
          </div>
        ) : rejectedAfterSuccess ? (
          <div className='space-y-4'>
            <div className='mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-amber-700'>
              <AlertTriangle size={26} />
            </div>
            <h1 className='text-2xl font-bold text-slate-950'>Pagamento non confermato</h1>
            <p className='text-sm text-slate-600'>
              {booking?.status === 'EXPIRED'
                ? 'La conferma è arrivata oltre il tempo massimo di hold e lo slot non è stato assegnato.'
                : 'La prenotazione non è più valida e il pagamento non può essere confermato automaticamente.'}
            </p>
            {booking ? <BookingSnapshot booking={booking} /> : null}
            <AlertBanner tone='warning'>Se vedi un addebito o una preautorizzazione, contatta il campo indicando il riferimento prenotazione.</AlertBanner>
          </div>
        ) : variant === 'success' ? (
          <div className='space-y-4'>
            <div className='mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-700'>
              <CheckCircle2 size={26} />
            </div>
            <h1 className='text-2xl font-bold text-slate-950'>Pagamento ricevuto</h1>
            <p className='text-sm text-slate-600'>La conferma finale arriva appena il sistema chiude il controllo sullo slot.</p>
            {booking ? <BookingSnapshot booking={booking} /> : null}
            <AlertBanner tone='info'>Se hai chiuso la pagina troppo presto, questa schermata si aggiorna da sola finché lo stato prenotazione non si stabilizza.</AlertBanner>
          </div>
        ) : variant === 'cancelled' ? (
          <div className='space-y-4'>
            {cancelledVerificationUnavailable ? (
              <>
                <div className='mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-rose-100 text-rose-700'>
                  <AlertTriangle size={26} />
                </div>
                <h1 className='text-2xl font-bold text-slate-950'>Stato annullamento da verificare</h1>
                <p className='text-sm text-slate-600'>Non riesco a confermare l'esito reale del checkout in questo momento.</p>
                <AlertBanner tone='error'>Ricarica tra poco o contatta il campo prima di ripetere il pagamento.</AlertBanner>
              </>
            ) : cancelledAlreadyConfirmed ? (
              <>
                <div className='mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-700'>
                  <CheckCircle2 size={26} />
                </div>
                <h1 className='text-2xl font-bold text-slate-950'>Pagamento già confermato</h1>
                <p className='text-sm text-slate-600'>La prenotazione risulta già confermata. Ignora questa schermata di annullamento.</p>
                {booking ? <BookingSnapshot booking={booking} /> : null}
                <AlertBanner tone='info'>Se hai ricevuto questo redirect dopo un ritorno del provider, lo stato valido resta quello mostrato qui.</AlertBanner>
              </>
            ) : cancelledExpired ? (
              <>
                <div className='mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-amber-700'>
                  <AlertTriangle size={26} />
                </div>
                <h1 className='text-2xl font-bold text-slate-950'>Prenotazione scaduta</h1>
                <p className='text-sm text-slate-600'>Lo slot non è più attivo e il pagamento non risulta confermato.</p>
                {booking ? <BookingSnapshot booking={booking} /> : null}
              </>
            ) : cancelledBooking ? (
              <>
                <div className='mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-amber-700'>
                  <CircleX size={26} />
                </div>
                <h1 className='text-2xl font-bold text-slate-950'>Prenotazione annullata</h1>
                <p className='text-sm text-slate-600'>La prenotazione non è più attiva.</p>
                {booking ? <BookingSnapshot booking={booking} /> : null}
              </>
            ) : (
              <>
                <div className='mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-amber-700'>
                  <CircleX size={26} />
                </div>
                <h1 className='text-2xl font-bold text-slate-950'>Pagamento annullato</h1>
                <p className='text-sm text-slate-600'>Nessun addebito confermato. Puoi tornare indietro e riprovare quando vuoi.</p>
                {booking ? <BookingSnapshot booking={booking} /> : null}
              </>
            )}
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
