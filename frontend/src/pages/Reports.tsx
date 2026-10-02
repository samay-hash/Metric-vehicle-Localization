import type { EODReport, EventStatus } from '../types';
import { useEffect, useState, useRef } from 'react';
import html2pdf from 'html2pdf.js';
import { getEODReport } from '../api';
import { LoadingDots, SeverityBadge } from '../components/Shared';
import { Download, AlertTriangle, Camera, CheckCircle, TrendingUp } from 'lucide-react';
function eventStatusColor(status: EventStatus) {
  if (status === 'escalated')           return 'var(--red)';
  if (status === 'pending_review')      return 'var(--amber)';
  if (status === 'under_investigation') return 'var(--text-primary)';
  if (status === 'resolved')            return 'var(--green)';
  return 'var(--text-muted)';
}
export default function Reports() {
  const [report, setReport] = useState<EODReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [isExporting, setIsExporting] = useState(false);
  const reportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setReport(null);
    getEODReport()
      .then(res => { if (active) setReport(res.data); })
      .catch(() => { if (active) setError('The report service is unavailable. Please try again.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);

  const handleDownloadPDF = () => {
    if (!report || !reportRef.current) return;
    setIsExporting(true);
    const element = reportRef.current;
    
    // Add temporary styling to ensure dark mode prints correctly
    const worker = html2pdf();
    const opt: Parameters<typeof worker.set>[0] = {
      margin: 10,
      filename: `EOD_Report_${report.report_date}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { 
        scale: 2,
        useCORS: true,
        backgroundColor: '#0a0a0f' // Force dark background
      },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' }
    };

    worker.set(opt).from(element).save().then(() => {
      setIsExporting(false);
    });
  };

  if (loading) return (
    <div className="page-body flex items-center gap-2" style={{ justifyContent: 'center' }}>
      <LoadingDots />
      <span className="text-xs text-muted">Generating EOD report…</span>
    </div>
  );
  if (!report) return <div className="page-body">
    <div className="page-title">EOD Security Report</div>
    <div className="rbac-page-error" role="alert">{error || 'No report was returned.'}</div>
    <button className="btn btn-secondary" onClick={() => setAttempt(value => value + 1)}>Retry report</button>
  </div>;
  const r = report;
  return (
    <div className="page-body">
      {/* HEADER (Not part of PDF) */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <div className="page-title">EOD Security Report</div>
          <div className="page-desc">{r.branch ?? r.network} · {r.report_date}</div>
        </div>
        <div className="flex gap-2 items-center">
          <span className="text-xs text-muted font-mono">
            {new Date(r.generated_at).toLocaleTimeString('en-IN', { hour12: false })}
          </span>
          <button 
            className="btn btn-secondary btn-sm" 
            onClick={handleDownloadPDF}
            disabled={isExporting}
          >
            {isExporting ? <LoadingDots /> : <Download size={11} />} 
            {isExporting ? 'Exporting...' : 'Export PDF'}
          </button>
        </div>
      </div>
      
      {/* PDF CONTENT WRAPPER */}
      <div ref={reportRef} style={{ padding: '2px', backgroundColor: 'var(--bg-base)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 18 }}>
          {[
            { label: 'Critical Events', val: r.critical_incidents ?? r.critical_events ?? 0, color: 'red' },
            { label: 'Total Events',    val: r.total_events },
            { label: 'Cameras Active', val: `${r.cameras_active ?? r.cameras_online ?? 0}/${r.total_cameras ?? r.camera_health.length}`, color: 'green' },
            { label: 'Pending Review', val: r.critical_section.filter(e => ['pending_review','under_investigation'].includes(e.status)).length, color: 'amber' },
          ].map(({ label, val, color }) => (
          <div key={label} className="card" style={{ padding: '14px 16px' }}>
            <div className={`metric-value ${color || ''}`} style={{ fontSize: 22 }}>{val}</div>
            <div className="metric-label">{label}</div>
          </div>
        ))}
      </div>
      {}
      <div className="card amber-accent mb-4">
        <div className="report-section-title">
          <TrendingUp size={11} /> Executive Summary
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.75 }}>
          {r.executive_summary}
        </p>
      </div>
      <div className="section-grid">
        {}
        <div className="card red-accent">
          <div className="report-section-title" style={{ color: 'var(--red)' }}>
            <AlertTriangle size={11} /> Critical Events ({r.critical_section.length})
          </div>
          {r.critical_section.map(ev => (
            <div
              key={ev.event_id}
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderLeft: '2px solid var(--red)',
                borderRadius: 'var(--radius-sm)',
                padding: '10px 12px',
                marginBottom: 8,
              }}
            >
              <div className="flex justify-between items-center mb-1">
                <span className="font-mono text-xs" style={{ color: 'var(--red)', fontWeight: 700 }}>{ev.event_id}</span>
                <span
                  className="text-xs font-semibold"
                  style={{ color: eventStatusColor(ev.status), textTransform: 'uppercase', letterSpacing: '0.4px' }}
                >
                  {ev.status.replace(/_/g, ' ')}
                </span>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-primary)', marginBottom: 6, lineHeight: 1.5 }}>
                {ev.description}
              </p>
              <div className="flex gap-4 text-xs text-muted">
                <span>{ev.camera}</span>
                <span className="font-mono">{ev.timestamp}</span>
                {ev.person_id && <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{ev.person_id}</span>}
                <span style={{ color: 'var(--amber)', fontWeight: 600 }}>{Math.round(ev.confidence * 100)}%</span>
              </div>
            </div>
          ))}
          {}
          {r.high_section && r.high_section.length > 0 && (
            <>
              <div className="divider" />
              <div className="report-section-title">High Severity</div>
              {r.high_section.map(ev => (
                <div
                  key={ev.event_id}
                  style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border)',
                    borderLeft: '2px solid var(--amber)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px 12px',
                    marginBottom: 8,
                  }}
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-mono text-xs" style={{ color: 'var(--amber)', fontWeight: 700 }}>{ev.event_id}</span>
                    <span className="text-xs text-muted" style={{ textTransform: 'uppercase' }}>{ev.status.replace(/_/g, ' ')}</span>
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{ev.description}</p>
                  <div className="text-xs text-muted mt-1 font-mono">{ev.camera} · {ev.timestamp}</div>
                </div>
              ))}
            </>
          )}
        </div>
        {}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {}
          <div className="card">
            <div className="report-section-title">
              <CheckCircle size={11} /> Recommendations
            </div>
            {r.recommendations.map((rec, i) => (
              <div key={i} className="recommendation-item">
                <span className="rec-num">{String(i + 1).padStart(2, '0')}</span>
                <span>{rec}</span>
              </div>
            ))}
          </div>
          {}
          <div className="card">
            <div className="report-section-title">
              <Camera size={11} /> Camera Health
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Camera</th>
                  <th>FPS</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {r.camera_health.map(cam => (
                  <tr key={cam.camera_id}>
                    <td>
                      <div className="font-semibold" style={{ fontSize: 11 }}>{cam.name}</div>
                      <div className="font-mono text-xs text-muted">{cam.camera_id}</div>
                    </td>
                    <td>
                      <span
                        className="font-mono text-xs"
                        style={{ color: cam.fps < 20 ? 'var(--amber)' : 'var(--text-secondary)' }}
                      >{cam.fps}</span>
                    </td>
                    <td>
                      <span
                        className="text-xs font-bold"
                        style={{ color: cam.status === 'active' ? 'var(--green)' : 'var(--amber)' }}
                      >
                        {cam.status === 'active' ? 'ACTIVE' : 'WARNING'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}