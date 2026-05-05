from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.services import play_service as play_service_module
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import Club, ClubDomain, CommunityAccessLink, CommunityInviteToken, Court, DEFAULT_CLUB_ID, Match, MatchPlayer, MatchStatus, PlayLevel, Player
from app.services.email_service import email_service
from app.services.play_service import PLAYER_SESSION_COOKIE_NAME, build_club_player_session_cookie_name, create_community_invite, hash_play_token


def tenant_headers(host: str) -> dict[str, str]:
    return {'host': host}


def create_secondary_tenant(
    *,
    slug: str = 'play-roma',
    host: str = 'play-roma.example.test',
    public_name: str = 'Play Roma',
) -> dict[str, str]:
    with SessionLocal() as db:
        club = Club(
            slug=slug,
            public_name=public_name,
            notification_email=f'ops@{slug}.example',
            support_email=f'support@{slug}.example',
            support_phone='+39021234567',
            timezone='Europe/Rome',
            currency='EUR',
            is_active=True,
        )
        db.add(club)
        db.flush()
        db.add(ClubDomain(club_id=club.id, host=host, is_primary=True, is_active=True))
        db.commit()
        return {'id': club.id, 'slug': club.slug, 'host': host}


def first_court_id_for_club(club_id: str) -> str:
    with SessionLocal() as db:
        court = db.query(Court).filter(Court.club_id == club_id).order_by(Court.sort_order.asc(), Court.created_at.asc()).first()
        assert court is not None
        return court.id


def seed_player(*, club_id: str, profile_name: str, phone: str, declared_level: PlayLevel = PlayLevel.NO_PREFERENCE) -> str:
    with SessionLocal() as db:
        player = Player(
            club_id=club_id,
            profile_name=profile_name,
            phone=phone,
            declared_level=declared_level,
            privacy_accepted_at=datetime.now(UTC),
            is_active=True,
        )
        db.add(player)
        db.commit()
        return player.id


def seed_match(
    *,
    club_id: str,
    court_id: str,
    creator_player_id: str,
    participant_player_ids: list[str],
    hours_from_now: int,
    level_requested: PlayLevel = PlayLevel.NO_PREFERENCE,
    note: str | None = None,
) -> str:
    with SessionLocal() as db:
        start_at = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=hours_from_now)
        match = Match(
            club_id=club_id,
            court_id=court_id,
            created_by_player_id=creator_player_id,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=90),
            duration_minutes=90,
            status=MatchStatus.OPEN,
            level_requested=level_requested,
            note=note,
            public_share_token_hash=hash_play_token(f'share-{uuid4().hex}'),
        )
        db.add(match)
        db.flush()
        for player_id in participant_player_ids:
            db.add(MatchPlayer(match_id=match.id, player_id=player_id))
        db.commit()
        return match.id


def test_play_identify_sets_cookie_and_me_reads_player(client):
    response = client.post(
        '/api/play/identify',
        json={
            'profile_name': 'Giulia Spin',
            'phone': '+39 333 111 2222',
            'declared_level': 'INTERMEDIATE_MEDIUM',
            'privacy_accepted': True,
        },
    )

    assert response.status_code == 200
    assert response.json()['player']['profile_name'] == 'Giulia Spin'
    raw_cookie = client.cookies.get(PLAYER_SESSION_COOKIE_NAME)
    assert raw_cookie

    me_response = client.get('/api/play/me')
    assert me_response.status_code == 200
    assert me_response.json()['player']['phone'] == '+393331112222'
    push_state = me_response.json()['notification_settings']['push']
    assert push_state['push_supported'] is True
    assert push_state['public_vapid_key']
    assert push_state['service_worker_path'] == '/play-service-worker.js'

    with SessionLocal() as db:
        stored_token = db.query(Player).filter(Player.phone == '+393331112222').one()
        access_token = stored_token.access_tokens[0]
        assert access_token.token_hash != raw_cookie
        assert len(access_token.token_hash) == 64


def test_play_me_without_cookie_returns_null_player(client):
    response = client.get('/api/play/me')

    assert response.status_code == 200
    assert response.json()['player'] is None


