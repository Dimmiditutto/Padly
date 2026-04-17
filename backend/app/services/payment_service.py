from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from urllib.parse import urlencode

import httpx
import stripe
from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Booking, BookingPayment, BookingStatus, PaymentProvider, PaymentStatus, PaymentWebhookEvent
from app.services.booking_service import as_utc, calculate_deposit, expire_pending_booking_if_needed, log_event, mark_booking_paid
from app.services.email_service import email_service
from app.services.settings_service import get_booking_rules


class PaymentGateway(Protocol):
    provider: PaymentProvider

    def create_checkout(self, booking: Booking) -> PaymentInitResult:
        ...

    def refund_payment(self, booking: Booking, payment: BookingPayment) -> 'RefundResult':
        ...


@dataclass
class PaymentInitResult:
    checkout_url: str
    provider_reference: str


@dataclass
class RefundResult:
    required: bool
    status: str
    amount: Decimal | None
    message: str
    provider_refund_id: str | None = None


REFUND_STATUS_NOT_REQUIRED = 'NOT_REQUIRED'
REFUND_STATUS_PENDING = 'PENDING'
REFUND_STATUS_SUCCEEDED = 'SUCCEEDED'
REFUND_STATUS_FAILED = 'FAILED'
ONLINE_REFUND_PROVIDERS = {PaymentProvider.STRIPE, PaymentProvider.PAYPAL}


def _booking_redirect_query(booking: Booking) -> str:
    params = {'booking': booking.public_reference}
    if booking.cancel_token:
        params['cancelToken'] = booking.cancel_token
    return urlencode(params)


class StripeGateway:
    provider = PaymentProvider.STRIPE

    def create_checkout(self, booking: Booking) -> PaymentInitResult:
        if not settings.stripe_secret_key:
            if not is_mock_payments_enabled():
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_provider_unavailable_detail(self.provider))
            query_params = {'booking': booking.public_reference, 'provider': 'stripe'}
            if booking.cancel_token:
                query_params['cancelToken'] = booking.cancel_token
            query = urlencode(query_params)
            return PaymentInitResult(checkout_url=f"{settings.app_url}/api/payments/mock/complete?{query}", provider_reference=f"mock-stripe-{booking.public_reference}")

        stripe.api_key = settings.stripe_secret_key
        redirect_query = _booking_redirect_query(booking)
        session = stripe.checkout.Session.create(
            mode='payment',
            success_url=f"{settings.app_url}/booking/success?{redirect_query}",
            cancel_url=f"{settings.app_url}/api/payments/stripe/cancel?{redirect_query}",
            client_reference_id=booking.public_reference,
            metadata={'booking_id': booking.id, 'public_reference': booking.public_reference},
            line_items=[
                {
                    'quantity': 1,
                    'price_data': {
                        'currency': 'eur',
                        'unit_amount': int(Decimal(booking.deposit_amount) * 100),
                        'product_data': {
                            'name': 'Caparra campo padel',
                            'description': f'Prenotazione {booking.public_reference} - {booking.duration_minutes} minuti',
                        },
                    },
                }
            ],
        )
        return PaymentInitResult(checkout_url=session.url, provider_reference=session.id)

    def refund_payment(self, booking: Booking, payment: BookingPayment) -> RefundResult:
        reference = payment.provider_capture_id or payment.provider_order_id or booking.payment_reference
        amount = _to_decimal(payment.amount or booking.deposit_amount)
        if not reference or amount is None:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Riferimento Stripe non disponibile per il rimborso')

        if not settings.stripe_secret_key:
            if not is_mock_payments_enabled():
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_provider_unavailable_detail(self.provider))
            return RefundResult(
                required=True,
                status=REFUND_STATUS_SUCCEEDED,
                amount=amount,
                message='Caparra rimborsata automaticamente in ambiente di test.',
                provider_refund_id=f'mock-refund-stripe-{booking.public_reference}',
            )

        stripe.api_key = settings.stripe_secret_key
        refund_params: dict[str, object] = {
            'amount': int(amount * 100),
            'reason': 'requested_by_customer',
            'metadata': {'booking_id': booking.id, 'public_reference': booking.public_reference},
        }
        if str(reference).startswith('ch_'):
            refund_params['charge'] = reference
        else:
            refund_params['payment_intent'] = reference

        refund = stripe.Refund.create(**refund_params)
        normalized_status = _normalize_stripe_refund_status(getattr(refund, 'status', None) or refund.get('status'))
        return RefundResult(
            required=True,
            status=normalized_status,
            amount=amount,
            message=_refund_message_for_status(normalized_status, required=True, before_cancellation=False),
            provider_refund_id=getattr(refund, 'id', None) or refund.get('id'),
        )


