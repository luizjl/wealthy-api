from fastapi import Depends, FastAPI

from wealthy_api.routers.people import router as people_router
from wealthy_api.security import get_current_user

app = FastAPI(title="Wealthy API", version="0.1.0")
app.include_router(people_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/me", tags=["account"])
def read_current_user(claims: dict = Depends(get_current_user)) -> dict[str, str | None]:
    return {"uid": claims["uid"], "email": claims.get("email")}
