import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import (
    Admin,
    AppSetting,
    BillingWebhookEvent,
    Booking,
    BookingEventLog,
    BookingPayment,
    BookingSource,
    BookingStatus,
    Club,
    ClubDomain,
    Customer,
    DEFAULT_CLUB_ID,
    EmailNotificationLog,
    PaymentProvider,
    PaymentStatus,
    PaymentWebhookEvent,
)
from app.services.booking_service import log_event
from app.services.billing_service import get_or_create_trial_subscription

PLATFORM_KEY = 'test-platform-key-fase8'


@pytest.fixture(autouse=True)
def set_platform_key(monkeypatch):
    from app.core import config as cfg

    monkeypatch.setattr(cfg.settings, 'platform_api_key', PLATFORM_KEY)


def create_tenant(
    db: Session,
    *,
    slug: str,
    host: str,
    admin_email: str,
    admin_password: str = 'SecurePass123!',
) -> dict[str, str]:
    club = Club(
        slug=slug,
        public_name=f'{slug.title()} Club',
        notification_email=f'ops@{slug}.example',
        billing_email=f'billing@{slug}.example',
        support_email=f'support@{slug}.example',
        support_phone='+39021111222',
        timezone='Europe/Rome',
        currency='EUR',
        is_active=True,
    )
    db.add(club)
    db.flush()
    db.add(ClubDomain(club_id=club.id, host=host, is_primary=True, is_active=True))
    db.add(
        Admin(
            club_id=club.id,
            email=admin_email,
            full_name=f'Admin {slug.title()}',
            password_hash=hash_password(admin_password),
        )
    )
    db.add(AppSetting(club_id=club.id, key='booking_rules', value={'slot_duration_minutes': 90}))
    get_or_create_trial_subscription(db, club)
    db.commit()
    return {
        'id': club.id,
        'slug': club.slug,
        'host': host,
        'admin_email': admin_email,
    }


def create_customer_booking_bundle(
    db: Session,
    *,
    club_id: str,
    email: str,
    phone: str,
    days_offset: int,
    booking_status: BookingStatus,
    payment_status: PaymentStatus,
) -> dict[str, str]:
    customer = Customer(
        club_id=club_id,
        first_name='Alice',
        last_name='Tenant',
        phone=phone,
        email=email,
        note='Customer export test',
    )
    db.add(customer)
    db.flush()

    start_at = datetime.now(UTC).replace(microsecond=0) + timedelta(days=days_offset)
    booking = Booking(
        club_id=club_id,
        public_reference=f'PB-{uuid.uuid4().hex[:8].upper()}',
        customer_id=customer.id,
        start_at=start_at,
        end_at=start_at + timedelta(minutes=90),
        duration_minutes=90,
        booking_date_local=(date.today() + timedelta(days=days_offset)),
        status=booking_status,
        deposit_amount=Decimal('20.00'),
        payment_provider=PaymentProvider.STRIPE,
        payment_status=payment_status,
        payment_reference=f'pay-ref-{uuid.uuid4().hex[:10]}',
        note='Governance seed booking',
        cancel_token=f'cancel-{uuid.uuid4().hex}',
        created_by='test-suite',
        source=BookingSource.PUBLIC,
    )
    db.add(booking)
    db.flush()

    payment = BookingPayment(
        booking_id=booking.id,
        provider=PaymentProvider.STRIPE,
        status=payment_status,
        amount=Decimal('20.00'),
        currency='EUR',
        provider_order_id=f'order-{uuid.uuid4().hex[:12]}',
        provider_capture_id=f'capture-{uuid.uuid4().hex[:12]}',
    )
    db.add(payment)
    db.flush()

    email_log = EmailNotificationLog(
        club_id=club_id,
        booking_id=booking.id,
        recipient=email,
        template='booking_confirmation',
        status='SENT',
        sent_at=datetime.now(UTC).replace(microsecond=0),
    )
    db.add(email_log)
    db.commit()

    return {
        'customer_id': customer.id,
        'booking_id': booking.id,
        'payment_id': payment.id,
        'email_log_id': email_log.id,
    }