class PayPalGateway:
    provider = PaymentProvider.PAYPAL

    def _headers(self) -> dict[str, str]:
        return {'Content-Type': 'application/json'}

    def _access_token(self) -> str | None:
        if not settings.paypal_client_id or not settings.paypal_client_secret:
            return None
        response = httpx.post(
            f'{settings.paypal_base_url}/v1/oauth2/token',
            auth=(settings.paypal_client_id, settings.paypal_client_secret),
            headers={'Accept': 'application/json', 'Accept-Language': 'it_IT'},
            data={'grant_type': 'client_credentials'},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()['access_token']

    def create_checkout(self, booking: Booking) -> PaymentInitResult:
        token = self._access_token()
        if not token:
            if not is_mock_payments_enabled():
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_provider_unavailable_detail(self.provider))
            query_params = {'booking': booking.public_reference, 'provider': 'paypal'}
            if booking.cancel_token:
                query_params['cancelToken'] = booking.cancel_token
            query = urlencode(query_params)
            return PaymentInitResult(checkout_url=f"{settings.app_url}/api/payments/mock/complete?{query}", provider_reference=f"mock-paypal-{booking.public_reference}")

        redirect_query = _booking_redirect_query(booking)
        body = {
            'intent': 'CAPTURE',
            'purchase_units': [
                {
                    'reference_id': booking.public_reference,
                    'custom_id': booking.public_reference,
                    'invoice_id': booking.public_reference,
                    'description': f'Caparra prenotazione {booking.public_reference}',
                    'amount': {'currency_code': 'EUR', 'value': f'{booking.deposit_amount:.2f}'},
                }
            ],
            'application_context': {
                'return_url': f'{settings.app_url}/api/payments/paypal/return?{redirect_query}',
                'cancel_url': f'{settings.app_url}/api/payments/paypal/cancel?{redirect_query}',
                'brand_name': settings.app_name,
                'user_action': 'PAY_NOW',
            },
        }
        response = httpx.post(
            f'{settings.paypal_base_url}/v2/checkout/orders',
            headers={**self._headers(), 'Authorization': f'Bearer {token}'},
            json=body,
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        approve_url = next((link['href'] for link in payload.get('links', []) if link.get('rel') == 'approve'), None)
        if not approve_url:
            raise HTTPException(status_code=502, detail='PayPal non ha restituito un link di checkout valido')
        return PaymentInitResult(checkout_url=approve_url, provider_reference=payload['id'])

    def refund_payment(self, booking: Booking, payment: BookingPayment) -> RefundResult:
        capture_id = payment.provider_capture_id
        amount = _to_decimal(payment.amount or booking.deposit_amount)
        if not capture_id or amount is None:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Riferimento PayPal non disponibile per il rimborso')

        token = self._access_token()
        if not token:
            if not is_mock_payments_enabled():
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_provider_unavailable_detail(self.provider))
            return RefundResult(
                required=True,
                status=REFUND_STATUS_SUCCEEDED,
                amount=amount,
                message='Caparra rimborsata automaticamente in ambiente di test.',
                provider_refund_id=f'mock-refund-paypal-{booking.public_reference}',
            )

        response = httpx.post(
            f'{settings.paypal_base_url}/v2/payments/captures/{capture_id}/refund',
            headers={**self._headers(), 'Authorization': f'Bearer {token}'},
            json={
                'amount': {'value': f'{amount:.2f}', 'currency_code': 'EUR'},
                'note_to_payer': f'Rimborso caparra prenotazione {booking.public_reference}',
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json() if response.content else {}
        normalized_status = _normalize_paypal_refund_status(payload.get('status') or 'PENDING')
        return RefundResult(
            required=True,
            status=normalized_status,
            amount=amount,
            message=_refund_message_for_status(normalized_status, required=True, before_cancellation=False),
            provider_refund_id=payload.get('id'),
        )

    def capture_order(self, order_id: str) -> dict:
        token = self._access_token()
        if not token:
            if not is_mock_payments_enabled():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_provider_unavailable_detail(self.provider))
            return {'status': 'COMPLETED', 'id': order_id}
        response = httpx.post(
            f'{settings.paypal_base_url}/v2/checkout/orders/{order_id}/capture',
            headers={**self._headers(), 'Authorization': f'Bearer {token}'},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def verify_webhook(self, request: Request, payload: dict) -> None:
        if not settings.paypal_webhook_id or not settings.paypal_client_id or not settings.paypal_client_secret:
            if not is_mock_payments_enabled():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_provider_webhook_unavailable_detail(self.provider))
            return

        token = self._access_token()
        if not token:
            if not is_mock_payments_enabled():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_provider_webhook_unavailable_detail(self.provider))
            return

        body = {
            'auth_algo': request.headers.get('paypal-auth-algo'),
            'cert_url': request.headers.get('paypal-cert-url'),
            'transmission_id': request.headers.get('paypal-transmission-id'),
            'transmission_sig': request.headers.get('paypal-transmission-sig'),
            'transmission_time': request.headers.get('paypal-transmission-time'),
            'webhook_id': settings.paypal_webhook_id,
            'webhook_event': payload,
        }
        response = httpx.post(
            f'{settings.paypal_base_url}/v1/notifications/verify-webhook-signature',
            headers={**self._headers(), 'Authorization': f'Bearer {token}'},
            json=body,
            timeout=20,
        )
        response.raise_for_status()
        verification_status = response.json().get('verification_status')
        if verification_status != 'SUCCESS':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Webhook PayPal non verificato')


