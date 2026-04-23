from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import (
    Admin,
    AppSetting,
    BillingWebhookEvent,
    Booking,
    BookingPayment,
    BookingStatus,
    Club,
    ClubSubscription,
    Customer,
    EmailNotificationLog,
    PaymentWebhookEvent,
)
from app.schemas.data_governance import DataExportScope
from app.services.booking_service import log_event

ANONYMIZED_EMAIL_DOMAIN = 'redacted.local'


def _get_club_or_404(db: Session, club_id: str) -> Club:
    club = db.scalar(
        select(Club)
        .options(
            selectinload(Club.domains),
            selectinload(Club.subscription).selectinload(ClubSubscription.plan),
        )
        .where(Club.id == club_id)
    )
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Tenant non trovato.')
    return club


def _get_customer_or_404(db: Session, club_id: str, customer_id: str) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.club_id == club_id, Customer.id == customer_id))
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Cliente non trovato per il tenant richiesto.')
    return customer


def _serialize_club(club: Club) -> dict:
    return {
        'id': club.id,
        'slug': club.slug,
        'public_name': club.public_name,
        'legal_name': club.legal_name,
        'notification_email': club.notification_email,
        'billing_email': club.billing_email,
        'support_email': club.support_email,
        'support_phone': club.support_phone,
        'timezone': club.timezone,
        'currency': club.currency,
        'is_active': club.is_active,
        'created_at': club.created_at,
        'updated_at': club.updated_at,
    }


def _serialize_customer(customer: Customer) -> dict:
    return {
        'id': customer.id,
        'first_name': customer.first_name,
        'last_name': customer.last_name,
        'phone': customer.phone,
        'email': customer.email,
        'note': customer.note,
        'created_at': customer.created_at,
    }


def _serialize_booking(booking: Booking) -> dict:
    return {
        'id': booking.id,
        'public_reference': booking.public_reference,
        'customer_id': booking.customer_id,
        'start_at': booking.start_at,
        'end_at': booking.end_at,
        'booking_date_local': booking.booking_date_local,
        'status': booking.status.value,
        'deposit_amount': float(booking.deposit_amount),
        'payment_provider': booking.payment_provider.value,
        'payment_status': booking.payment_status.value,
        'note': booking.note,
        'created_at': booking.created_at,
        'cancelled_at': booking.cancelled_at,
        'completed_at': booking.completed_at,
        'no_show_at': booking.no_show_at,
    }


def _serialize_payment(payment: BookingPayment) -> dict:
    return {
        'id': payment.id,
        'booking_id': payment.booking_id,
        'provider': payment.provider.value,
        'status': payment.status.value,
        'amount': float(payment.amount),
        'currency': payment.currency,
        'provider_order_id': payment.provider_order_id,
        'provider_capture_id': payment.provider_capture_id,
        'refund_status': payment.refund_status,
        'provider_refund_id': payment.provider_refund_id,
        'refunded_amount': float(payment.refunded_amount) if payment.refunded_amount is not None else None,
        'refunded_at': payment.refunded_at,
        'created_at': payment.created_at,
    }


