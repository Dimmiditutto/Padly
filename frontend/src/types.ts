export type BookingStatus = 'PENDING_PAYMENT' | 'CONFIRMED' | 'CANCELLED' | 'COMPLETED' | 'NO_SHOW' | 'EXPIRED';
export type PaymentProvider = 'STRIPE' | 'PAYPAL' | 'NONE';
export type PaymentStatus = 'UNPAID' | 'INITIATED' | 'PAID' | 'FAILED' | 'CANCELLED' | 'EXPIRED';

export interface TimeSlot {
  start_time: string;
  end_time: string;
  available: boolean;
  reason?: string | null;
}

export interface BookingSummary {
  id: string;
  public_reference: string;
  start_at: string;
  end_at: string;
  duration_minutes: number;
  booking_date_local: string;
  status: BookingStatus;
  deposit_amount: number;
  payment_provider: PaymentProvider;
  payment_status: PaymentStatus;
  customer_name?: string | null;
  customer_email?: string | null;
  customer_phone?: string | null;
  note?: string | null;
  created_by: string;
  source: string;
  created_at: string;
  cancelled_at?: string | null;
  completed_at?: string | null;
  no_show_at?: string | null;
  balance_paid_at?: string | null;
}

export interface AvailabilityResponse {
  date: string;
  duration_minutes: number;
  deposit_amount: number;
  slots: TimeSlot[];
}

export interface ReportResponse {
  total_bookings: number;
  confirmed_bookings: number;
  pending_bookings: number;
  cancelled_bookings: number;
  collected_deposits: number;
}
