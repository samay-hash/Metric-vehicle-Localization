"""
Gujarat Sentinel Grid — Reports Router
Real PDF generation via fpdf2 + JSON EOD reports.
"""

import io
import os
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from datetime import datetime
from data.database import EVENTS, INCIDENTS, CAMERAS, SYSTEM_STATS

router = APIRouter(prefix="/reports", tags=["reports"])


# ── Shared report builder ─────────────────────────────────────────────────────

def _build_report_data() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    critical_events = [e for e in EVENTS if e["severity"] == "critical"]
    high_events     = [e for e in EVENTS if e["severity"] == "high"]
    pending         = [e for e in EVENTS if e["status"] == "pending_review"]

    def _ts(e):
        ts = e.get("timestamp", "")
        if isinstance(ts, datetime):
            return ts.isoformat()[:19].replace("T", " ")
        return str(ts)[:19]

    executive_summary = (
        f"Surveillance report for {today}. "
        f"{len(EVENTS)} AI-detected events recorded across {len(CAMERAS)} active cameras. "
        f"{len(critical_events)} critical event(s) flagged. "
        f"{len(pending)} event(s) pending investigator review. "
        f"{len(INCIDENTS)} active incident(s) under investigation."
    ) if EVENTS else (
        f"Surveillance report for {today}. No events recorded yet. "
        "System is operational and monitoring all camera feeds."
    )

    recommendations = []
    if critical_events:
        recommendations.append(f"Immediately review {len(critical_events)} critical event(s).")
    if pending:
        recommendations.append(f"Clear {len(pending)} pending event(s) before next cycle.")
    warn_cams = [c for c in CAMERAS if c["status"] == "warning"]
    if warn_cams:
        recommendations.append(f"Schedule maintenance: {', '.join(c['id'] for c in warn_cams)}.")
    if not recommendations:
        recommendations.append("No immediate action required. Continue routine surveillance.")

    return {
        "report_date": today,
        "generated_at": datetime.now().isoformat(),
        "network": "Gujarat Police AI Surveillance Grid",
        "total_cameras": len(CAMERAS),
        "cameras_online": SYSTEM_STATS()["cameras_online"],
        "total_events": len(EVENTS),
        "critical_events": len(critical_events),
        "high_events": len(high_events),
        "pending_review": len(pending),
        "active_incidents": len(INCIDENTS),
        "executive_summary": executive_summary,
        "recommendations": recommendations,
        "critical_section": [
            {
                "event_id": e["id"], "timestamp": _ts(e),
                "camera": e["camera_name"], "zone": e.get("zone", ""),
                "description": e.get("description", ""),
                "confidence": e.get("confidence", 0),
                "status": e.get("status", "open"),
            }
            for e in critical_events
        ],
        "high_section": [
            {
                "event_id": e["id"], "timestamp": _ts(e),
                "camera": e["camera_name"],
                "description": e.get("description", ""),
                "status": e.get("status", "open"),
            }
            for e in high_events
        ],
        "camera_health": [
            {"camera_id": c["id"], "name": c["name"], "status": c["status"],
             "fps": c.get("fps", 0), "resolution": c["resolution"], "zone": c["zone"]}
            for c in CAMERAS
        ],
        "system_stats": SYSTEM_STATS(),
        "incidents": INCIDENTS,
    }


# ── JSON EOD endpoint ─────────────────────────────────────────────────────────

@router.get("/eod")
def get_eod_report():
    return _build_report_data()


# ── Real PDF generation ───────────────────────────────────────────────────────

