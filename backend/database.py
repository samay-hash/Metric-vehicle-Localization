import os
from pathlib import Path
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, JSON, MetaData
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

DEFAULT_DATABASE = Path(__file__).resolve().parent / "data" / "analytics.sqlite3"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBEvent(Base):
    __tablename__ = "events"
    id = Column(String, primary_key=True, index=True)
    camera_id = Column(String, index=True)
    camera_name = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String)
    severity = Column(String)
    summary = Column(Text)
    person_id = Column(String, nullable=True)
    clip_ref = Column(String, nullable=True)
    thumbnail = Column(String, nullable=True)
    
    # Text embedding for True Semantic Search (RAG)
    embedding = Column(Vector(384) if engine.dialect.name == "postgresql" else JSON)
    
    # Raw JSON data for backward compatibility with existing codebase
    raw_data = Column(JSON)

class VehicleSighting(Base):
    __tablename__ = "vehicle_sightings"
    id = Column(String, primary_key=True, index=True)
    plate = Column(String, index=True)
    camera_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    confidence = Column(Float)
    embedding = Column(Vector(2048) if engine.dialect.name == "postgresql" else JSON) # FastReID 2048d

def log_sighting(plate: str, camera_id: str, timestamp: datetime, confidence: float, embedding: list = None):
    db = SessionLocal()
    try:
        sighting = VehicleSighting(
            id=f"SIG_{uuid.uuid4().hex[:8].upper()}",
            plate=plate,
            camera_id=camera_id,
            timestamp=timestamp,
            confidence=float(confidence),
            embedding=embedding
        )
        db.add(sighting)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log silent vehicle sighting: {e}")
    finally:
        db.close()

def init_db():
    from sqlalchemy import text
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