stripe_gateway = StripeGateway()
paypal_gateway = PayPalGateway()
GATEWAYS: dict[PaymentProvider, PaymentGateway] = {
    PaymentProvider.STRIPE: stripe_gateway,
    PaymentProvider.PAYPAL: paypal_gateway,
}


MOCK_PAYMENT_ENVS = {'development', 'test'}


def is_mock_payments_enabled() -> bool:
    return settings.app_env.lower() in MOCK_PAYMENT_ENVS


def _provider_unavailable_detail(provider: PaymentProvider) -> str:
    provider_label = 'Stripe' if provider == PaymentProvider.STRIPE else 'PayPal'
    if settings.is_production:
        return f'{provider_label} non configurato in produzione'
    return f'{provider_label} non disponibile in questo ambiente'


def _provider_webhook_unavailable_detail(provider: PaymentProvider) -> str:
    provider_label = 'Stripe' if provider == PaymentProvider.STRIPE else 'PayPal'
    if settings.is_production:
        return f'{provider_label} webhook non configurato in produzione'
    return f'{provider_label} webhook non disponibile in questo ambiente'


def is_stripe_checkout_available() -> bool:
    return bool(settings.stripe_secret_key) or is_mock_payments_enabled()


def is_paypal_checkout_available() -> bool:
    return bool(settings.paypal_client_id and settings.paypal_client_secret) or is_mock_payments_enabled()


def is_checkout_available(provider: PaymentProvider) -> bool:
    _assert_valid_provider(provider)
    if provider == PaymentProvider.STRIPE:
        return is_stripe_checkout_available()
    return is_paypal_checkout_available()


def assert_checkout_available(provider: PaymentProvider) -> None:
    if not is_checkout_available(provider):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_provider_unavailable_detail(provider))


def _normalize_stripe_refund_status(value: str | None) -> str:
    normalized = (value or '').lower()
    if normalized == 'succeeded':
        return REFUND_STATUS_SUCCEEDED
    if normalized in {'pending', 'requires_action'}:
        return REFUND_STATUS_PENDING
    return REFUND_STATUS_FAILED


def _normalize_paypal_refund_status(value: str | None) -> str:
    normalized = (value or '').upper()
    if normalized == 'COMPLETED':
        return REFUND_STATUS_SUCCEEDED
    if normalized in {'PENDING', 'CREATED'}:
        return REFUND_STATUS_PENDING
    return REFUND_STATUS_FAILED