@router.get("/eod/pdf")
def download_eod_pdf():
    """Generate and stream a real PDF report using fpdf2."""
    try:
        from fpdf import FPDF
    except ImportError:
        return JSONResponse({"error": "fpdf2 not installed. Run: pip install fpdf2"}, status_code=500)

    data = _build_report_data()
    now  = datetime.now()

    class PDF(FPDF):
        def header(self):
            self.set_fill_color(10, 36, 99)        # Dark navy
            self.rect(0, 0, 210, 22, "F")
            self.set_font("Helvetica", "B", 13)
            self.set_text_color(255, 255, 255)
            self.set_xy(10, 6)
            self.cell(0, 10, "GUJARAT POLICE — AI SURVEILLANCE GRID", align="L")
            self.set_font("Helvetica", "", 8)
            self.set_xy(10, 14)
            self.cell(0, 5, "CONFIDENTIAL — END OF DAY SECURITY REPORT", align="L")
            self.ln(10)

        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(120, 120, 120)
            self.cell(0, 5,
                      f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')} IST  |  "
                      f"Gujarat Sentinel Grid v1.0  |  Page {self.page_no()}",
                      align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(12, 28, 12)

    # ── Title block ───────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(10, 36, 99)
    pdf.cell(0, 10, f"Daily Surveillance Report — {data['report_date']}", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Generated: {now.strftime('%H:%M:%S IST')}  |  "
                   f"Network: {data['network']}", ln=True)
    pdf.ln(4)

    # ── Summary stat boxes ────────────────────────────────────────────────────
    stats = [
        ("CAMERAS ONLINE",   str(data["cameras_online"]),   (16, 185, 129)),
        ("TOTAL EVENTS",     str(data["total_events"]),     (59,  130, 246)),
        ("CRITICAL ALERTS",  str(data["critical_events"]),  (239, 68,  68)),
        ("ACTIVE INCIDENTS", str(data["active_incidents"]), (245, 158, 11)),
    ]
    box_w = 43
    for i, (label, value, color) in enumerate(stats):
        x = 12 + i * (box_w + 2)
        pdf.set_xy(x, pdf.get_y())
        pdf.set_fill_color(*color)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(box_w, 12, value, fill=True, align="C")
        pdf.set_xy(x, pdf.get_y())
        pdf.set_font("Helvetica", "", 6.5)
        pdf.cell(box_w, 5, label, align="C", ln=(i == 3))
    pdf.ln(6)

    # ── Executive Summary ─────────────────────────────────────────────────────
    pdf.set_text_color(10, 36, 99)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "EXECUTIVE SUMMARY", ln=True)
    pdf.set_draw_color(10, 36, 99)
    pdf.line(12, pdf.get_y(), 198, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5, data["executive_summary"])
    pdf.ln(3)

    # ── Recommendations ───────────────────────────────────────────────────────
    pdf.set_text_color(10, 36, 99)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "RECOMMENDATIONS", ln=True)
    pdf.line(12, pdf.get_y(), 198, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    for rec in data["recommendations"]:
        pdf.cell(5, 5, chr(149))   # bullet
        pdf.multi_cell(0, 5, rec)
    pdf.ln(3)

    # ── Critical Events table ─────────────────────────────────────────────────
    if data["critical_section"]:
        pdf.set_text_color(10, 36, 99)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, f"CRITICAL EVENTS ({len(data['critical_section'])})", ln=True)
        pdf.line(12, pdf.get_y(), 198, pdf.get_y())
        pdf.ln(2)

        headers = ["Event ID", "Time", "Camera", "Zone", "Description", "Conf", "Status"]
        widths  = [28, 28, 30, 22, 55, 12, 11]

        pdf.set_fill_color(239, 68, 68)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 7)
        for h, w in zip(headers, widths):
            pdf.cell(w, 6, h, border=0, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 7)
        for i, ev in enumerate(data["critical_section"]):
            fill = i % 2 == 0
            pdf.set_fill_color(255, 240, 240) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.set_text_color(30, 30, 30)
            row = [ev["event_id"], ev["timestamp"][-8:], ev["camera"],
                   ev["zone"], ev["description"][:45], f"{ev['confidence']:.0%}", ev["status"]]
            for val, w in zip(row, widths):
                pdf.cell(w, 5, str(val), border=0, fill=fill, align="L")
            pdf.ln()
        pdf.ln(3)

    # ── Camera Health ─────────────────────────────────────────────────────────
    pdf.set_text_color(10, 36, 99)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "CAMERA HEALTH STATUS", ln=True)
    pdf.line(12, pdf.get_y(), 198, pdf.get_y())
    pdf.ln(2)

    pdf.set_fill_color(10, 36, 99)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 7)
    for h, w in zip(["Camera ID", "Name", "Zone", "FPS", "Resolution", "Status"],
                    [22, 48, 28, 12, 24, 20]):
        pdf.cell(w, 6, h, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 7)
    for i, cam in enumerate(data["camera_health"]):
        fill = i % 2 == 0
        pdf.set_fill_color(240, 248, 255) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(30, 30, 30)
        status_color = (16, 185, 129) if cam["status"] == "active" else (245, 158, 11)
        for val, w in zip([cam["camera_id"], cam["name"], cam["zone"],
                           cam["fps"], cam["resolution"], cam["status"].upper()],
                          [22, 48, 28, 12, 24, 20]):
            if val == cam["status"].upper():
                pdf.set_text_color(*status_color)
            pdf.cell(w, 5, str(val), fill=fill, align="L")
            pdf.set_text_color(30, 30, 30)
        pdf.ln()

    # ── Output ────────────────────────────────────────────────────────────────
    pdf_bytes = bytes(pdf.output())
    filename  = f"sentinel_eod_{now.strftime('%Y%m%d_%H%M%S')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/incident/{incident_id}")
def get_incident_report(incident_id: str):
    incident = next((i for i in INCIDENTS if i["id"] == incident_id), None)
    if not incident:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Incident not found")
    events = [e for e in EVENTS if e["id"] in incident.get("event_ids", [])]
    return {
        "incident": incident,
        "related_events": events,
        "cameras_involved": incident.get("camera_ids", []),
        "persons_of_interest": incident.get("person_ids", []),
        "report_generated_at": datetime.now().isoformat(),
    }


@router.get("/system/stats")
def system_stats():
    return SYSTEM_STATS()