from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlencode

import httpx
import stripe
from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Booking, BookingPayment, PaymentProvider, PaymentStatus, PaymentWebhookEvent
from app.services.booking_service import log_event, mark_booking_paid
from app.services.email_service import email_service


@dataclass
class PaymentInitResult:
    checkout_url: str
    provider_reference: str


class StripeGateway:
    provider = PaymentProvider.STRIPE

    def create_checkout(self, booking: Booking) -> PaymentInitResult:
        if not settings.stripe_secret_key:
            query = urlencode({'booking': booking.public_reference, 'provider': 'stripe'})
            return PaymentInitResult(checkout_url=f"{settings.app_url}/api/payments/mock/complete?{query}", provider_reference=f"mock-stripe-{booking.public_reference}")

        stripe.api_key = settings.stripe_secret_key
        session = stripe.checkout.Session.create(
            mode='payment',
            success_url=f"{settings.app_url}/booking/success?booking={booking.public_reference}",
            cancel_url=f"{settings.app_url}/booking/cancelled?booking={booking.public_reference}",
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
            query = urlencode({'booking': booking.public_reference, 'provider': 'paypal'})
            return PaymentInitResult(checkout_url=f"{settings.app_url}/api/payments/mock/complete?{query}", provider_reference=f"mock-paypal-{booking.public_reference}")

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
                'return_url': f'{settings.app_url}/api/payments/paypal/return?booking={booking.public_reference}',
                'cancel_url': f'{settings.app_url}/booking/cancelled?booking={booking.public_reference}',
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

    def capture_order(self, order_id: str) -> dict:
        token = self._access_token()
        if not token:
            return {'status': 'COMPLETED', 'id': order_id}
        response = httpx.post(
            f'{settings.paypal_base_url}/v2/checkout/orders/{order_id}/capture',
            headers={**self._headers(), 'Authorization': f'Bearer {token}'},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()


stripe_gateway = StripeGateway()
paypal_gateway = PayPalGateway()


def start_payment_for_booking(db: Session, booking: Booking, provider: PaymentProvider) -> PaymentInitResult:
    if booking.status not in {booking.status.__class__.PENDING_PAYMENT, booking.status.__class__.CONFIRMED}:
        raise HTTPException(status_code=400, detail='Stato prenotazione non compatibile con il pagamento')

    if provider == PaymentProvider.STRIPE:
        result = stripe_gateway.create_checkout(booking)
    elif provider == PaymentProvider.PAYPAL:
        result = paypal_gateway.create_checkout(booking)
    else:
        raise HTTPException(status_code=400, detail='Provider pagamento non supportato')

    booking.payment_provider = provider
    booking.payment_status = PaymentStatus.INITIATED
    booking.payment_reference = result.provider_reference

    payment = BookingPayment(
        booking_id=booking.id,
        provider=provider,
        status=PaymentStatus.INITIATED,
        amount=booking.deposit_amount,
        currency='EUR',
        provider_order_id=result.provider_reference,
        checkout_url=result.checkout_url,
    )
    db.add(payment)
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
    else:
        event = json.loads(raw_payload.decode('utf-8'))  # pragma: no cover

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
            mark_booking_paid(db, booking, provider=PaymentProvider.STRIPE, reference=data.get('id', event_id))
            email_service.booking_confirmation(db, booking)
            email_service.admin_notification(db, booking)


def handle_paypal_return(db: Session, booking_reference: str, token: str) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.public_reference == booking_reference))
    if not booking:
        raise HTTPException(status_code=404, detail='Prenotazione non trovata')

    capture = paypal_gateway.capture_order(token)
    booking = mark_booking_paid(db, booking, provider=PaymentProvider.PAYPAL, reference=capture.get('id', token))
    email_service.booking_confirmation(db, booking)
    email_service.admin_notification(db, booking)
    return booking


def handle_paypal_webhook(db: Session, payload: dict) -> None:
    event_id = payload.get('id') or f"paypal-{payload.get('event_type', 'unknown')}"
    if _already_processed(db, 'paypal', event_id):
        return

    event_type = payload.get('event_type', 'UNKNOWN')
    _record_webhook(db, 'paypal', event_id, event_type, payload)
    resource = payload.get('resource', {})
    reference = resource.get('custom_id') or resource.get('invoice_id') or resource.get('supplementary_data', {}).get('related_ids', {}).get('order_id')

    if reference:
        booking = db.scalar(select(Booking).where(Booking.public_reference == reference))
        if booking and event_type in {'PAYMENT.CAPTURE.COMPLETED', 'CHECKOUT.ORDER.APPROVED'}:
            mark_booking_paid(db, booking, provider=PaymentProvider.PAYPAL, reference=resource.get('id', event_id))
            email_service.booking_confirmation(db, booking)
            email_service.admin_notification(db, booking)


def handle_mock_payment(db: Session, booking_reference: str, provider: PaymentProvider) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.public_reference == booking_reference))
    if not booking:
        raise HTTPException(status_code=404, detail='Prenotazione non trovata')
    booking = mark_booking_paid(db, booking, provider=provider, reference=f'mock-{provider.value.lower()}-{booking.public_reference}')
    email_service.booking_confirmation(db, booking)
    email_service.admin_notification(db, booking)
    return booking
