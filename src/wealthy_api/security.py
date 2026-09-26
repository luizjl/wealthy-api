from typing import Any

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin.exceptions import FirebaseError

from wealthy_api.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def verify_firebase_id_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        app = firebase_admin.get_app()
    except ValueError:
        options = (
            {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None
        )
        app = firebase_admin.initialize_app(options=options)
    return firebase_auth.verify_id_token(token, app=app, check_revoked=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token Firebase ausente ou inválido",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        claims = verify_firebase_id_token(credentials.credentials, settings)
    except FirebaseError as error:
        raise unauthorized from error

    uid = claims.get("uid")
    if not isinstance(uid, str):
        raise unauthorized

    if uid not in settings.allowed_firebase_uids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem autorização para acessar a API",
        )

    return claims