def test_play_matches_are_ordered_by_fill_level_and_scoped_to_current_club(client):
    secondary = create_secondary_tenant()

    identify_response = client.post(
        '/api/play/identify',
        json={
            'profile_name': 'Marco Lobby',
            'phone': '3334445555',
            'declared_level': 'INTERMEDIATE_LOW',
            'privacy_accepted': True,
        },
    )
    assert identify_response.status_code == 200
    current_player_id = identify_response.json()['player']['id']

    default_court_id = first_court_id_for_club(DEFAULT_CLUB_ID)
    player_two = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Player Two', phone='3330000002')
    player_three = seed_player(club_id=DEFAULT_CLUB_ID, profile_name='Player Three', phone='3330000003')

    one_of_four = seed_match(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=current_player_id,
        participant_player_ids=[current_player_id],
        hours_from_now=48,
        note='1 su 4',
    )
    two_of_four = seed_match(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=current_player_id,
        participant_player_ids=[current_player_id, player_two],
        hours_from_now=24,
        note='2 su 4',
    )
    three_of_four = seed_match(
        club_id=DEFAULT_CLUB_ID,
        court_id=default_court_id,
        creator_player_id=current_player_id,
        participant_player_ids=[current_player_id, player_two, player_three],
        hours_from_now=36,
        note='3 su 4',
    )

    secondary_court_id = first_court_id_for_club(secondary['id'])
    secondary_player = seed_player(club_id=secondary['id'], profile_name='Tenant Other', phone='3331231234')
    secondary_guest = seed_player(club_id=secondary['id'], profile_name='Tenant Guest', phone='3331231235')
    secondary_guest_two = seed_player(club_id=secondary['id'], profile_name='Tenant Guest Two', phone='3331231236')
    seed_match(
        club_id=secondary['id'],
        court_id=secondary_court_id,
        creator_player_id=secondary_player,
        participant_player_ids=[secondary_player, secondary_guest, secondary_guest_two],
        hours_from_now=12,
        note='tenant secondario',
    )

    response = client.get('/api/play/matches')

    assert response.status_code == 200
    payload = response.json()
    assert [match['id'] for match in payload['open_matches']] == [three_of_four, two_of_four, one_of_four]
    assert {match['id'] for match in payload['my_matches']} == {three_of_four, two_of_four, one_of_four}
    assert all(match['note'] != 'tenant secondario' for match in payload['open_matches'])


def test_community_invite_access_requires_verified_otp_before_session(client, monkeypatch):
    monkeypatch.setattr(play_service_module, 'generate_email_otp_code', lambda: '123456')
    monkeypatch.setattr(email_service, 'play_access_otp', lambda *args, **kwargs: 'SENT')

    with SessionLocal() as db:
        valid_invite, valid_raw_token = create_community_invite(
            db,
            club_id='00000000-0000-0000-0000-000000000001',
            profile_name='Invited Player',
            phone='3337778888',
            invited_level=PlayLevel.BEGINNER,
        )
        expired_invite, expired_raw_token = create_community_invite(
            db,
            club_id='00000000-0000-0000-0000-000000000001',
            profile_name='Expired Player',
            phone='3337779999',
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        used_invite, used_raw_token = create_community_invite(
            db,
            club_id='00000000-0000-0000-0000-000000000001',
            profile_name='Used Player',
            phone='3331119999',
        )
        used_invite.used_at = datetime.now(UTC)
        db.commit()
        valid_invite_id = valid_invite.id

    valid_start_response = client.post(
        '/api/public/play-access/start',
        json={
            'purpose': 'INVITE',
            'invite_token': valid_raw_token,
            'email': 'invited@example.com',
            'declared_level': 'INTERMEDIATE_HIGH',
            'privacy_accepted': True,
        },
    )
    expired_start_response = client.post(
        '/api/public/play-access/start',
        json={
            'purpose': 'INVITE',
            'invite_token': expired_raw_token,
            'email': 'expired@example.com',
            'declared_level': 'BEGINNER',
            'privacy_accepted': True,
        },
    )
    used_start_response = client.post(
        '/api/public/play-access/start',
        json={
            'purpose': 'INVITE',
            'invite_token': used_raw_token,
            'email': 'used@example.com',
            'declared_level': 'BEGINNER',
            'privacy_accepted': True,
        },
    )

    assert valid_start_response.status_code == 200
    assert valid_start_response.json()['email_hint'].startswith('in')
    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME) is None
    assert expired_start_response.status_code == 409
    assert used_start_response.status_code == 409

    with SessionLocal() as db:
        invite = db.get(CommunityInviteToken, valid_invite_id)
        assert invite is not None
        assert invite.used_at is None

    verify_response = client.post(
        '/api/public/play-access/verify',
        json={
            'challenge_id': valid_start_response.json()['challenge_id'],
            'otp_code': '123456',
        },
    )

    assert verify_response.status_code == 200
    assert verify_response.json()['player']['profile_name'] == 'Invited Player'
    assert verify_response.json()['player']['email'] == 'invited@example.com'
    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME)

    with SessionLocal() as db:
        invite = db.get(CommunityInviteToken, valid_invite_id)
        assert invite is not None
        player = db.query(Player).filter(Player.phone == '3337778888').one()
        assert invite.used_at is not None
        assert invite.accepted_player_id == player.id


