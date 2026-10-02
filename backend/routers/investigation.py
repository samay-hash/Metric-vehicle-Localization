import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from data.database import EVENTS, INCIDENTS, CAMERAS
from datetime import datetime
import re
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/investigation", tags=["investigation"])
class InvestigationQuery(BaseModel):
    query: str
    time_from: Optional[str] = None
    time_to: Optional[str] = None
    camera_ids: Optional[List[str]] = None
KEYWORD_MAP = {
    "restricted": ["restricted_entry", "after_hours_presence", "unauthorized_entry"],
    "vault": ["restricted_entry", "unauthorized_entry"],
    "cash": ["object_removal", "loitering", "repeated_approach"],
    "counter": ["object_removal", "loitering", "repeated_approach"],
    "atm": ["atm_obstruction"],
    "after hours": ["after_hours_presence"],
    "closing": ["after_hours_presence"],
    "suspicious": ["restricted_entry", "object_removal", "atm_obstruction", "suspicious_motion", "repeated_approach"],
    "motion": ["suspicious_motion"],
    "camera": ["camera_tampering", "camera_obstruction"],
    "bag": ["unattended_object"],
    "object": ["object_removal", "unattended_object"],
    "loiter": ["loitering"],
    "person following": ["person_following"],
    "upload": ["suspicious_motion"],
    "uploaded": ["suspicious_motion"],
    "video": ["suspicious_motion"],
    "weird": ["suspicious_motion", "restricted_entry", "object_removal"],
    "today": [],
    "critical": [],
    "all": [],
    "everything": [],
    "show": [],
}
ZONE_KEYWORDS = {
    "vault": "restricted",
    "manager": "restricted",
    "restricted": "restricted",
    "cash": "cash_counter",
    "counter": "cash_counter",
    "atm": "atm",
    "entrance": "entrance",
    "parking": "exterior",
    "lobby": "lobby",
}
SEVERITY_KEYWORDS = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "serious": "critical",
    "urgent": "critical",
}
def _parse_query(query: str):
    q = query.lower()
    matched_types = []
    matched_zones = []
    matched_severity = None
    for kw, types in KEYWORD_MAP.items():
        if kw in q:
            matched_types.extend(types)
    for kw, zone in ZONE_KEYWORDS.items():
        if kw in q:
            matched_zones.append(zone)
    for kw, sev in SEVERITY_KEYWORDS.items():
        if kw in q:
            matched_severity = sev
            break
    return list(set(matched_types)), list(set(matched_zones)), matched_severity
async def _generate_answer_async(query: str, matched_events: list, incidents: list) -> str:
    n = len(matched_events)
    if n == 0:
        return (
            "No matching events found for this query in the current time window. "
            "Try broadening the time range or using different keywords."
        )

    context_lines = []
    for e in matched_events[:15]:
        context_lines.append(f"- Time: {e['timestamp']}, Camera: {e['camera_id']}, Zone: {e['zone']}, Event: {e['event_type']}, Person: {e.get('person_id', 'Unknown')}, Description: {e['description']}")
    
    context_str = "\n".join(context_lines)
    
    prompt = f"""You are BankCCTV, a highly professional and analytical AI security investigator.
The user asked a query about the CCTV system. Based on the following retrieved events, provide a direct, concise, and professional response answering their query. 
Use markdown formatting (like bolding key details, bullet points if needed). Do not just list the events, synthesize them into a coherent answer. Point out specific persons (e.g., P_001) if they are relevant.

User Query: "{query}"

Retrieved Events:
{context_str}
"""
    from services.local_llm import generate_text
    try:
        response = await generate_text(prompt)
        if response:
            answer = response.strip()
            answer += f"\n\n*(Found {n} matching event(s) in system logs)*"
            return answer
    except Exception as e:
        print(f"Local LLM error in investigation: {e}")
        
    return f"Investigation complete. Found {n} matching events, but Local AI failed to generate a summary."
from scipy.spatial.distance import cosine
from database import SessionLocal, DBEvent
from services.video_pipeline import embed_model

@router.post("/query")
async def investigate_query(body: InvestigationQuery):
    query = body.query
    filtered = []
    matched_types = []
    matched_zones = []
    matched_severity = None
    
    if embed_model:
        query_embedding = embed_model.encode(query).tolist()
        try:
            db = SessionLocal()
            try:
                results = db.query(DBEvent).order_by(DBEvent.embedding.cosine_distance(query_embedding)).limit(10).all()
                filtered = [r.raw_data for r in results]
            finally:
                db.close()
        except Exception as e:
            print(f"Warning: PostgreSQL pgvector search failed ({e}). Falling back to local scipy RAG.")
            scored_events = []
            for e in EVENTS:
                if 'embedding' not in e:
                    text_to_embed = f"Event: {e.get('event_type')}. {e.get('description')} Location: {e.get('camera_id')}"
                    e['embedding'] = embed_model.encode(text_to_embed).tolist()
                dist = cosine(query_embedding, e['embedding'])
                scored_events.append((dist, e))
            scored_events.sort(key=lambda x: x[0])
            filtered = [e for _, e in scored_events[:10]]
    else:
        # Fallback to old keyword search if model is completely unavailable
        matched_types, matched_zones, matched_severity = _parse_query(query)
        filtered = list(EVENTS)
        if matched_types:
            filtered = [e for e in filtered if e["event_type"] in matched_types]
        if matched_zones:
            filtered = [e for e in filtered if e["zone"] in matched_zones]
        if matched_severity:
            filtered = [e for e in filtered if e["severity"] == matched_severity]
        filtered.sort(key=lambda x: x["timestamp"], reverse=True)
    relevant_events_ids = {e["id"] for e in filtered}
    related_incidents = [
        inc for inc in INCIDENTS
        if any(eid in relevant_events_ids for eid in inc["event_ids"])
    ]
    timeline = [
        {
            "time": e["timestamp"],
            "camera": e["camera_id"],
            "event": e["description"][:80],
            "type": e["event_type"],
        }
        for e in filtered
    ]
    timeline.sort(key=lambda x: x["time"])
    answer = await _generate_answer_async(query, filtered, related_incidents)
    evidence_clips = [e["clip_ref"] for e in filtered if e.get("clip_ref")]
    all_cameras = list({e["camera_id"] for e in filtered})
    return {
        "query": query,
        "answer": answer,
        "relevant_events": filtered[:10],
        "relevant_cameras": all_cameras,
        "timeline": timeline,
        "confidence": round(0.75 + len(filtered) * 0.02, 2) if filtered else 0.0,
        "evidence_clips": evidence_clips,
        "related_incidents": [inc["id"] for inc in related_incidents],
        "parsed_filters": {
            "event_types": matched_types,
            "zones": matched_zones,
            "severity": matched_severity,
        },
    }
@router.get("/incidents")
def list_incidents():
    return {"incidents": INCIDENTS, "total": len(INCIDENTS)}
@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    incident = next((i for i in INCIDENTS if i["id"] == incident_id), None)
    if not incident:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
@router.get("/persons/{person_id}")
def get_person_events(person_id: str):
    person_events = [e for e in EVENTS if e.get("person_id") == person_id]
    from data.database import TRAJECTORIES
    trajectory = TRAJECTORIES.get(person_id, [])
    return {
        "person_id": person_id,
        "events": person_events,
        "trajectory": trajectory,
        "total_events": len(person_events),
    }