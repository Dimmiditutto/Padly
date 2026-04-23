from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_enforced
from app.core.db import get_db
from app.models import Admin
from app.schemas.admin import CourtCreateRequest, CourtListResponse, CourtUpdateRequest
from app.schemas.common import CourtSummary
from app.services.court_service import create_court, list_courts, rename_court

router = APIRouter(prefix='/admin/courts', tags=['Admin Courts'])


@router.get('', response_model=CourtListResponse)
def get_courts(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> CourtListResponse:
    items = list_courts(db, club_id=admin.club_id, include_inactive=True)
    return CourtListResponse(items=[CourtSummary.model_validate(item) for item in items])


@router.post('', response_model=CourtSummary)
def add_court(payload: CourtCreateRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> CourtSummary:
    court = create_court(db, name=payload.name, club_id=admin.club_id)
    db.commit()
    db.refresh(court)
    return CourtSummary.model_validate(court)


@router.put('/{court_id}', response_model=CourtSummary)
def update_court(court_id: str, payload: CourtUpdateRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin_enforced)) -> CourtSummary:
    court = rename_court(db, court_id=court_id, name=payload.name, club_id=admin.club_id)
    db.commit()
    db.refresh(court)
    return CourtSummary.model_validate(court)