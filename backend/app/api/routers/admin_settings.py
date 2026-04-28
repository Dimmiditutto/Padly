from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_enforced
from app.core.db import get_db
from app.models import Admin
from app.schemas.admin import AdminSettingsResponse, AdminSettingsUpdateRequest
from app.schemas.play import (
    AdminCommunityInviteCreateRequest,
    AdminCommunityInviteCreateResponse,
    AdminCommunityInviteListResponse,
    AdminCommunityInviteRevokeResponse,
    AdminCommunityInviteSummary,
)
from app.services.payment_service import is_paypal_checkout_available, is_stripe_checkout_available, list_available_checkout_providers
from app.services.play_service import (
    can_revoke_community_invite,
    create_community_invite,
    get_community_invite_status,
    list_community_invites,
    revoke_community_invite,
)
from app.services.settings_service import get_tenant_settings, update_tenant_settings

router = APIRouter(prefix='/admin/settings', tags=['Admin Settings'])


def _build_admin_community_invite_summary(invite) -> AdminCommunityInviteSummary:
    status_value = get_community_invite_status(invite)
    return AdminCommunityInviteSummary(
        id=invite.id,
        profile_name=invite.profile_name,
        phone=invite.phone,
        invited_level=invite.invited_level,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        used_at=invite.used_at,
        revoked_at=invite.revoked_at,
        accepted_player_name=invite.accepted_player.profile_name if invite.accepted_player else None,
        status=status_value,
        can_revoke=can_revoke_community_invite(invite),
    )


@router.get('', response_model=AdminSettingsResponse)
def get_settings_payload(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> AdminSettingsResponse:
    payload = get_tenant_settings(db, club=admin.club)
    return AdminSettingsResponse(
        stripe_enabled=is_stripe_checkout_available(),
        paypal_enabled=is_paypal_checkout_available(),
        **payload,
    )


@router.put('', response_model=AdminSettingsResponse)
def update_settings_payload(
    payload: AdminSettingsUpdateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin_enforced),
) -> AdminSettingsResponse:
    if payload.play_community_deposit_enabled and payload.play_community_deposit_amount <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='Configura una caparra community maggiore di zero')
    if payload.play_community_deposit_enabled and not list_available_checkout_providers():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Nessun provider online disponibile per attivare la caparra community')

    settings_payload = update_tenant_settings(
        db,
        club=admin.club,
        booking_hold_minutes=payload.booking_hold_minutes,
        cancellation_window_hours=payload.cancellation_window_hours,
        reminder_window_hours=payload.reminder_window_hours,
        public_name=payload.public_name,
        notification_email=payload.notification_email,
        support_email=payload.support_email,
        support_phone=payload.support_phone,
        public_address=payload.public_address,
        public_postal_code=payload.public_postal_code,
        public_city=payload.public_city,
        public_province=payload.public_province,
        public_latitude=payload.public_latitude,
        public_longitude=payload.public_longitude,
        is_community_open=payload.is_community_open,
        member_hourly_rate=payload.member_hourly_rate,
        non_member_hourly_rate=payload.non_member_hourly_rate,
        member_ninety_minute_rate=payload.member_ninety_minute_rate,
        non_member_ninety_minute_rate=payload.non_member_ninety_minute_rate,
        play_community_deposit_enabled=payload.play_community_deposit_enabled,
        play_community_deposit_amount=payload.play_community_deposit_amount,
        play_community_payment_timeout_minutes=payload.play_community_payment_timeout_minutes,
    )
    db.commit()
    return AdminSettingsResponse(
        stripe_enabled=is_stripe_checkout_available(),
        paypal_enabled=is_paypal_checkout_available(),
        **settings_payload,
    )


@router.post('/community-invites', response_model=AdminCommunityInviteCreateResponse, status_code=status.HTTP_201_CREATED)
def create_settings_community_invite(
    payload: AdminCommunityInviteCreateRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin_enforced),
) -> AdminCommunityInviteCreateResponse:
    invite, raw_token = create_community_invite(
        db,
        club_id=admin.club_id,
        profile_name=payload.profile_name,
        phone=payload.phone,
        invited_level=payload.invited_level,
    )
    db.commit()
    return AdminCommunityInviteCreateResponse(
        message='Invito community creato.',
        invite_id=invite.id,
        invite_token=raw_token,
        invite_path=f'/c/{admin.club.slug}/play/invite/{raw_token}',
        profile_name=invite.profile_name,
        phone=invite.phone,
        invited_level=invite.invited_level,
        expires_at=invite.expires_at,
    )


@router.get('/community-invites', response_model=AdminCommunityInviteListResponse)
def list_settings_community_invites(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin_enforced),
) -> AdminCommunityInviteListResponse:
    items = list_community_invites(db, club_id=admin.club_id)
    return AdminCommunityInviteListResponse(items=[_build_admin_community_invite_summary(invite) for invite in items])


@router.post('/community-invites/{invite_id}/revoke', response_model=AdminCommunityInviteRevokeResponse)
def revoke_settings_community_invite(
    invite_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin_enforced),
) -> AdminCommunityInviteRevokeResponse:
    invite = revoke_community_invite(db, club_id=admin.club_id, invite_id=invite_id)
    db.commit()
    return AdminCommunityInviteRevokeResponse(
        message='Invito community revocato.',
        item=_build_admin_community_invite_summary(invite),
    )