def _refund_message_for_status(status_value: str, *, required: bool, before_cancellation: bool, error: str | None = None) -> str:
    if not required:
        return 'Nessun rimborso automatico necessario: la caparra online non risulta incassata.'
    if status_value == REFUND_STATUS_SUCCEEDED:
        return 'Caparra rimborsata automaticamente.'
    if status_value == REFUND_STATUS_PENDING:
        if before_cancellation:
            return 'Confermando l\'annullamento la caparra verra rimborsata automaticamente.'
        return 'Rimborso automatico della caparra avviato correttamente.'
    return error or 'Il rimborso automatico della caparra non e andato a buon fine.'


def _refund_cutoff_hours(db: Session) -> int:
    return get_booking_rules(db)['cancellation_window_hours']


def _hours_until_booking_start(booking: Booking) -> float:
    return (as_utc(booking.start_at) - datetime.now(UTC)).total_seconds() / 3600


def _late_cancellation_refund_message(cutoff_hours: int, *, before_cancellation: bool) -> str:
    if before_cancellation:
        return f'Annullando nelle ultime {cutoff_hours} ore la caparra non verra rimborsata automaticamente.'
    return f'Nessun rimborso automatico: la cancellazione e avvenuta nelle ultime {cutoff_hours} ore.'


def _to_decimal(value: Decimal | str | int | float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal('0.01'))


def _parse_provider_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _expected_booking_amount(booking: Booking) -> Decimal:
    expected = _to_decimal(calculate_deposit(booking.duration_minutes))
    current = _to_decimal(booking.deposit_amount)
    if current != expected:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Importo caparra non coerente con la durata prenotata')
    return expected


def _assert_valid_provider(provider: PaymentProvider) -> None:
    if provider not in {PaymentProvider.STRIPE, PaymentProvider.PAYPAL}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Provider pagamento non supportato')


def _assert_payment_amount(booking: Booking, *, amount: Decimal | str | int | float | None, currency: str = 'EUR') -> Decimal:
    if currency.upper() != 'EUR':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Valuta pagamento non valida')

    expected = _expected_booking_amount(booking)
    actual = _to_decimal(amount) or expected
    if actual != expected:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Importo pagamento non coerente con la caparra')
    return actual


def _find_booking_payment(
    db: Session,
    booking: Booking,
    *,
    provider: PaymentProvider,
    provider_order_id: str | None = None,
) -> BookingPayment | None:
    stmt = select(BookingPayment).where(BookingPayment.booking_id == booking.id, BookingPayment.provider == provider)
    if provider_order_id:
        payment = db.scalar(stmt.where(BookingPayment.provider_order_id == provider_order_id).limit(1))
        if payment:
            return payment
    return db.scalar(stmt.order_by(BookingPayment.created_at.desc()).limit(1))


def _find_booking_by_payment_reference(
    db: Session,
    *,
    provider: PaymentProvider,
    provider_order_id: str | None = None,
    provider_capture_id: str | None = None,
) -> Booking | None:
    if provider_order_id:
        payment = db.scalar(
            select(BookingPayment)
            .where(BookingPayment.provider == provider, BookingPayment.provider_order_id == provider_order_id)
            .limit(1)
        )
        if payment:
            return db.scalar(select(Booking).where(Booking.id == payment.booking_id))

    if provider_capture_id:
        payment = db.scalar(
            select(BookingPayment)
            .where(BookingPayment.provider == provider, BookingPayment.provider_capture_id == provider_capture_id)
            .limit(1)
        )
        if payment:
            return db.scalar(select(Booking).where(Booking.id == payment.booking_id))

    return None


def _ensure_booking_payment(
    db: Session,
    booking: Booking,
    *,
    provider: PaymentProvider,
    provider_order_id: str | None = None,
    checkout_url: str | None = None,
) -> BookingPayment:
    payment = _find_booking_payment(db, booking, provider=provider, provider_order_id=provider_order_id)
    if payment:
        if provider_order_id:
            payment.provider_order_id = provider_order_id
        if checkout_url:
            payment.checkout_url = checkout_url
        return payment

    payment = BookingPayment(
        booking_id=booking.id,
        provider=provider,
        status=PaymentStatus.INITIATED,
        amount=_expected_booking_amount(booking),
        currency='EUR',
        provider_order_id=provider_order_id,
        checkout_url=checkout_url,
    )
    db.add(payment)
    db.flush()
    return payment


