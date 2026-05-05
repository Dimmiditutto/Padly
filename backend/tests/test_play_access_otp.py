from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.db import SessionLocal
from app.models import CommunityAccessLink, DEFAULT_CLUB_ID, PlayLevel, Player, PlayerAccessChallenge
from app.services.email_service import email_service
from app.services import play_service as play_service_module
from app.services.play_service import PLAYER_SESSION_COOKIE_NAME, PLAY_ACCESS_OTP_MAX_ATTEMPTS, create_community_access_link, hash_play_token


@pytest.fixture(autouse=True)
def mock_play_access_email_delivery(monkeypatch):
    monkeypatch.setattr(email_service, 'play_access_otp', lambda *args, **kwargs: 'SENT')


def test_play_access_direct_flow_supports_resend_and_sets_cookie_only_after_verify(client, monkeypatch):
    otp_codes = iter(['111111', '222222'])
    monkeypatch.setattr(play_service_module, 'generate_email_otp_code', lambda: next(otp_codes))

    start_response = client.post(
        '/api/public/play-access/start',
        json={
            'purpose': 'DIRECT',
            'profile_name': 'Giulia Smash',
            'phone': '+39 333 111 2222',
            'email': 'giulia@example.com',
            'declared_level': 'INTERMEDIATE_MEDIUM',
            'privacy_accepted': True,
        },
    )

    assert start_response.status_code == 200
    challenge_id = start_response.json()['challenge_id']
    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME) is None

    with SessionLocal() as db:
        challenge = db.get(PlayerAccessChallenge, challenge_id)
        assert challenge is not None
        challenge.last_sent_at = datetime.now(UTC) - timedelta(minutes=2)
        db.commit()

    resend_response = client.post(f'/api/public/play-access/{challenge_id}/resend')

    assert resend_response.status_code == 200
    assert resend_response.json()['challenge_id'] == challenge_id
    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME) is None

    verify_response = client.post(
        '/api/public/play-access/verify',
        json={
            'challenge_id': challenge_id,
            'otp_code': '222222',
        },
    )

    assert verify_response.status_code == 200
    assert verify_response.json()['player']['profile_name'] == 'Giulia Smash'
    assert verify_response.json()['player']['email'] == 'giulia@example.com'
    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME)

    with SessionLocal() as db:
        player = db.query(Player).filter(Player.phone == '+393331112222').one()
        assert player.email == 'giulia@example.com'
        assert player.email_verified_at is not None


def test_play_access_recovery_reactivates_existing_player_by_verified_email(client, monkeypatch):
    monkeypatch.setattr(play_service_module, 'generate_email_otp_code', lambda: '123456')

    with SessionLocal() as db:
        player = Player(
            club_id=DEFAULT_CLUB_ID,
            profile_name='Luca Recovery',
            phone='+393331234567',
            email='luca.recovery@example.com',
            email_verified_at=datetime.now(UTC) - timedelta(days=1),
            declared_level=PlayLevel.INTERMEDIATE_LOW,
            privacy_accepted_at=datetime.now(UTC) - timedelta(days=1),
            is_active=False,
        )
        db.add(player)
        db.commit()
        player_id = player.id

    start_response = client.post(
        '/api/public/play-access/start',
        json={
            'purpose': 'RECOVERY',
            'email': 'luca.recovery@example.com',
            'declared_level': 'NO_PREFERENCE',
            'privacy_accepted': False,
        },
    )

    assert start_response.status_code == 200
    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME) is None

    verify_response = client.post(
        '/api/public/play-access/verify',
        json={
            'challenge_id': start_response.json()['challenge_id'],
            'otp_code': '123456',
        },
    )

    assert verify_response.status_code == 200
    assert verify_response.json()['player']['id'] == player_id
    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME)

    with SessionLocal() as db:
        player = db.get(Player, player_id)
        assert player is not None
        assert player.is_active is True


def test_play_group_access_link_creates_individual_profile_and_consumes_one_use(client, monkeypatch):
    monkeypatch.setattr(play_service_module, 'generate_email_otp_code', lambda: '654321')

    with SessionLocal() as db:
        item, raw_token = create_community_access_link(
            db,
            club_id=DEFAULT_CLUB_ID,
            label='Gruppo Open Match',
            max_uses=2,
        )
        db.commit()
        link_id = item.id

    start_response = client.post(
        '/api/public/play-access/start',
        json={
            'purpose': 'GROUP',
            'group_token': raw_token,
            'profile_name': 'Marco Group',
            'phone': '3338887777',
            'email': 'marco.group@example.com',
            'declared_level': 'ADVANCED',
            'privacy_accepted': True,
        },
    )

    assert start_response.status_code == 200
    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME) is None

    verify_response = client.post(
        '/api/public/play-access/verify',
        json={
            'challenge_id': start_response.json()['challenge_id'],
            'otp_code': '654321',
        },
    )

    assert verify_response.status_code == 200
    assert verify_response.json()['player']['profile_name'] == 'Marco Group'
    assert verify_response.json()['player']['email'] == 'marco.group@example.com'
    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME)

    with SessionLocal() as db:
        item = db.get(CommunityAccessLink, link_id)
        player = db.query(Player).filter(Player.phone == '3338887777').one()
        assert item is not None
        assert item.used_count == 1
        assert item.token_hash == hash_play_token(raw_token)
        assert player.email == 'marco.group@example.com'