def export_governance_data(
    db: Session,
    *,
    club_id: str,
    scope: DataExportScope,
    customer_id: str | None = None,
) -> dict:
    club = _get_club_or_404(db, club_id)
    if scope == DataExportScope.CUSTOMER and not customer_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='customer_id obbligatorio per export customer-scoped.',
        )

    customers_query = select(Customer).where(Customer.club_id == club_id).order_by(Customer.created_at.asc())
    if scope == DataExportScope.CUSTOMER:
        _get_customer_or_404(db, club_id, customer_id or '')
        customers_query = customers_query.where(Customer.id == customer_id)
    customers = list(db.scalars(customers_query))

    bookings_query = (
        select(Booking)
        .options(selectinload(Booking.payments))
        .where(Booking.club_id == club_id)
        .order_by(Booking.start_at.asc(), Booking.created_at.asc())
    )
    if scope == DataExportScope.CUSTOMER:
        bookings_query = bookings_query.where(Booking.customer_id == customer_id)
    bookings = list(db.scalars(bookings_query).unique().all())
    booking_ids = [booking.id for booking in bookings]

    email_notifications: list[EmailNotificationLog] = []
    if booking_ids:
        email_notifications = list(
            db.scalars(
                select(EmailNotificationLog)
                .where(EmailNotificationLog.club_id == club_id, EmailNotificationLog.booking_id.in_(booking_ids))
                .order_by(EmailNotificationLog.created_at.asc())
            )
        )

    payments = [payment for booking in bookings for payment in booking.payments]

    tenant_data: dict | None = None
    if scope == DataExportScope.TENANT:
        admins = list(db.scalars(select(Admin).where(Admin.club_id == club_id).order_by(Admin.created_at.asc())))
        app_settings = list(db.scalars(select(AppSetting).where(AppSetting.club_id == club_id).order_by(AppSetting.key.asc())))
        tenant_data = {
            'domains': [
                {
                    'host': domain.host,
                    'is_primary': domain.is_primary,
                    'is_active': domain.is_active,
                    'created_at': domain.created_at,
                }
                for domain in sorted(club.domains, key=lambda item: item.created_at)
            ],
            'admins': [
                {
                    'id': admin.id,
                    'email': admin.email,
                    'full_name': admin.full_name,
                    'role': admin.role.value,
                    'is_active': admin.is_active,
                    'created_at': admin.created_at,
                }
                for admin in admins
            ],
            'settings': [
                {
                    'key': setting.key,
                    'value': setting.value,
                    'updated_at': setting.updated_at,
                }
                for setting in app_settings
            ],
            'subscription': (
                {
                    'plan_code': club.subscription.plan.code if club.subscription and club.subscription.plan else None,
                    'status': club.subscription.status.value if club.subscription else None,
                    'provider': club.subscription.provider if club.subscription else None,
                    'trial_ends_at': club.subscription.trial_ends_at if club.subscription else None,
                    'current_period_end': club.subscription.current_period_end if club.subscription else None,
                    'cancelled_at': club.subscription.cancelled_at if club.subscription else None,
                }
                if club.subscription
                else None
            ),
        }

    return {
        'scope': scope,
        'generated_at': datetime.now(UTC),
        'club': _serialize_club(club),
        'tenant_data': tenant_data,
        'customer_data': {
            'customers': [_serialize_customer(customer) for customer in customers],
            'bookings': [_serialize_booking(booking) for booking in bookings],
            'payments': [_serialize_payment(payment) for payment in payments],
            'email_notifications': [
                {
                    'id': item.id,
                    'booking_id': item.booking_id,
                    'recipient': item.recipient,
                    'template': item.template,
                    'status': item.status,
                    'error': None,
                    'sent_at': item.sent_at,
                    'created_at': item.created_at,
                }
                for item in email_notifications
            ],
        },
    }