def _reuse_initiated_checkout(db: Session, booking: Booking, *, provider: PaymentProvider) -> PaymentInitResult | None:
    payment = _find_booking_payment(db, booking, provider=provider)
    if not payment:
        return None

    provider_reference = payment.provider_order_id or booking.payment_reference
    if (
        booking.status == BookingStatus.PENDING_PAYMENT
        and booking.payment_status == PaymentStatus.INITIATED
        and payment.status == PaymentStatus.INITIATED
        and payment.checkout_url
        and provider_reference
    ):
        booking.payment_provider = provider
        booking.payment_reference = provider_reference
        payment.provider_order_id = provider_reference
        return PaymentInitResult(checkout_url=payment.checkout_url, provider_reference=provider_reference)

    return None


def get_booking_refund_snapshot(db: Session, booking: Booking) -> RefundResult:
    provider = booking.payment_provider
    payment = None
    if provider in ONLINE_REFUND_PROVIDERS:
        payment = _find_booking_payment(db, booking, provider=provider)

    amount = _to_decimal((payment.refunded_amount if payment and payment.refunded_amount is not None else None) or (payment.amount if payment else booking.deposit_amount))
    paid_online_payment = booking.payment_status == PaymentStatus.PAID and provider in ONLINE_REFUND_PROVIDERS
    cutoff_hours = _refund_cutoff_hours(db)
    within_refund_block_window = paid_online_payment and _hours_until_booking_start(booking) < cutoff_hours

    if payment and payment.refund_status:
        refund_required = payment.refund_status in {REFUND_STATUS_SUCCEEDED, REFUND_STATUS_PENDING, REFUND_STATUS_FAILED}
        if payment.refund_status == REFUND_STATUS_NOT_REQUIRED and paid_online_payment:
            message = _late_cancellation_refund_message(cutoff_hours, before_cancellation=booking.status != BookingStatus.CANCELLED)
        else:
            message = _refund_message_for_status(
                payment.refund_status,
                required=refund_required,
                before_cancellation=booking.status != BookingStatus.CANCELLED,
                error=payment.refund_error,
            )
        return RefundResult(
            required=refund_required,
            status=payment.refund_status,
            amount=amount,
            message=message,
            provider_refund_id=payment.provider_refund_id,
        )

    if not paid_online_payment:
        return RefundResult(
            required=False,
            status=REFUND_STATUS_NOT_REQUIRED,
            amount=amount,
            message=_refund_message_for_status(REFUND_STATUS_NOT_REQUIRED, required=False, before_cancellation=False),
            provider_refund_id=payment.provider_refund_id if payment else None,
        )

    if within_refund_block_window:
        return RefundResult(
            required=False,
            status=REFUND_STATUS_NOT_REQUIRED,
            amount=amount,
            message=_late_cancellation_refund_message(cutoff_hours, before_cancellation=booking.status != BookingStatus.CANCELLED),
            provider_refund_id=payment.provider_refund_id if payment else None,
        )

    return RefundResult(
        required=True,
        status=REFUND_STATUS_PENDING,
        amount=amount,
        message=_refund_message_for_status(REFUND_STATUS_PENDING, required=True, before_cancellation=booking.status != BookingStatus.CANCELLED),
        provider_refund_id=payment.provider_refund_id if payment else None,
    )


