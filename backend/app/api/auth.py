from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_csrf
from app.models import User
from app.schemas.auth import AuthUser, ChangePasswordRequest, LoginRequest, LoginResponse
from app.security import clear_auth_cookies, enforce_allowed_origin
from app.services.auth import authenticate_and_start_session, change_own_password, revoke_current_session, rotate_session


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    enforce_allowed_origin(request)
    user = authenticate_and_start_session(db, request, response, str(payload.email), payload.password)
    return LoginResponse(user=AuthUser.model_validate(user))


@router.post("/refresh", response_model=LoginResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    enforce_allowed_origin(request)
    user = rotate_session(db, request, response)
    return LoginResponse(user=AuthUser.model_validate(user))


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    user: User = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    enforce_allowed_origin(request)
    revoke_current_session(db, request, response, user)
    response.status_code = 204
    return None


@router.get("/me", response_model=AuthUser)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    user: User = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    enforce_allowed_origin(request)
    change_own_password(db, request, user, payload.current_password, payload.new_password)
    clear_auth_cookies(response)
    response.status_code = 204
    return None
