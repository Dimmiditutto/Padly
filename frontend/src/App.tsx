import { Navigate, Route, Routes } from 'react-router-dom';
import { AdminBookingDetailPage } from './pages/AdminBookingDetailPage';
import { AdminBookingsPage } from './pages/AdminBookingsPage';
import { AdminCurrentBookingsPage } from './pages/AdminCurrentBookingsPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { AdminLoginPage } from './pages/AdminLoginPage';
import { AdminLogsPage } from './pages/AdminLogsPage';
import { AdminPasswordResetPage } from './pages/AdminPasswordResetPage';
import { PublicCancellationPage } from './pages/PublicCancellationPage';
import { PaymentStatusPage } from './pages/PaymentStatusPage';
import { PublicBookingPage } from './pages/PublicBookingPage';

export default function App() {
  return (
    <Routes>
      <Route path='/' element={<PublicBookingPage />} />
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