def refund_booking_payment(db: Session, booking: Booking) -> RefundResult:
    snapshot = get_booking_refund_snapshot(db, booking)
    provider = booking.payment_provider

    if not snapshot.required:
        payment = None
        if provider in ONLINE_REFUND_PROVIDERS:
            payment = _find_booking_payment(db, booking, provider=provider)
        if payment:
            payment.refund_status = REFUND_STATUS_NOT_REQUIRED
            payment.provider_refund_id = None
            payment.refunded_amount = None
            payment.refunded_at = None
            payment.refund_error = None
        if booking.payment_status == PaymentStatus.PAID and provider in ONLINE_REFUND_PROVIDERS:
            log_event(db, booking, 'PAYMENT_REFUND_NOT_REQUIRED', snapshot.message, actor='payment')
        return get_booking_refund_snapshot(db, booking)

    payment = _find_booking_payment(db, booking, provider=provider)
    if not payment:
        log_event(db, booking, 'PAYMENT_REFUND_FAILED', 'Pagamento caparra non trovato per il rimborso', actor='payment')
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Il rimborso automatico della caparra non e disponibile in questo momento')

    if payment.refund_status in {REFUND_STATUS_SUCCEEDED, REFUND_STATUS_PENDING}:
        return get_booking_refund_snapshot(db, booking)

    try:
        result = GATEWAYS[provider].refund_payment(booking, payment)
    except HTTPException as exc:
        payment.refund_status = REFUND_STATUS_FAILED
        payment.refund_error = str(exc.detail)
        payment.refunded_at = None
        log_event(db, booking, 'PAYMENT_REFUND_FAILED', payment.refund_error, actor='payment')
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Il rimborso automatico della caparra non e andato a buon fine') from exc
    except Exception as exc:
        payment.refund_status = REFUND_STATUS_FAILED
        payment.refund_error = 'Errore tecnico durante il rimborso automatico'
        payment.refunded_at = None
        log_event(db, booking, 'PAYMENT_REFUND_FAILED', payment.refund_error, actor='payment')
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Il rimborso automatico della caparra non e andato a buon fine') from exc

    if result.status == REFUND_STATUS_FAILED:
        payment.refund_status = REFUND_STATUS_FAILED
        payment.refund_error = result.message
        payment.refunded_at = None
        log_event(db, booking, 'PAYMENT_REFUND_FAILED', result.message, actor='payment')
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Il rimborso automatico della caparra non e andato a buon fine')

    payment.refund_status = result.status
    payment.provider_refund_id = result.provider_refund_id
    payment.refunded_amount = result.amount
    payment.refunded_at = datetime.now(UTC) if result.status == REFUND_STATUS_SUCCEEDED else None
    payment.refund_error = None
    log_event(
        db,
        booking,
        'PAYMENT_REFUND_SUCCEEDED' if result.status == REFUND_STATUS_SUCCEEDED else 'PAYMENT_REFUND_PENDING',
        result.message,
        actor='payment',
        payload={
            'provider_refund_id': result.provider_refund_id,
            'amount': str(result.amount) if result.amount is not None else None,
        },
    )
    return result


def _confirm_payment(
    db: Session,
    booking: Booking,
    *,
    provider: PaymentProvider,
    provider_order_id: str | None,
    provider_capture_id: str | None,
    amount: Decimal | str | int | float | None,
    currency: str = 'EUR',
    occurred_at: datetime | None = None,
) -> bool:
    actual_amount = _assert_payment_amount(booking, amount=amount, currency=currency)
    payment = _ensure_booking_payment(
        db,
        booking,
        provider=provider,
        provider_order_id=provider_order_id,
    )
    payment.amount = actual_amount
    payment.currency = currency.upper()
    if provider_order_id:
        payment.provider_order_id = provider_order_id
    if provider_capture_id:
        payment.provider_capture_id = provider_capture_id

    already_confirmed = booking.payment_status == PaymentStatus.PAID and booking.status == BookingStatus.CONFIRMED
    booking = mark_booking_paid(
        db,
        booking,
        provider=provider,
        reference=provider_capture_id or provider_order_id or payment.provider_order_id or booking.public_reference,
        occurred_at=occurred_at,
    )

    if booking.payment_status == PaymentStatus.PAID and booking.status == BookingStatus.CONFIRMED:
        payment.status = PaymentStatus.PAID
        return not already_confirmed

    if booking.status == BookingStatus.EXPIRED:
        payment.status = PaymentStatus.EXPIRED
    elif booking.status == BookingStatus.CANCELLED:
        payment.status = PaymentStatus.CANCELLED
    return False