def test_play_access_direct_flow_does_not_rebind_existing_player_to_new_email_by_phone_only(client, monkeypatch):
    monkeypatch.setattr(play_service_module, 'generate_email_otp_code', lambda: '112233')

    with SessionLocal() as db:
        player = Player(
            club_id=DEFAULT_CLUB_ID,
            profile_name='Luca Existing',
            phone='+393339998887',
            email='luca.existing@example.com',
            email_verified_at=datetime.now(UTC) - timedelta(days=2),
            declared_level=PlayLevel.INTERMEDIATE_MEDIUM,
            privacy_accepted_at=datetime.now(UTC) - timedelta(days=2),
            is_active=True,
        )
        db.add(player)
        db.commit()
        existing_player_id = player.id

    start_response = client.post(
        '/api/public/play-access/start',
        json={
            'purpose': 'DIRECT',
            'profile_name': 'Luca Existing',
            'phone': '+39 333 999 8887',
            'email': 'attacker@example.com',
            'declared_level': 'INTERMEDIATE_MEDIUM',
            'privacy_accepted': True,
        },
    )

    if start_response.status_code == 200:
        verify_response = client.post(
            '/api/public/play-access/verify',
            json={
                'challenge_id': start_response.json()['challenge_id'],
                'otp_code': '112233',
            },
        )
        assert verify_response.status_code == 409
    else:
        assert start_response.status_code == 409

    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME) is None

    with SessionLocal() as db:
        player = db.get(Player, existing_player_id)
        assert player is not None
        assert player.email == 'luca.existing@example.com'
        assert player.email_verified_at is not None


def test_play_access_direct_flow_invalidates_challenge_after_max_wrong_otp_attempts(client, monkeypatch):
    monkeypatch.setattr(play_service_module, 'generate_email_otp_code', lambda: '555555')

    start_response = client.post(
        '/api/public/play-access/start',
        json={
            'purpose': 'DIRECT',
            'profile_name': 'Giulia Attempts',
            'phone': '+39 333 123 4545',
            'email': 'giulia.attempts@example.com',
            'declared_level': 'INTERMEDIATE_LOW',
            'privacy_accepted': True,
        },
    )

    assert start_response.status_code == 200
    challenge_id = start_response.json()['challenge_id']

    for _ in range(PLAY_ACCESS_OTP_MAX_ATTEMPTS - 1):
        response = client.post(
            '/api/public/play-access/verify',
            json={
                'challenge_id': challenge_id,
                'otp_code': '000000',
            },
        )
        assert response.status_code == 409
        assert response.json()['detail'] == 'Codice OTP non valido'

    locked_response = client.post(
        '/api/public/play-access/verify',
        json={
            'challenge_id': challenge_id,
            'otp_code': '000000',
        },
    )

    assert locked_response.status_code == 409
    assert locked_response.json()['detail'] == 'Troppi tentativi. Richiedi un nuovo codice'
    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME) is None

    verify_response = client.post(
        '/api/public/play-access/verify',
        json={
            'challenge_id': challenge_id,
            'otp_code': '555555',
        },
    )

    assert verify_response.status_code == 409
    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME) is None

    with SessionLocal() as db:
        challenge = db.get(PlayerAccessChallenge, challenge_id)
        assert challenge is not None
        assert challenge.attempt_count == PLAY_ACCESS_OTP_MAX_ATTEMPTS
        assert challenge.verified_at is None
        expires_at = challenge.expires_at if challenge.expires_at.tzinfo else challenge.expires_at.replace(tzinfo=UTC)
        assert expires_at <= datetime.now(UTC)


def test_play_access_start_fails_explicitly_when_email_provider_is_not_configured(client, monkeypatch):
    monkeypatch.setattr(email_service, 'play_access_otp', lambda *args, **kwargs: 'SKIPPED')

    response = client.post(
        '/api/public/play-access/start',
        json={
            'purpose': 'DIRECT',
            'profile_name': 'Giulia Local',
            'phone': '+39 333 111 0000',
            'email': 'giulia.local@example.com',
            'declared_level': 'INTERMEDIATE_LOW',
            'privacy_accepted': True,
        },
    )

    assert response.status_code == 503
    assert response.json()['detail'] == 'Provider email non configurato in questo ambiente. Configura Resend o SMTP per inviare il codice OTP.'