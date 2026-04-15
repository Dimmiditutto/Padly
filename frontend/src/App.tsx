import { Navigate, Route, Routes } from 'react-router-dom';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { AdminLoginPage } from './pages/AdminLoginPage';
import { PaymentStatusPage } from './pages/PaymentStatusPage';
import { PublicBookingPage } from './pages/PublicBookingPage';

export default function App() {
  return (
    <Routes>
      <Route path='/' element={<PublicBookingPage />} />
      <Route path='/booking/success' element={<PaymentStatusPage variant='success' />} />
      <Route path='/booking/cancelled' element={<PaymentStatusPage variant='cancelled' />} />
      <Route path='/booking/error' element={<PaymentStatusPage variant='error' />} />
      <Route path='/admin/login' element={<AdminLoginPage />} />
      <Route path='/admin' element={<AdminDashboardPage />} />
      <Route path='*' element={<Navigate to='/' replace />} />
    </Routes>
  );
}