def mark_checkout_cancelled(db: Session, booking_reference: str, provider: PaymentProvider, *, reason: str) -> Booking:
    _assert_valid_provider(provider)
    booking = db.scalar(select(Booking).where(Booking.public_reference == booking_reference))
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Prenotazione non trovata')

    if expire_pending_booking_if_needed(db, booking, actor='payment'):
        return booking

    if booking.payment_status == PaymentStatus.PAID or booking.status != BookingStatus.PENDING_PAYMENT:
        return booking

    booking.payment_provider = provider
    booking.payment_status = PaymentStatus.CANCELLED
    payment = _find_booking_payment(db, booking, provider=provider)
    if payment and payment.status != PaymentStatus.PAID:
        payment.status = PaymentStatus.CANCELLED
    log_event(db, booking, 'PAYMENT_CANCELLED', reason, actor='payment')
    return booking


def _notify_booking_confirmed(db: Session, booking: Booking, *, was_confirmed: bool) -> None:
    if not was_confirmed:
        return
    email_service.booking_confirmation(db, booking)
    email_service.admin_notification(db, booking)


def start_payment_for_booking(db: Session, booking: Booking, provider: PaymentProvider) -> PaymentInitResult:
    _assert_valid_provider(provider)
    assert_checkout_available(provider)
    _expected_booking_amount(booking)

    expires_at = as_utc(booking.expires_at) if booking.expires_at else None
    if expires_at and datetime.now(UTC) > expires_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='La prenotazione è scaduta')

    if booking.status not in {booking.status.__class__.PENDING_PAYMENT, booking.status.__class__.CONFIRMED}:
        raise HTTPException(status_code=400, detail='Stato prenotazione non compatibile con il pagamento')

    existing_checkout = _reuse_initiated_checkout(db, booking, provider=provider)
    if existing_checkout:
        return existing_checkout

    result = GATEWAYS[provider].create_checkout(booking)

    booking.payment_provider = provider
    booking.payment_status = PaymentStatus.INITIATED
    booking.payment_reference = result.provider_reference

    payment = _ensure_booking_payment(
        db,
        booking,
        provider=provider,
        provider_order_id=result.provider_reference,
        checkout_url=result.checkout_url,
    )
    payment.status = PaymentStatus.INITIATED
    log_event(db, booking, 'PAYMENT_INITIATED', f'Checkout {provider.value} avviato', actor='payment')
    return result


def _already_processed(db: Session, provider: str, event_id: str) -> bool:
    existing = db.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.provider == provider, PaymentWebhookEvent.event_id == event_id))
    return existing is not None


def _record_webhook(db: Session, provider: str, event_id: str, event_type: str, payload: dict) -> None:
    db.add(PaymentWebhookEvent(provider=provider, event_id=event_id, event_type=event_type, payload=payload, processed_at=datetime.now(UTC)))


def handle_stripe_webhook(db: Session, request: Request, raw_payload: bytes) -> None:
    signature = request.headers.get('stripe-signature')
    if settings.stripe_webhook_secret:
        event = stripe.Webhook.construct_event(raw_payload, signature, settings.stripe_webhook_secret)
    elif not is_mock_payments_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_provider_webhook_unavailable_detail(PaymentProvider.STRIPE),
        )
    else:
        event = json.loads(raw_payload.decode('utf-8'))

    event_id = event['id']
    if _already_processed(db, 'stripe', event_id):
        return

    event_type = event['type']
    data = event['data']['object']
    _record_webhook(db, 'stripe', event_id, event_type, event)

    if event_type == 'checkout.session.completed':
        reference = data.get('client_reference_id') or data.get('metadata', {}).get('public_reference')
        booking = db.scalar(select(Booking).where(Booking.public_reference == reference))
        if booking:
            was_confirmed = _confirm_payment(
                db,
                booking,
                provider=PaymentProvider.STRIPE,
                provider_order_id=data.get('id'),
                provider_capture_id=data.get('payment_intent'),
                amount=(Decimal(str(data.get('amount_total', 0))) / Decimal('100')) if data.get('amount_total') is not None else None,
                currency=(data.get('currency') or 'eur').upper(),
                occurred_at=datetime.fromtimestamp(event.get('created', int(datetime.now(UTC).timestamp())), UTC),
            )
            _notify_booking_confirmed(db, booking, was_confirmed=was_confirmed)
    elif event_type == 'checkout.session.expired':
        reference = data.get('client_reference_id') or data.get('metadata', {}).get('public_reference')
        booking = db.scalar(select(Booking).where(Booking.public_reference == reference))
        if booking:
            mark_checkout_cancelled(db, reference, PaymentProvider.STRIPE, reason='Sessione Stripe scaduta o annullata')