def anonymize_customer_data(
    db: Session,
    *,
    club_id: str,
    customer_id: str,
    reason: str | None = None,
    actor: str = 'platform',
) -> dict:
    customer = _get_customer_or_404(db, club_id, customer_id)
    now = datetime.now(UTC)
    future_booking_count = db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(
            Booking.club_id == club_id,
            Booking.customer_id == customer_id,
            Booking.status.in_([BookingStatus.PENDING_PAYMENT, BookingStatus.CONFIRMED]),
            Booking.end_at > now,
        )
    ) or 0
    if future_booking_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Cliente con prenotazioni future attive: usare procedura manuale prima dell\'anonimizzazione.',
        )

    bookings = list(
        db.scalars(
            select(Booking)
            .where(Booking.club_id == club_id, Booking.customer_id == customer_id)
            .order_by(Booking.created_at.asc())
        )
    )
    booking_ids = [booking.id for booking in bookings]
    retained_booking_count = len(bookings)
    retained_payment_count = db.scalar(
        select(func.count())
        .select_from(BookingPayment)
        .join(Booking, Booking.id == BookingPayment.booking_id)
        .where(Booking.club_id == club_id, Booking.customer_id == customer_id)
    ) or 0

    audit_reason = reason.strip() if reason and reason.strip() else None
    anonymized_email = f'anonymized+{customer.id}@{ANONYMIZED_EMAIL_DOMAIN}'
    customer.first_name = 'Anonymized'
    customer.last_name = 'Customer'
    customer.email = anonymized_email
    customer.phone = f'anonymized-{customer.id[:12]}'
    customer.note = None

    redacted_booking_note_count = 0
    for booking in bookings:
        if booking.note is not None:
            booking.note = None
            redacted_booking_note_count += 1

    updated_email_log_count = 0
    if booking_ids:
        email_logs = list(
            db.scalars(
                select(EmailNotificationLog)
                .where(EmailNotificationLog.club_id == club_id, EmailNotificationLog.booking_id.in_(booking_ids))
            )
        )
        for email_log in email_logs:
            email_log.recipient = anonymized_email
        updated_email_log_count = len(email_logs)

    log_event(
        db,
        booking=None,
        event_type='CUSTOMER_ANONYMIZED',
        message='Dati cliente anonimizzati tramite workflow interno',
        actor=actor,
        payload={
            'customer_id': customer.id,
            'reason': audit_reason,
            'retained_booking_count': retained_booking_count,
            'retained_payment_count': retained_payment_count,
            'redacted_booking_note_count': redacted_booking_note_count,
        },
        club_id=club_id,
    )
    db.flush()

    return {
        'status': 'anonymized',
        'club_id': club_id,
        'customer_id': customer.id,
        'anonymized_email': anonymized_email,
        'retained_booking_count': retained_booking_count,
        'retained_payment_count': retained_payment_count,
        'updated_email_log_count': updated_email_log_count,
        'processed_at': now,
    }


def purge_technical_retention_data(
    db: Session,
    *,
    dry_run: bool = False,
    now: datetime | None = None,
) -> dict:
    executed_at = now or datetime.now(UTC)
    retention_days = {
        'email_notifications_log': settings.email_log_retention_days,
        'payment_webhook_events': settings.payment_webhook_retention_days,
        'billing_webhook_events': settings.billing_webhook_retention_days,
    }
    email_cutoff = executed_at - timedelta(days=retention_days['email_notifications_log'])
    payment_cutoff = executed_at - timedelta(days=retention_days['payment_webhook_events'])
    billing_cutoff = executed_at - timedelta(days=retention_days['billing_webhook_events'])

    candidate_counts = {
        'email_notifications_log': db.scalar(
            select(func.count()).select_from(EmailNotificationLog).where(EmailNotificationLog.created_at < email_cutoff)
        ) or 0,
        'payment_webhook_events': db.scalar(
            select(func.count())
            .select_from(PaymentWebhookEvent)
            .where(PaymentWebhookEvent.created_at < payment_cutoff, PaymentWebhookEvent.processed_at.is_not(None))
        ) or 0,
        'billing_webhook_events': db.scalar(
            select(func.count())
            .select_from(BillingWebhookEvent)
            .where(BillingWebhookEvent.created_at < billing_cutoff, BillingWebhookEvent.processed_at.is_not(None))
        ) or 0,
    }

    deleted_counts = {
        'email_notifications_log': 0,
        'payment_webhook_events': 0,
        'billing_webhook_events': 0,
    }

    if not dry_run:
        deleted_counts['email_notifications_log'] = db.execute(
            delete(EmailNotificationLog).where(EmailNotificationLog.created_at < email_cutoff)
        ).rowcount or 0
        deleted_counts['payment_webhook_events'] = db.execute(
            delete(PaymentWebhookEvent).where(
                PaymentWebhookEvent.created_at < payment_cutoff,
                PaymentWebhookEvent.processed_at.is_not(None),
            )
        ).rowcount or 0
        deleted_counts['billing_webhook_events'] = db.execute(
            delete(BillingWebhookEvent).where(
                BillingWebhookEvent.created_at < billing_cutoff,
                BillingWebhookEvent.processed_at.is_not(None),
            )
        ).rowcount or 0

    return {
        'dry_run': dry_run,
        'executed_at': executed_at,
        'retention_days': retention_days,
        'candidate_counts': candidate_counts,
        'deleted_counts': deleted_counts,
    }