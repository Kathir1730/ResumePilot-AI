import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .db import get_db
from .models import User
load_dotenv()
SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)
def hash_password(s): return pwd.hash(s)
def verify_password(s, h): return pwd.verify(s, h)
def token_for(uid):
    return jwt.encode({"sub":str(uid), "exp":datetime.now(timezone.utc) + timedelta(minutes=int(os.getenv("TOKEN_EXPIRE_MINUTES", "1440")))}, SECRET, algorithm="HS256")
def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if not creds: raise HTTPException(401, "Sign in to continue")
    try: uid = int(jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])["sub"])
    except (JWTError, ValueError, KeyError): raise HTTPException(401, "Invalid or expired session")
    user = db.get(User, uid)
    if not user: raise HTTPException(401, "User not found")
    return user