def handle_paypal_return(db: Session, booking_reference: str, token: str) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.public_reference == booking_reference))
    if not booking:
        raise HTTPException(status_code=404, detail='Prenotazione non trovata')

    if booking.status == BookingStatus.CONFIRMED and booking.payment_status == PaymentStatus.PAID:
        log_event(
            db,
            booking,
            'PAYPAL_RETURN_ALREADY_CONFIRMED',
            'Doppio ritorno PayPal ignorato: prenotazione già confermata',
            actor='payment',
        )
        return booking

    capture = paypal_gateway.capture_order(token)
    capture_block = ((capture.get('purchase_units') or [{}])[0].get('payments') or {}).get('captures', [{}])[0]
    amount_block = capture_block.get('amount', {})
    was_confirmed = _confirm_payment(
        db,
        booking,
        provider=PaymentProvider.PAYPAL,
        provider_order_id=token,
        provider_capture_id=capture_block.get('id', capture.get('id', token)),
        amount=amount_block.get('value'),
        currency=amount_block.get('currency_code', 'EUR'),
        occurred_at=_parse_provider_datetime(capture_block.get('create_time') or capture.get('create_time')),
    )
    _notify_booking_confirmed(db, booking, was_confirmed=was_confirmed)
    return booking


def handle_paypal_webhook(db: Session, request: Request, payload: dict) -> None:
    paypal_gateway.verify_webhook(request, payload)

    event_id = payload.get('id') or f"paypal-{payload.get('event_type', 'unknown')}"
    if _already_processed(db, 'paypal', event_id):
        return

    event_type = payload.get('event_type', 'UNKNOWN')
    _record_webhook(db, 'paypal', event_id, event_type, payload)
    resource = payload.get('resource', {})
    reference = resource.get('custom_id') or resource.get('invoice_id')
    provider_order_id = resource.get('supplementary_data', {}).get('related_ids', {}).get('order_id') or resource.get('id')
    provider_capture_id = resource.get('id')

    booking = None
    if reference:
        booking = db.scalar(select(Booking).where(Booking.public_reference == reference))
    if not booking:
        booking = _find_booking_by_payment_reference(
            db,
            provider=PaymentProvider.PAYPAL,
            provider_order_id=provider_order_id,
            provider_capture_id=provider_capture_id,
        )

    if booking:
        if booking and event_type == 'PAYMENT.CAPTURE.COMPLETED':
            amount_block = resource.get('amount', {})
            was_confirmed = _confirm_payment(
                db,
                booking,
                provider=PaymentProvider.PAYPAL,
                provider_order_id=provider_order_id,
                provider_capture_id=provider_capture_id,
                amount=amount_block.get('value'),
                currency=amount_block.get('currency_code', 'EUR'),
                occurred_at=_parse_provider_datetime(resource.get('create_time')),
            )
            _notify_booking_confirmed(db, booking, was_confirmed=was_confirmed)
        elif booking and event_type in {'CHECKOUT.ORDER.CANCELLED', 'PAYMENT.CAPTURE.DENIED'}:
            mark_checkout_cancelled(db, booking.public_reference, PaymentProvider.PAYPAL, reason='Pagamento PayPal non completato')


def handle_mock_payment(db: Session, booking_reference: str, provider: PaymentProvider) -> Booking:
    if not is_mock_payments_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Endpoint non disponibile')

    booking = db.scalar(select(Booking).where(Booking.public_reference == booking_reference))
    if not booking:
        raise HTTPException(status_code=404, detail='Prenotazione non trovata')
    was_confirmed = _confirm_payment(
        db,
        booking,
        provider=provider,
        provider_order_id=booking.payment_reference,
        provider_capture_id=f'mock-{provider.value.lower()}-{booking.public_reference}',
        amount=booking.deposit_amount,
        currency='EUR',
        occurred_at=datetime.now(UTC),
    )
    _notify_booking_confirmed(db, booking, was_confirmed=was_confirmed)
    return booking
