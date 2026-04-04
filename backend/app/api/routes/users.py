from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.user import (
    ProfileResponse,
    TimelineResponse,
    UserCreateRequest,
    UserListItem,
    UserResponse,
    UsersListResponse,
    UserProfileUpdateRequest,
)
from app.services.memory_service import build_user_timeline
from app.services.user_service import create_user, get_profile_or_404, list_users, update_profile

router = APIRouter()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(payload: UserCreateRequest, db: Session = Depends(get_db)) -> UserResponse:
    return create_user(db=db, payload=payload)


@router.get("", response_model=UsersListResponse)
def list_users_endpoint(
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> UsersListResponse:
    items, total = list_users(db=db, q=q, limit=limit, offset=offset)
    return UsersListResponse(
        items=[UserListItem.model_validate(item) for item in items],
        total=total,
        limit=max(1, min(limit, 200)),
        offset=max(0, offset),
    )


@router.get("/{user_id}/profile", response_model=ProfileResponse)
def get_profile_endpoint(user_id: str, db: Session = Depends(get_db)) -> ProfileResponse:
    profile = get_profile_or_404(db=db, user_id=user_id)
    return ProfileResponse.model_validate(profile)


@router.patch("/{user_id}/profile", response_model=ProfileResponse)
def update_profile_endpoint(
    user_id: str,
    payload: UserProfileUpdateRequest,
    db: Session = Depends(get_db),
) -> ProfileResponse:
    profile = update_profile(db=db, user_id=user_id, payload=payload)
    return ProfileResponse.model_validate(profile)


@router.get("/{user_id}/timeline", response_model=TimelineResponse)
def get_timeline_endpoint(user_id: str, limit: int = 20, db: Session = Depends(get_db)) -> TimelineResponse:
    try:
        return build_user_timeline(db=db, user_id=user_id, limit=max(1, min(limit, 200)))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
