import { Link, Navigate, Route, Routes, useLocation, useParams } from 'react-router-dom';
import { AlertBanner } from './components/AlertBanner';
import { AppBrand } from './components/AppBrand';
import { AdminBookingDetailPage } from './pages/AdminBookingDetailPage';
import { AdminBookingsPage } from './pages/AdminBookingsPage';
import { AdminCurrentBookingsPage } from './pages/AdminCurrentBookingsPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { AdminLoginPage } from './pages/AdminLoginPage';
import { AdminLogsPage } from './pages/AdminLogsPage';
import { AdminPasswordResetPage } from './pages/AdminPasswordResetPage';
import { ClubDirectoryPage } from './pages/ClubDirectoryPage';
import { InviteAcceptPage } from './pages/InviteAcceptPage';
import { PublicCancellationPage } from './pages/PublicCancellationPage';
import { PublicClubPage } from './pages/PublicClubPage';
import { PaymentStatusPage } from './pages/PaymentStatusPage';
import { PlayAccessPage } from './pages/PlayAccessPage';
import { PlayPage } from './pages/PlayPage';
import { PublicBookingPage } from './pages/PublicBookingPage';
import { SharedMatchPage } from './pages/SharedMatchPage';
import { resolveTenantSlugFromLocation } from './utils/tenantContext';
import { buildClubPlayPath, buildInviteAcceptPath, buildPlayAccessPath, buildPlayMatchPath, DEFAULT_PLAY_ALIAS_SLUG } from './utils/play';

function PlayAliasRedirect({ suffix = '' }: { suffix?: string }) {
  const location = useLocation();
  const tenantSlug = resolveTenantSlugFromLocation(location) || DEFAULT_PLAY_ALIAS_SLUG;
  return <Navigate to={`${buildClubPlayPath(tenantSlug, suffix)}${location.search}`} replace />;
}


function PlayAliasTenantRequiredPage({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className='page-shell max-w-3xl'>
      <section className='surface-card'>
        <AppBrand label='Play' />
        <h1 className='mt-4 text-3xl font-bold tracking-tight text-slate-950'>{title}</h1>
        <div className='mt-4'>
          <AlertBanner tone='error'>{message}</AlertBanner>
        </div>
        <div className='mt-6 flex flex-col gap-3 sm:flex-row'>
          <Link className='btn-secondary' to='/'>Torna al booking</Link>
        </div>
      </section>
    </div>
  );
}


function PlayInviteAliasRedirect() {
  const location = useLocation();
  const { token } = useParams();
  const tenantSlug = resolveTenantSlugFromLocation(location);

  if (!tenantSlug || !token) {
    return (
      <PlayAliasTenantRequiredPage
        title='Link invito incompleto'
        message='Questo invito play richiede il club corretto. Apri la versione completa del link del circolo oppure aggiungi ?tenant=<club-slug>.'
      />
    );
  }

  return <Navigate to={`${buildInviteAcceptPath(tenantSlug, token)}${location.search}`} replace />;
}


function PlayAccessAliasRedirect() {
  const location = useLocation();
  const { groupToken } = useParams();
  const tenantSlug = resolveTenantSlugFromLocation(location);

  if (!tenantSlug) {
    return (
      <PlayAliasTenantRequiredPage
        title='Link accesso incompleto'
        message='Questo accesso community richiede il club corretto. Apri la versione completa del link del circolo oppure aggiungi ?tenant=<club-slug>.'
      />
    );
  }

  return <Navigate to={`${buildPlayAccessPath(tenantSlug, groupToken)}${location.search}`} replace />;
}


function PlaySharedAliasRedirect() {
  const location = useLocation();
  const { shareToken } = useParams();
  const tenantSlug = resolveTenantSlugFromLocation(location);

  if (!tenantSlug || !shareToken) {
    return (
      <PlayAliasTenantRequiredPage
        title='Link partita incompleto'
        message='Questo link partita richiede il club corretto. Apri la versione completa del link del circolo oppure aggiungi ?tenant=<club-slug>.'
      />
    );
  }

  return <Navigate to={`${buildPlayMatchPath(tenantSlug, shareToken)}${location.search}`} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path='/' element={<PublicBookingPage />} />
      <Route path='/clubs' element={<ClubDirectoryPage />} />
      <Route path='/clubs/nearby' element={<ClubDirectoryPage autoLocateOnMount />} />
      <Route path='/play' element={<PlayAliasRedirect />} />
      <Route path='/play/access' element={<PlayAccessAliasRedirect />} />
      <Route path='/play/access/:groupToken' element={<PlayAccessAliasRedirect />} />
      <Route path='/play/invite/:token' element={<PlayInviteAliasRedirect />} />
      <Route path='/play/matches/:shareToken' element={<PlaySharedAliasRedirect />} />
      <Route path='/c/:clubSlug' element={<PublicClubPage />} />
      <Route path='/c/:clubSlug/play' element={<PlayPage />} />
      <Route path='/c/:clubSlug/play/access' element={<PlayAccessPage />} />
      <Route path='/c/:clubSlug/play/access/:groupToken' element={<PlayAccessPage />} />
      <Route path='/c/:clubSlug/play/invite/:token' element={<InviteAcceptPage />} />
      <Route path='/c/:clubSlug/play/matches/:shareToken' element={<SharedMatchPage />} />
      <Route path='/booking/cancel' element={<PublicCancellationPage />} />
      <Route path='/booking/success' element={<PaymentStatusPage variant='success' />} />
      <Route path='/booking/cancelled' element={<PaymentStatusPage variant='cancelled' />} />
      <Route path='/booking/error' element={<PaymentStatusPage variant='error' />} />
      <Route path='/admin/login' element={<AdminLoginPage />} />
      <Route path='/admin/reset-password' element={<AdminPasswordResetPage />} />
      <Route path='/admin' element={<AdminDashboardPage />} />
      <Route path='/admin/prenotazioni-attuali' element={<AdminCurrentBookingsPage />} />
      <Route path='/admin/prenotazioni' element={<AdminBookingsPage />} />
      <Route path='/admin/log' element={<AdminLogsPage />} />
      <Route path='/admin/bookings/:bookingId' element={<AdminBookingDetailPage />} />
      <Route path='*' element={<Navigate to='/' replace />} />
    </Routes>
  );
}