def test_platform_tenant_export_returns_filtered_tenant_dataset(client):
    with SessionLocal() as db:
        tenant = create_tenant(db, slug='export-club', host='export.example.test', admin_email='owner@export.example')
        bundle = create_customer_booking_bundle(
            db,
            club_id=tenant['id'],
            email='alice.export@example.com',
            phone='3331110001',
            days_offset=-5,
            booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
        )
        email_log = db.scalar(select(EmailNotificationLog).where(EmailNotificationLog.id == bundle['email_log_id']))
        assert email_log is not None
        email_log.status = 'FAILED'
        email_log.error = 'SMTP rejected recipient alice.export@example.com'
        db.commit()
        create_customer_booking_bundle(
            db,
            club_id=DEFAULT_CLUB_ID,
            email='legacy@example.com',
            phone='3339990001',
            days_offset=-3,
            booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
        )

    response = client.get(
        f"/api/platform/tenants/{tenant['id']}/data-export",
        headers={'x-platform-key': PLATFORM_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['scope'] == 'tenant'
    assert payload['club']['id'] == tenant['id']
    assert payload['tenant_data']['admins'][0]['email'] == tenant['admin_email']
    assert 'password_hash' not in payload['tenant_data']['admins'][0]
    assert payload['tenant_data']['settings'][0]['key'] == 'booking_rules'
    assert [item['id'] for item in payload['customer_data']['customers']] == [bundle['customer_id']]
    assert [item['id'] for item in payload['customer_data']['bookings']] == [bundle['booking_id']]
    assert [item['booking_id'] for item in payload['customer_data']['payments']] == [bundle['booking_id']]
    assert [item['booking_id'] for item in payload['customer_data']['email_notifications']] == [bundle['booking_id']]
    assert payload['customer_data']['email_notifications'][0]['template'] == 'booking_confirmation'
    assert payload['customer_data']['email_notifications'][0]['status'] == 'FAILED'
    assert payload['customer_data']['email_notifications'][0]['error'] is None

    with SessionLocal() as db:
        stored_email_log = db.scalar(select(EmailNotificationLog).where(EmailNotificationLog.id == bundle['email_log_id']))

    assert stored_email_log is not None
    assert stored_email_log.error == 'SMTP rejected recipient alice.export@example.com'


def test_platform_customer_export_filters_single_customer_dataset(client):
    with SessionLocal() as db:
        tenant = create_tenant(db, slug='customer-export', host='customer-export.example.test', admin_email='owner@customer-export.example')
        alice = create_customer_booking_bundle(
            db,
            club_id=tenant['id'],
            email='alice.customer@example.com',
            phone='3331110002',
            days_offset=-2,
            booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
        )
        alice_email_log = db.scalar(select(EmailNotificationLog).where(EmailNotificationLog.id == alice['email_log_id']))
        assert alice_email_log is not None
        alice_email_log.status = 'FAILED'
        alice_email_log.error = 'SMTP rejected recipient alice.customer@example.com'
        db.commit()
        create_customer_booking_bundle(
            db,
            club_id=tenant['id'],
            email='bob.customer@example.com',
            phone='3331110003',
            days_offset=-1,
            booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
        )

    response = client.get(
        f"/api/platform/tenants/{tenant['id']}/data-export",
        params={'scope': 'customer', 'customer_id': alice['customer_id']},
        headers={'x-platform-key': PLATFORM_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['scope'] == 'customer'
    assert payload['tenant_data'] is None
    assert [item['id'] for item in payload['customer_data']['customers']] == [alice['customer_id']]
    assert {item['customer_id'] for item in payload['customer_data']['bookings']} == {alice['customer_id']}
    assert {item['booking_id'] for item in payload['customer_data']['payments']} == {alice['booking_id']}
    assert {item['recipient'] for item in payload['customer_data']['email_notifications']} == {'alice.customer@example.com'}
    assert payload['customer_data']['email_notifications'][0]['status'] == 'FAILED'
    assert payload['customer_data']['email_notifications'][0]['error'] is None


def test_customer_anonymization_preserves_bookings_and_updates_logs(client):
    with SessionLocal() as db:
        tenant = create_tenant(db, slug='anon-club', host='anon.example.test', admin_email='owner@anon.example')
        bundle = create_customer_booking_bundle(
            db,
            club_id=tenant['id'],
            email='anon.customer@example.com',
            phone='3331110004',
            days_offset=-7,
            booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
        )
        booking = db.scalar(select(Booking).where(Booking.id == bundle['booking_id']))
        email_log = db.scalar(select(EmailNotificationLog).where(EmailNotificationLog.id == bundle['email_log_id']))
        assert booking is not None
        assert email_log is not None
        booking.note = 'Customer private note to redact'
        email_log.error = 'SMTP rejected recipient anon.customer@example.com'
        db.commit()

    response = client.post(
        f"/api/platform/tenants/{tenant['id']}/customers/{bundle['customer_id']}/anonymize",
        json={'reason': 'GDPR request', 'actor': 'support'},
        headers={'x-platform-key': PLATFORM_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'anonymized'
    assert payload['retained_booking_count'] == 1
    assert payload['retained_payment_count'] == 1
    assert payload['updated_email_log_count'] == 1

    with SessionLocal() as db:
        customer = db.scalar(select(Customer).where(Customer.id == bundle['customer_id']))
        booking = db.scalar(select(Booking).where(Booking.id == bundle['booking_id']))
        email_log = db.scalar(select(EmailNotificationLog).where(EmailNotificationLog.id == bundle['email_log_id']))
        audit = db.scalar(select(BookingEventLog).where(BookingEventLog.event_type == 'CUSTOMER_ANONYMIZED'))

    assert customer is not None
    assert booking is not None
    assert email_log is not None
    assert audit is not None
    assert customer.first_name == 'Anonymized'
    assert customer.email.endswith('@redacted.local')
    assert customer.note is None
    assert booking.customer_id == bundle['customer_id']
    assert booking.note is None
    assert email_log.recipient == customer.email
    assert audit.club_id == tenant['id']
    assert audit.actor == 'support'
    assert audit.payload is not None
    assert audit.payload['reason'] == 'GDPR request'

    export_response = client.get(
        f"/api/platform/tenants/{tenant['id']}/data-export",
        params={'scope': 'customer', 'customer_id': bundle['customer_id']},
        headers={'x-platform-key': PLATFORM_KEY},
    )

    assert export_response.status_code == 200
    export_payload = export_response.json()
    assert export_payload['tenant_data'] is None
    assert export_payload['customer_data']['customers'][0]['note'] is None
    assert export_payload['customer_data']['bookings'][0]['note'] is None
    assert export_payload['customer_data']['email_notifications'][0]['error'] is None


def test_customer_anonymization_rejects_future_active_bookings(client):
    with SessionLocal() as db:
        tenant = create_tenant(db, slug='future-anon', host='future-anon.example.test', admin_email='owner@future-anon.example')
        bundle = create_customer_booking_bundle(
            db,
            club_id=tenant['id'],
            email='future.customer@example.com',
            phone='3331110005',
            days_offset=2,
            booking_status=BookingStatus.CONFIRMED,
            payment_status=PaymentStatus.PAID,
        )

    response = client.post(
        f"/api/platform/tenants/{tenant['id']}/customers/{bundle['customer_id']}/anonymize",
        json={'reason': 'Should fail'},
        headers={'x-platform-key': PLATFORM_KEY},
    )

    assert response.status_code == 409
    assert 'prenotazioni future attive' in response.json()['detail']


def test_technical_retention_purge_deletes_only_old_processed_records(client, monkeypatch):
    monkeypatch.setattr(settings, 'email_log_retention_days', 30)
    monkeypatch.setattr(settings, 'payment_webhook_retention_days', 60)
    monkeypatch.setattr(settings, 'billing_webhook_retention_days', 90)

    old_timestamp = datetime.now(UTC).replace(microsecond=0) - timedelta(days=120)
    recent_timestamp = datetime.now(UTC).replace(microsecond=0) - timedelta(days=5)

    with SessionLocal() as db:
        tenant = create_tenant(db, slug='retention-club', host='retention.example.test', admin_email='owner@retention.example')
        seeded = create_customer_booking_bundle(
            db,
            club_id=tenant['id'],
            email='retention.customer@example.com',
            phone='3331110006',
            days_offset=-10,
            booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
        )

        old_email = EmailNotificationLog(
            club_id=tenant['id'],
            booking_id=seeded['booking_id'],
            recipient='old@example.com',
            template='old-template',
            status='FAILED',
            created_at=old_timestamp,
        )
        recent_email = EmailNotificationLog(
            club_id=tenant['id'],
            booking_id=seeded['booking_id'],
            recipient='recent@example.com',
            template='recent-template',
            status='SENT',
            created_at=recent_timestamp,
        )
        old_payment_webhook = PaymentWebhookEvent(
            provider='stripe',
            event_id=f'evt-payment-old-{uuid.uuid4().hex[:8]}',
            event_type='payment_intent.succeeded',
            payload={'id': 'old-payment'},
            processed_at=old_timestamp,
            created_at=old_timestamp,
        )
        old_unprocessed_payment_webhook = PaymentWebhookEvent(
            provider='stripe',
            event_id=f'evt-payment-open-{uuid.uuid4().hex[:8]}',
            event_type='payment_intent.payment_failed',
            payload={'id': 'open-payment'},
            processed_at=None,
            created_at=old_timestamp,
        )
        old_billing_webhook = BillingWebhookEvent(
            provider='stripe',
            event_id=f'evt-billing-old-{uuid.uuid4().hex[:8]}',
            event_type='invoice.payment_failed',
            club_id=tenant['id'],
            payload={'id': 'old-billing'},
            processed_at=old_timestamp,
            created_at=old_timestamp,
        )
        recent_billing_webhook = BillingWebhookEvent(
            provider='stripe',
            event_id=f'evt-billing-recent-{uuid.uuid4().hex[:8]}',
            event_type='invoice.payment_failed',
            club_id=tenant['id'],
            payload={'id': 'recent-billing'},
            processed_at=recent_timestamp,
            created_at=recent_timestamp,
        )
        db.add_all(
            [
                old_email,
                recent_email,
                old_payment_webhook,
                old_unprocessed_payment_webhook,
                old_billing_webhook,
                recent_billing_webhook,
            ]
        )
        db.commit()

        old_email_id = old_email.id
        recent_email_id = recent_email.id
        old_payment_webhook_id = old_payment_webhook.id
        old_unprocessed_payment_webhook_id = old_unprocessed_payment_webhook.id
        old_billing_webhook_id = old_billing_webhook.id
        recent_billing_webhook_id = recent_billing_webhook.id
        booking_id = seeded['booking_id']

    preview = client.post('/api/platform/data-retention/purge?dry_run=true', headers={'x-platform-key': PLATFORM_KEY})

    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload['dry_run'] is True
    assert preview_payload['candidate_counts'] == {
        'email_notifications_log': 1,
        'payment_webhook_events': 1,
        'billing_webhook_events': 1,
    }

    execute = client.post('/api/platform/data-retention/purge', headers={'x-platform-key': PLATFORM_KEY})

    assert execute.status_code == 200
    execute_payload = execute.json()
    assert execute_payload['dry_run'] is False
    assert execute_payload['deleted_counts'] == {
        'email_notifications_log': 1,
        'payment_webhook_events': 1,
        'billing_webhook_events': 1,
    }

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(EmailNotificationLog).where(EmailNotificationLog.id == old_email_id)) == 0
        assert db.scalar(select(func.count()).select_from(EmailNotificationLog).where(EmailNotificationLog.id == recent_email_id)) == 1
        assert db.scalar(select(func.count()).select_from(PaymentWebhookEvent).where(PaymentWebhookEvent.id == old_payment_webhook_id)) == 0
        assert db.scalar(select(func.count()).select_from(PaymentWebhookEvent).where(PaymentWebhookEvent.id == old_unprocessed_payment_webhook_id)) == 1
        assert db.scalar(select(func.count()).select_from(BillingWebhookEvent).where(BillingWebhookEvent.id == old_billing_webhook_id)) == 0
        assert db.scalar(select(func.count()).select_from(BillingWebhookEvent).where(BillingWebhookEvent.id == recent_billing_webhook_id)) == 1
        assert db.scalar(select(func.count()).select_from(Booking).where(Booking.id == booking_id)) == 1


def test_historical_governance_audit_dry_run_classifies_records_without_exposing_raw_payloads(client):
    booking_email = 'history.booking@example.com'
    booking_phone = '+39 333 444 5555'
    booking_note = 'Private customer note for audit'
    webhook_email = 'history.webhook@example.com'

    with SessionLocal() as db:
        tenant = create_tenant(db, slug='history-audit', host='history-audit.example.test', admin_email='owner@history-audit.example')
        bundle = create_customer_booking_bundle(
            db,
            club_id=tenant['id'],
            email='seed.history@example.com',
            phone='3331111000',
            days_offset=-4,
            booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
        )
        booking = db.scalar(select(Booking).where(Booking.id == bundle['booking_id']))
        assert booking is not None
        log_event(
            db,
            booking,
            'BOOKING_UPDATED',
            f'Cliente aggiornato con contatto {booking_email} e telefono {booking_phone}',
            actor='support',
            payload={'note': booking_note, 'customer_email': booking_email, 'customer_phone': booking_phone},
        )
        db.add(
            PaymentWebhookEvent(
                provider='stripe',
                event_id=f'evt-payment-history-{uuid.uuid4().hex[:8]}',
                event_type='payment_intent.succeeded',
                payload={'data': {'object': {'object': 'payment_intent', 'receipt_email': webhook_email}}},
                processed_at=datetime.now(UTC),
            )
        )
        db.add(
            BillingWebhookEvent(
                provider='stripe',
                event_id=f'evt-billing-history-{uuid.uuid4().hex[:8]}',
                event_type='invoice.payment_failed',
                club_id=tenant['id'],
                payload={'data': {'object': {'object': 'invoice', 'customer_email': webhook_email}}},
                processed_at=datetime.now(UTC),
            )
        )
        db.add(
            EmailNotificationLog(
                club_id=tenant['id'],
                booking_id=bundle['booking_id'],
                recipient='history-error@example.com',
                template='smtp_failure',
                status='FAILED',
                error=f'SMTP rejected recipient {booking_email}',
            )
        )
        db.commit()

    response = client.post(
        '/api/platform/data-governance/historical-audit',
        params={'dry_run': 'true', 'window_days': 30, 'sample_limit': 10},
        headers={'x-platform-key': PLATFORM_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['dry_run'] is True
    assert payload['redaction_counts']['booking_events_log'] == 0
    assert booking_email not in response.text
    assert booking_phone not in response.text
    assert booking_note not in response.text
    assert webhook_email not in response.text

    summaries = {item['table_name']: item for item in payload['table_summaries']}
    assert summaries['booking_events_log']['classification_counts']['safe_to_redact'] >= 1
    assert summaries['payment_webhook_events']['classification_counts']['needs_manual_review'] >= 1
    assert summaries['billing_webhook_events']['classification_counts']['needs_manual_review'] >= 1
    assert summaries['email_notifications_log']['classification_counts']['needs_manual_review'] >= 1
    booking_sample = summaries['booking_events_log']['samples'][0]
    payment_sample = summaries['payment_webhook_events']['samples'][0]
    billing_sample = summaries['billing_webhook_events']['samples'][0]
    assert booking_sample['redaction_supported'] is True
    assert booking_sample['classification'] == 'safe_to_redact'
    assert payment_sample['review_projection']['provider'] == 'stripe'
    assert payment_sample['review_projection']['event_type'] == 'payment_intent.succeeded'
    assert payment_sample['review_projection']['indicator_count'] >= 1
    assert 'payload.data.object.receipt_email' in payment_sample['review_projection']['sensitive_paths']
    assert payment_sample['review_projection']['safe_preview']['object_type'] == 'payment_intent'
    assert 'receipt_email' in payment_sample['review_projection']['safe_preview']['sensitive_fields_present']
    assert billing_sample['review_projection']['provider'] == 'stripe'
    assert billing_sample['review_projection']['event_type'] == 'invoice.payment_failed'
    assert 'payload.data.object.customer_email' in billing_sample['review_projection']['sensitive_paths']
    assert billing_sample['review_projection']['safe_preview']['object_type'] == 'invoice'


def test_historical_governance_audit_can_redact_only_safe_booking_events_and_keep_webhooks_unchanged(client):
    booking_email = 'redact.booking@example.com'
    booking_phone = '+39 320 111 2222'
    payment_event_id = f'evt-payment-redaction-{uuid.uuid4().hex[:8]}'
    billing_event_id = f'evt-billing-redaction-{uuid.uuid4().hex[:8]}'

    with SessionLocal() as db:
        tenant = create_tenant(db, slug='history-redact', host='history-redact.example.test', admin_email='owner@history-redact.example')
        bundle = create_customer_booking_bundle(
            db,
            club_id=tenant['id'],
            email='seed.redaction@example.com',
            phone='3331111001',
            days_offset=-6,
            booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
        )
        booking = db.scalar(select(Booking).where(Booking.id == bundle['booking_id']))
        assert booking is not None
        log_event(
            db,
            booking,
            'BOOKING_UPDATED',
            f'Contatto cliente aggiornato: {booking_email} {booking_phone}',
            actor='support',
            payload={'note': 'history note', 'customer_email': booking_email, 'customer_phone': booking_phone},
        )
        payment_webhook = PaymentWebhookEvent(
            provider='stripe',
            event_id=payment_event_id,
            event_type='payment_intent.succeeded',
            payload={'data': {'object': {'receipt_email': 'webhook.redaction@example.com'}}},
            processed_at=datetime.now(UTC),
        )
        billing_webhook = BillingWebhookEvent(
            provider='stripe',
            event_id=billing_event_id,
            event_type='invoice.payment_failed',
            club_id=tenant['id'],
            payload={'data': {'object': {'customer_email': 'billing.redaction@example.com'}}},
            processed_at=datetime.now(UTC),
        )
        db.add(payment_webhook)
        db.add(billing_webhook)
        db.commit()
        payment_webhook_id = payment_webhook.id
        billing_webhook_id = billing_webhook.id

    response = client.post(
        '/api/platform/data-governance/historical-audit',
        params={'dry_run': 'false', 'window_days': 30, 'sample_limit': 10},
        headers={'x-platform-key': PLATFORM_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['dry_run'] is False
    assert payload['redaction_counts']['booking_events_log'] >= 1
    assert payload['redaction_counts']['payment_webhook_events'] == 0
    assert payload['redaction_counts']['billing_webhook_events'] == 0

    with SessionLocal() as db:
        redacted_event = db.scalar(select(BookingEventLog).where(BookingEventLog.event_type == 'BOOKING_UPDATED').order_by(BookingEventLog.created_at.desc()))
        stored_payment_webhook = db.scalar(select(PaymentWebhookEvent).where(PaymentWebhookEvent.id == payment_webhook_id))
        stored_billing_webhook = db.scalar(select(BillingWebhookEvent).where(BillingWebhookEvent.id == billing_webhook_id))

    assert redacted_event is not None
    assert booking_email not in redacted_event.message
    assert booking_phone not in redacted_event.message
    assert redacted_event.payload is not None
    assert redacted_event.payload['note'] == '[redacted]'
    assert redacted_event.payload['customer_email'] == '[redacted]'
    assert redacted_event.payload['customer_phone'] == '[redacted]'
    assert stored_payment_webhook is not None
    assert stored_payment_webhook.payload['data']['object']['receipt_email'] == 'webhook.redaction@example.com'
    assert stored_billing_webhook is not None
    assert stored_billing_webhook.payload['data']['object']['customer_email'] == 'billing.redaction@example.com'


def test_historical_governance_audit_ignores_empty_or_already_redacted_booking_payloads(client):
    with SessionLocal() as db:
        tenant = create_tenant(db, slug='history-empty', host='history-empty.example.test', admin_email='owner@history-empty.example')
        bundle = create_customer_booking_bundle(
            db,
            club_id=tenant['id'],
            email='seed.empty@example.com',
            phone='3331111003',
            days_offset=-3,
            booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
        )
        booking = db.scalar(select(Booking).where(Booking.id == bundle['booking_id']))
        assert booking is not None
        log_event(
            db,
            booking,
            'BOOKING_UPDATED',
            'Evento tecnico senza PII residua',
            actor='support',
            payload={'before': {'note': None}, 'after': {'note': '[redacted]'}},
        )
        db.commit()

    response = client.post(
        '/api/platform/data-governance/historical-audit',
        params={'dry_run': 'true', 'window_days': 30, 'sample_limit': 10},
        headers={'x-platform-key': PLATFORM_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    booking_summary = next(item for item in payload['table_summaries'] if item['table_name'] == 'booking_events_log')
    assert booking_summary['classification_counts']['safe_to_redact'] == 0
    assert booking_summary['classification_counts']['keep_for_audit'] >= 1


def test_historical_governance_audit_redaction_is_idempotent_for_booking_events(client):
    with SessionLocal() as db:
        tenant = create_tenant(
            db,
            slug='history-idempotent',
            host='history-idempotent.example.test',
            admin_email='owner@history-idempotent.example',
        )
        bundle = create_customer_booking_bundle(
            db,
            club_id=tenant['id'],
            email='seed.idempotent@example.com',
            phone='3331111004',
            days_offset=-3,
            booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
        )
        booking = db.scalar(select(Booking).where(Booking.id == bundle['booking_id']))
        assert booking is not None
        log_event(
            db,
            booking,
            'BOOKING_UPDATED',
            'Contatto cliente aggiornato: idempotent.booking@example.com +39 333 000 9999',
            actor='support',
            payload={
                'note': 'idempotent history note',
                'customer_email': 'idempotent.booking@example.com',
                'customer_phone': '+39 333 000 9999',
            },
        )
        db.commit()

    first_response = client.post(
        '/api/platform/data-governance/historical-audit',
        params={'dry_run': 'false', 'window_days': 30, 'sample_limit': 10},
        headers={'x-platform-key': PLATFORM_KEY},
    )

    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload['redaction_counts']['booking_events_log'] == 1

    second_response = client.post(
        '/api/platform/data-governance/historical-audit',
        params={'dry_run': 'false', 'window_days': 30, 'sample_limit': 10},
        headers={'x-platform-key': PLATFORM_KEY},
    )

    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload['redaction_counts']['booking_events_log'] == 0


def test_historical_governance_audit_webhook_review_projection_stays_useful_without_provider_preview(client):
    webhook_email = 'fallback.review@example.com'

    with SessionLocal() as db:
        db.add(
            PaymentWebhookEvent(
                provider='legacy-gateway',
                event_id=f'evt-payment-fallback-{uuid.uuid4().hex[:8]}',
                event_type='legacy.event.received',
                payload={'metadata': {'billing_email': webhook_email}},
                processed_at=datetime.now(UTC),
            )
        )
        db.commit()

    response = client.post(
        '/api/platform/data-governance/historical-audit',
        params={'dry_run': 'true', 'window_days': 30, 'sample_limit': 10},
        headers={'x-platform-key': PLATFORM_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    assert webhook_email not in response.text

    payment_summary = next(item for item in payload['table_summaries'] if item['table_name'] == 'payment_webhook_events')
    sample = payment_summary['samples'][0]
    assert sample['classification'] == 'needs_manual_review'
    assert sample['review_projection']['provider'] == 'legacy-gateway'
    assert sample['review_projection']['event_type'] == 'legacy.event.received'
    assert sample['review_projection']['indicator_count'] >= 1
    assert 'payload.metadata.billing_email' in sample['review_projection']['sensitive_paths']
    assert sample['review_projection']['safe_preview'] is None


def test_historical_governance_audit_supports_default_tenant_legacy_records(client):
    with SessionLocal() as db:
        bundle = create_customer_booking_bundle(
            db,
            club_id=DEFAULT_CLUB_ID,
            email='legacy.history@example.com',
            phone='3331111002',
            days_offset=-2,
            booking_status=BookingStatus.COMPLETED,
            payment_status=PaymentStatus.PAID,
        )
        booking = db.scalar(select(Booking).where(Booking.id == bundle['booking_id']))
        assert booking is not None
        log_event(db, booking, 'LEGACY_HISTORY_EVENT', 'Legacy history smoke event', actor='system')
        db.commit()

    response = client.post(
        '/api/platform/data-governance/historical-audit',
        params={'dry_run': 'true', 'window_days': 30},
        headers={'x-platform-key': PLATFORM_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    booking_summary = next(item for item in payload['table_summaries'] if item['table_name'] == 'booking_events_log')
    assert booking_summary['scanned_count'] >= 1
    assert booking_summary['tenant_counts'][DEFAULT_CLUB_ID] >= 1