def test_admin_can_create_community_invite_and_receive_share_path(client):
    login_response = client.post(
        '/api/admin/auth/login',
        json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'},
    )
    assert login_response.status_code == 200

    response = client.post(
        '/api/admin/settings/community-invites',
        json={
            'profile_name': 'Giulia Spin',
            'phone': '+39 333 111 2222',
            'invited_level': 'INTERMEDIATE_MEDIUM',
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload['message'] == 'Invito community creato.'
    assert payload['profile_name'] == 'Giulia Spin'
    assert payload['phone'] == '+393331112222'
    assert payload['invited_level'] == 'INTERMEDIATE_MEDIUM'
    assert payload['invite_path'].startswith('/c/default-club/play/invite/')
    assert payload['invite_token']

    with SessionLocal() as db:
        invite = db.get(CommunityInviteToken, payload['invite_id'])
        assert invite is not None
        assert invite.club_id == DEFAULT_CLUB_ID
        assert invite.token_hash == hash_play_token(payload['invite_token'])


def test_admin_can_list_and_revoke_community_invites(client):
    login_response = client.post(
        '/api/admin/auth/login',
        json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'},
    )
    assert login_response.status_code == 200

    with SessionLocal() as db:
        active_invite, _ = create_community_invite(
            db,
            club_id=DEFAULT_CLUB_ID,
            profile_name='Active Guest',
            phone='3330000001',
            invited_level=PlayLevel.INTERMEDIATE_LOW,
        )
        expired_invite, _ = create_community_invite(
            db,
            club_id=DEFAULT_CLUB_ID,
            profile_name='Expired Guest',
            phone='3330000002',
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        used_invite, _ = create_community_invite(
            db,
            club_id=DEFAULT_CLUB_ID,
            profile_name='Used Guest',
            phone='3330000003',
            invited_level=PlayLevel.ADVANCED,
        )
        accepted_player = Player(
            club_id=DEFAULT_CLUB_ID,
            profile_name='Used Guest',
            phone='3330009999',
            declared_level=PlayLevel.ADVANCED,
            privacy_accepted_at=datetime.now(UTC),
            is_active=True,
        )
        db.add(accepted_player)
        db.flush()
        used_invite.used_at = datetime.now(UTC)
        used_invite.accepted_player_id = accepted_player.id

        revoked_invite, _ = create_community_invite(
            db,
            club_id=DEFAULT_CLUB_ID,
            profile_name='Revoked Guest',
            phone='3330000004',
        )
        revoked_invite.revoked_at = datetime.now(UTC)
        db.commit()

        active_invite_id = active_invite.id
        expired_invite_id = expired_invite.id
        used_invite_id = used_invite.id
        revoked_invite_id = revoked_invite.id

    list_response = client.get('/api/admin/settings/community-invites')

    assert list_response.status_code == 200
    items_by_id = {item['id']: item for item in list_response.json()['items']}
    assert items_by_id[active_invite_id]['status'] == 'ACTIVE'
    assert items_by_id[active_invite_id]['can_revoke'] is True
    assert items_by_id[expired_invite_id]['status'] == 'EXPIRED'
    assert items_by_id[expired_invite_id]['can_revoke'] is False
    assert items_by_id[used_invite_id]['status'] == 'USED'
    assert items_by_id[used_invite_id]['accepted_player_name'] == 'Used Guest'
    assert items_by_id[revoked_invite_id]['status'] == 'REVOKED'

    revoke_response = client.post(f'/api/admin/settings/community-invites/{active_invite_id}/revoke')

    assert revoke_response.status_code == 200
    assert revoke_response.json()['message'] == 'Invito community revocato.'
    assert revoke_response.json()['item']['status'] == 'REVOKED'
    assert revoke_response.json()['item']['can_revoke'] is False

    with SessionLocal() as db:
        invite = db.get(CommunityInviteToken, active_invite_id)
        assert invite is not None
        assert invite.revoked_at is not None


def test_admin_can_create_list_and_revoke_community_access_links(client):
    login_response = client.post(
        '/api/admin/auth/login',
        json={'email': 'admin@padelbooking.app', 'password': 'ChangeMe123!'},
    )
    assert login_response.status_code == 200

    create_response = client.post(
        '/api/admin/settings/community-access-links',
        json={
            'label': 'Gruppo WhatsApp Open Match',
            'max_uses': 200,
        },
    )

    assert create_response.status_code == 201
    create_payload = create_response.json()
    assert create_payload['message'] == 'Link accesso community creato.'
    assert create_payload['label'] == 'Gruppo WhatsApp Open Match'
    assert create_payload['max_uses'] == 200
    assert create_payload['used_count'] == 0
    assert create_payload['access_path'].startswith('/c/default-club/play/access/')
    assert create_payload['access_token']

    with SessionLocal() as db:
        item = db.get(CommunityAccessLink, create_payload['link_id'])
        assert item is not None
        assert item.club_id == DEFAULT_CLUB_ID
        assert item.token_hash == hash_play_token(create_payload['access_token'])

    list_response = client.get('/api/admin/settings/community-access-links')

    assert list_response.status_code == 200
    listed_item = next(item for item in list_response.json()['items'] if item['id'] == create_payload['link_id'])
    assert listed_item['status'] == 'ACTIVE'
    assert listed_item['can_revoke'] is True

    revoke_response = client.post(f"/api/admin/settings/community-access-links/{create_payload['link_id']}/revoke")

    assert revoke_response.status_code == 200
    assert revoke_response.json()['message'] == 'Link accesso community revocato.'
    assert revoke_response.json()['item']['status'] == 'REVOKED'
    assert revoke_response.json()['item']['can_revoke'] is False

    with SessionLocal() as db:
        item = db.get(CommunityAccessLink, create_payload['link_id'])
        assert item is not None
        assert item.revoked_at is not None


def test_play_cookie_is_not_valid_across_tenants(client):
    secondary = create_secondary_tenant(slug='play-milano', host='play-milano.example.test')

    identify_response = client.post(
        '/api/play/identify',
        json={
            'profile_name': 'Tenant Default',
            'phone': '3335550001',
            'declared_level': 'ADVANCED',
            'privacy_accepted': True,
        },
    )
    assert identify_response.status_code == 200
    legacy_cookie = client.cookies.get(PLAYER_SESSION_COOKIE_NAME)
    default_club_cookie = client.cookies.get(build_club_player_session_cookie_name('default-club'))

    assert legacy_cookie
    assert default_club_cookie == legacy_cookie

    cross_tenant_me = client.get('/api/play/me', headers=tenant_headers(secondary['host']))

    assert cross_tenant_me.status_code == 200
    assert cross_tenant_me.json()['player'] is None
    assert client.cookies.get(PLAYER_SESSION_COOKIE_NAME) == legacy_cookie
    assert client.cookies.get(build_club_player_session_cookie_name('default-club')) == default_club_cookie