from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime
class Camera(BaseModel):
    id: str
    name: str
    location: str
    zone: str
    status: str
    fps: int
    resolution: str
    rtsp: str
class VLMAnalysis(BaseModel):
    summary: str
    objects_detected: List[str]
    sequence: List[str]
    confidence: float
    flags: List[str]
class Event(BaseModel):
    id: str
    camera_id: str
    camera_name: str
    event_type: str
    severity: str
    timestamp: str
    person_id: Optional[str]
    zone: str
    confidence: float
    duration_sec: int
    clip_ref: str
    thumbnail: Optional[str]
    status: str
    description: str
    vlm_analysis: Optional[VLMAnalysis]
class IncidentTimelineEntry(BaseModel):
    time: str
    camera: str
    event: str
    type: str
class Incident(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    created_at: str
    updated_at: str
    event_ids: List[str]
    camera_ids: List[str]
    person_ids: List[str]
    summary: str
    timeline: List[IncidentTimelineEntry]
    assigned_to: str
    investigation_notes: str
class TrajectoryEntry(BaseModel):
    camera: str
    time: str
    zone: str
    event: str
class SystemStats(BaseModel):
    cameras_online: int
    cameras_warning: int
    cameras_offline: int
    events_today: int
    critical_events: int
    high_events: int
    pending_review: int
    active_incidents: int
    avg_detection_latency_ms: int
    gpu_utilization: int
    gpu_memory_gb: float
    streams_fps: Dict[str, int]
class InvestigationQuery(BaseModel):
    query: str
    time_from: Optional[str] = None
    time_to: Optional[str] = None
    camera_ids: Optional[List[str]] = None
    severity: Optional[str] = None
class InvestigationResult(BaseModel):
    query: str
    answer: str
    relevant_events: List[Event]
    relevant_cameras: List[str]
    timeline: List[IncidentTimelineEntry]
    confidence: float
    evidence_clips: List[str]
class EODReport(BaseModel):
    report_date: str
    branch: str
    generated_at: str
    critical_incidents: int
    total_events: int
    cameras_active: int
    executive_summary: str
    critical_section: List[Dict[str, Any]]
    high_section: List[Dict[str, Any]]
    recommendations: List[str]
    camera_health: List[Dict[str, Any]]