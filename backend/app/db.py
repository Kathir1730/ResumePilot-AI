import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
load_dotenv()
URL = os.getenv("DATABASE_URL", "sqlite:///./resumepilot.db")
if URL.startswith("postgres://"):
    URL = URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(URL, connect_args={"check_same_thread":False} if URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
