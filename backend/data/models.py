from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost:5432/bankcctv")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
class Event(Base):
    __tablename__ = "events"
    id = Column(String, primary_key=True, index=True)
    camera_id = Column(String, index=True)
    camera_name = Column(String)
    event_type = Column(String, index=True)
    severity = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    person_id = Column(String, nullable=True)
    zone = Column(String)
    confidence = Column(Float)
    duration_sec = Column(Integer)
    clip_ref = Column(String)
    status = Column(String, default="pending_review")
    description = Column(String)
    vlm_analysis = Column(JSON, nullable=True)
class Incident(Base):
    __tablename__ = "incidents"
    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    status = Column(String)
    severity = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    assigned_to = Column(String)
    events_linked = Column(JSON)
    summary = Column(String)