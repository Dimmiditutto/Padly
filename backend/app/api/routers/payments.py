from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models import PaymentProvider
from app.schemas.common import SimpleMessage
from app.services.booking_service import acquire_single_court_lock
from app.services.payment_service import handle_mock_payment, handle_paypal_return, handle_paypal_webhook, handle_stripe_webhook, is_mock_payments_enabled, mark_checkout_cancelled

router = APIRouter(tags=['Payments'])


def _booking_redirect_url(path: str, booking: str, cancel_token: str | None, tenant: str | None = None) -> str:
    params = {'booking': booking}
    if cancel_token:
        params['cancelToken'] = cancel_token
    if tenant:
        params['tenant'] = tenant
    return f'{path}?{urlencode(params)}'


@router.get('/health')
def health() -> dict:
    return {'status': 'ok', 'service': settings.app_name}


@router.post('/payments/stripe/webhook', response_model=SimpleMessage)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> SimpleMessage:
    raw_payload = await request.body()
    with acquire_single_court_lock(db):
        handle_stripe_webhook(db, request, raw_payload)
        db.commit()
    return SimpleMessage(message='Stripe webhook processato')


@router.get('/payments/paypal/return')
def paypal_return(booking: str, token: str, cancelToken: str | None = None, tenant: str | None = None, db: Session = Depends(get_db)) -> RedirectResponse:
    with acquire_single_court_lock(db):
        handle_paypal_return(db, booking_reference=booking, token=token)
        db.commit()
    return RedirectResponse(url=_booking_redirect_url('/booking/success', booking, cancelToken, tenant))


@router.post('/payments/paypal/webhook', response_model=SimpleMessage)
async def paypal_webhook(request: Request, db: Session = Depends(get_db)) -> SimpleMessage:
    payload = await request.json()
    with acquire_single_court_lock(db):
        handle_paypal_webhook(db, request, payload)
        db.commit()
    return SimpleMessage(message='PayPal webhook processato')


@router.get('/payments/stripe/cancel')
def stripe_cancel(booking: str, cancelToken: str | None = None, tenant: str | None = None, db: Session = Depends(get_db)) -> RedirectResponse:
    with acquire_single_court_lock(db):
        mark_checkout_cancelled(db, booking, PaymentProvider.STRIPE, reason='Checkout Stripe annullato dal cliente')
        db.commit()
    return RedirectResponse(url=_booking_redirect_url('/booking/cancelled', booking, cancelToken, tenant))


@router.get('/payments/paypal/cancel')
def paypal_cancel(booking: str, cancelToken: str | None = None, tenant: str | None = None, db: Session = Depends(get_db)) -> RedirectResponse:
    with acquire_single_court_lock(db):
        mark_checkout_cancelled(db, booking, PaymentProvider.PAYPAL, reason='Checkout PayPal annullato dal cliente')
        db.commit()
    return RedirectResponse(url=_booking_redirect_url('/booking/cancelled', booking, cancelToken, tenant))


@router.get('/payments/mock/complete')
def mock_complete(booking: str, provider: str, cancelToken: str | None = None, tenant: str | None = None, db: Session = Depends(get_db)) -> RedirectResponse:
    if not is_mock_payments_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Endpoint non disponibile')

    chosen = PaymentProvider.STRIPE if provider.lower() == 'stripe' else PaymentProvider.PAYPAL
    with acquire_single_court_lock(db):
        handle_mock_payment(db, booking_reference=booking, provider=chosen)
        db.commit()
    return RedirectResponse(url=_booking_redirect_url('/booking/success', booking, cancelToken, tenant))
