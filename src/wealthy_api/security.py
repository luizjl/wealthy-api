from pathlib import Path
from typing import Any

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials as firebase_credentials
from firebase_admin.exceptions import FirebaseError
from google.auth.exceptions import DefaultCredentialsError

from wealthy_api.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


class FirebaseConfigurationError(Exception):
    pass


def verify_firebase_id_token(token: str, settings: Settings) -> dict[str, Any]:
    if not settings.firebase_project_id:
        raise FirebaseConfigurationError("WEALTHY_FIREBASE_PROJECT_ID não configurado")

    credential = None
    if settings.firebase_credentials_file:
        credentials_path = Path(settings.firebase_credentials_file).expanduser()
        if not credentials_path.is_file():
            raise FirebaseConfigurationError("Arquivo de credenciais Firebase não encontrado")
        try:
            credential = firebase_credentials.Certificate(str(credentials_path))
        except (OSError, ValueError) as error:
            raise FirebaseConfigurationError("Arquivo de credenciais Firebase inválido") from error

    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app(
            credential=credential,
            options={"projectId": settings.firebase_project_id},
        )
    try:
        return firebase_auth.verify_id_token(token, app=app, check_revoked=True)
    except DefaultCredentialsError as error:
        raise FirebaseConfigurationError(
            "Configure credenciais Firebase Admin ou GOOGLE_APPLICATION_CREDENTIALS"
        ) from error


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
    except FirebaseConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Autenticação Firebase não configurada no servidor",
        ) from error
    except FirebaseError as error:
        raise unauthorized from error

    uid = claims.get("uid")
    if not isinstance(uid, str):
        raise unauthorized

    if uid not in settings.allowed_firebase_uids:
        if uid not in settings.admin_firebase_uids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário sem autorização para acessar a API",
            )

    return claims


def get_current_admin(
    claims: dict[str, Any] = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    uid = claims.get("uid")
    if uid not in settings.admin_firebase_uids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem perfil administrativo",
        )
    return claims
