import os
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production-use-long-random-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

app = FastAPI(title="Auth service", version="1.0.0")


class TokenRequest(BaseModel):
    username: str = "demo"
    password: str = "demo"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ValidateRequest(BaseModel):
    token: str


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@app.post("/token", response_model=TokenResponse)
def issue_token(body: TokenRequest) -> TokenResponse:
    if body.username != "demo" or body.password != "demo":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(subject=body.username)
    return TokenResponse(access_token=token)


@app.post("/validate")
def validate_token(body: ValidateRequest) -> dict:
    try:
        payload = jwt.decode(body.token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {"valid": True, "user": sub}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "auth_engine"}
