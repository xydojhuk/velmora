import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.dependencies import require_admin, require_admin_read
from app.enums import UserRole
from app.models import RefreshSession, User
from app.schemas.users import UserCreate, UserList, UserPasswordReset, UserRead, UserUpdate
from app.security import hash_password, validate_password_policy
from app.utils import utcnow


router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=UserList)
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    search: str | None = Query(default=None, max_length=120),
    role: UserRole | None = None,
    active: bool | None = None,
    _: User = Depends(require_admin_read),
    db: Session = Depends(get_db),
):
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(User.email.ilike(term), User.display_name.ilike(term)))
    if role is not None:
        filters.append(User.role == role)
    if active is not None:
        filters.append(User.is_active == active)
    total = db.scalar(select(func.count(User.id)).where(*filters)) or 0
    items = db.scalars(
        select(User).where(*filters).order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return UserList(items=items, total=total, page=page, size=size)


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    email = str(payload.email).strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists")
    try:
        validate_password_policy(payload.password, email)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    user = User(
        email=email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
        password_changed_at=utcnow(),
    )
    db.add(user)
    db.flush()
    write_audit(
        db,
        request,
        "user.created",
        actor=actor,
        resource_type="user",
        resource_id=user.id,
        details={"email": user.email, "role": user.role.value},
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    changes = payload.model_dump(exclude_unset=True)
    if user.id == actor.id and (changes.get("is_active") is False or changes.get("role") == UserRole.MODERATOR):
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account or lower your own role")
    if user.role == UserRole.ADMIN and user.is_active:
        will_remove_admin = changes.get("is_active") is False or changes.get("role") == UserRole.MODERATOR
        if will_remove_admin:
            active_admins = db.scalar(
                select(func.count(User.id)).where(User.role == UserRole.ADMIN, User.is_active.is_(True))
            ) or 0
            if active_admins <= 1:
                raise HTTPException(status_code=400, detail="At least one active administrator must remain in the system")
    for key, value in changes.items():
        setattr(user, key, value)
    if changes.get("is_active") is False:
        db.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )
    write_audit(
        db,
        request,
        "user.updated",
        actor=actor,
        resource_type="user",
        resource_id=user.id,
        details={"changed_fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", status_code=204)
def reset_password(
    user_id: uuid.UUID,
    payload: UserPasswordReset,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        validate_password_policy(payload.new_password, user.email)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = utcnow()
    user.failed_login_attempts = 0
    user.locked_until = None
    db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    write_audit(db, request, "user.password_reset", actor=actor, resource_type="user", resource_id=user.id)
    db.commit()
    return None
