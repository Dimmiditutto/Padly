import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AlertBanner } from '../components/AlertBanner';
import { EmptyState } from '../components/EmptyState';
import { LoadingBlock } from '../components/LoadingBlock';
import { PageBrandBar } from '../components/PageBrandBar';
import { SectionCard } from '../components/SectionCard';
import { StatusBadge } from '../components/StatusBadge';
import { cancelPublicBooking, getPublicCancellation, getPublicConfig } from '../services/publicApi';
import type { PublicCancellationResponse, PublicConfig } from '../types';
import { formatCurrency, formatDateTime } from '../utils/format';
import { getTenantSlugFromSearchParams, withTenantPath } from '../utils/tenantContext';

export function PublicCancellationPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const tenantSlug = getTenantSlugFromSearchParams(searchParams);
  const [cancellation, setCancellation] = useState<PublicCancellationResponse | null>(null);
  const [publicConfig, setPublicConfig] = useState<PublicConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const paidOnlineNoRefund = Boolean(
    cancellation
    && !cancellation.refund_required
    && cancellation.booking.payment_status === 'PAID'
    && ['STRIPE', 'PAYPAL'].includes(cancellation.booking.payment_provider)
  );

  useEffect(() => {
    void bootstrap();
  }, [token, tenantSlug]);

  async function bootstrap() {
    setLoading(true);
    setError('');
    if (!token) {
      setLoading(false);
      setError('Link annullamento non valido.');
      return;
    }

    try {
      const preview = await getPublicCancellation(token, tenantSlug);
      setCancellation(preview);
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Non riesco a verificare la prenotazione da questo link.');
      setCancellation(null);
    }

    try {
      const config = await getPublicConfig(tenantSlug);
      setPublicConfig(config);
    } catch {
      setPublicConfig(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleCancellation() {
    if (!token) return;
    setSubmitting(true);
    setError('');
    try {
      const response = await cancelPublicBooking(token, tenantSlug);
      setCancellation(response);
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || 'Annullamento non riuscito.');
      try {
        const preview = await getPublicCancellation(token, tenantSlug);
        setCancellation(preview);
      } catch {
        // Best effort refresh only.
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className='min-h-screen px-4 py-6 sm:px-6 lg:px-8'>
      <div className='page-shell max-w-3xl space-y-6'>
        <PageBrandBar
          actions={(
            <>
              <Link to={withTenantPath('/booking', tenantSlug)} className='btn-secondary inline-flex'>Torna alla prenotazione</Link>
              <Link to='/' className='btn-secondary inline-flex'>Torna alla home</Link>
            </>
          )}
        />

        {loading ? (
          <LoadingBlock label='Sto verificando il link di annullamento…' />
        ) : error && !cancellation ? (
          <EmptyState icon={AlertTriangle} title='Link annullamento non disponibile' description={error} />
        ) : cancellation ? (
          <div className='space-y-6'>
            {cancellation.message ? <AlertBanner tone={paidOnlineNoRefund ? 'warning' : 'success'}>{cancellation.message}</AlertBanner> : null}
            {error ? <AlertBanner tone='error'>{error}</AlertBanner> : null}

            <SectionCard
              title='Annullamento self-service'
              description='Controlla il riepilogo e verifica se la caparra è rimborsabile prima di confermare.'
              actions={<StatusBadge status={cancellation.booking.status} />}
              elevated
            >
              <div className='grid gap-4 sm:grid-cols-2'>
                <InfoRow label='Riferimento' value={cancellation.booking.public_reference} />
                <InfoRow label='Caparra' value={formatCurrency(cancellation.booking.deposit_amount)} />
                <InfoRow label='Inizio' value={formatDateTime(cancellation.booking.start_at)} />
                <InfoRow label='Fine' value={formatDateTime(cancellation.booking.end_at)} />
                <InfoRow label='Durata' value={`${cancellation.booking.duration_minutes} minuti`} />
                <InfoRow label='Pagamento' value={`${cancellation.booking.payment_provider} • ${cancellation.booking.payment_status}`} />
              </div>

              {publicConfig ? (
                <div className='mt-5 rounded-[24px] border border-cyan-200 bg-cyan-50 p-4 text-sm text-slate-700'>
                  Puoi annullare in autonomia fino all inizio della prenotazione. Se annulli prima di {publicConfig.cancellation_window_hours} ore dall inizio, la caparra online viene rimborsata automaticamente. Nelle ultime {publicConfig.cancellation_window_hours} ore la caparra non è rimborsabile.
                </div>
              ) : null}

              <div className='mt-5'>
                <AlertBanner tone={cancellation.refund_status === 'FAILED' ? 'error' : paidOnlineNoRefund ? 'warning' : cancellation.refund_required ? 'info' : 'success'}>
                  {cancellation.refund_message}
                </AlertBanner>
              </div>

              {cancellation.cancellation_reason ? (
                <div className='mt-5'>
                  <AlertBanner tone='warning'>{cancellation.cancellation_reason}</AlertBanner>
                </div>
              ) : null}

              {cancellation.cancellable ? (
                <div className='mt-5 flex flex-wrap gap-3'>
                  <button className='btn-primary' type='button' disabled={submitting} onClick={() => void handleCancellation()}>
                    {submitting
                      ? 'Annullamento in corso…'
                      : cancellation.refund_required
                        ? 'Conferma annullamento e rimborso'
                        : 'Conferma annullamento'}
                  </button>
                  <Link to={withTenantPath('/booking', tenantSlug)} className='btn-secondary'>Mantieni la prenotazione</Link>
                </div>
              ) : (
                <div className='mt-5 flex items-center gap-3 rounded-[24px] border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600'>
                  <CheckCircle2 size={18} className='text-slate-400' />
                  <span>Nessuna azione ulteriore disponibile da questo link.</span>
                </div>
              )}
            </SectionCard>
          </div>
        ) : (
          <EmptyState icon={AlertTriangle} title='Link annullamento non disponibile' description='Non riesco a mostrare i dettagli della prenotazione da questo link.' />
        )}
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className='surface-muted'>
      <p className='text-xs font-semibold uppercase tracking-[0.18em] text-slate-500'>{label}</p>
      <p className='mt-2 text-sm font-medium text-slate-900'>{value}</p>
    </div>
  );
}