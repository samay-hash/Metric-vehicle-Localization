from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://bankadmin:bankpassword@localhost:5432/bankcctv")
engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    res = conn.execute(text("SELECT count(*) FROM events"))
    print(f"Total events in DB: {res.scalar()}")
