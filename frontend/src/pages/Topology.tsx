import type { SecurityEvent, GeoCamera } from '../types';
import React, { useState, useEffect } from 'react';
import { AlertTriangle, Shield, Eye, Wifi, WifiOff, Info } from 'lucide-react';
import { dashboardFetch, getLiveFeed, getVehiclesCameras } from '../api';
import { MapContainer, TileLayer, Marker, Popup, LayersControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Leaflet Icon setup
// Explicit asset URLs avoid depending on Leaflet’s internal icon path detection.
L.Marker.prototype.options.icon = L.icon({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], tooltipAnchor: [16, -28], shadowSize: [41, 41],
});

const createPulseIcon = (color: string, isThreat: boolean) => new L.DivIcon({
  html: `<div style="
    background-color: ${color}; 
    width: ${isThreat ? '16px' : '12px'}; 
    height: ${isThreat ? '16px' : '12px'}; 
    border-radius: 50%; 
    border: 2px solid ${isThreat ? 'white' : 'rgba(255,255,255,0.7)'}; 
    box-shadow: 0 0 ${isThreat ? '20px 5px' : '10px 2px'} ${color};
    ${isThreat ? 'animation: pulse-ring 1s infinite alternate;' : ''}
  "></div>`,
  className: '',
  iconSize: isThreat ? [16, 16] : [12, 12],
  iconAnchor: isThreat ? [8, 8] : [6, 6]
});

const ZONE_COLORS = {
  entrance:     '#10b981',
  cash_counter: '#f59e0b',
  atm:          '#6366f1',
  restricted:   '#ef4444',
  public:       '#0ea5e9',
};

export default function Topology() {
  const [threatCamIds, setThreatCamIds]   = useState<string[]>([]);
  const [alertLog, setAlertLog]           = useState<SecurityEvent[]>([]);
  const [hoveredCam, setHoveredCam]       = useState<string | null>(null);
  const [liveEvents, setLiveEvents]       = useState<SecurityEvent[]>([]);
  const [isUploading, setIsUploading]     = useState(false);
  const [cameras, setCameras] = useState<GeoCamera[]>([]);
  const [selectedCam, setSelectedCam]     = useState("");
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const prevThreatCountRef = React.useRef(0);
  const [showProdNote, setShowProdNote]   = useState(false);
  const [toastMessage, setToastMessage]   = useState<string | null>(null);

  // Audio function using Web Audio API to play a beep sequence
  const playAlarmSound = () => {
    try {
      const audioCtx = new (window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext!)();
      
      const playBeep = (time: number, freq: number) => {
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        oscillator.type = 'square';
        oscillator.frequency.setValueAtTime(freq, audioCtx.currentTime + time);
        
        gainNode.gain.setValueAtTime(0, audioCtx.currentTime + time);
        gainNode.gain.linearRampToValueAtTime(0.1, audioCtx.currentTime + time + 0.05);
        gainNode.gain.linearRampToValueAtTime(0, audioCtx.currentTime + time + 0.3);
        
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        oscillator.start(audioCtx.currentTime + time);
        oscillator.stop(audioCtx.currentTime + time + 0.3);
      };

      // Play a triple beep siren pattern (Critical Alert)
      playBeep(0, 880);
      playBeep(0.4, 880);
      playBeep(0.8, 880);
    } catch(e) {
      console.warn("Audio play failed", e);
    }
  };

  useEffect(() => {
    getVehiclesCameras().then(res => {
      const cams = res.cameras || [];
      setCameras(cams);
      if (cams.length > 0) setSelectedCam(cams[0].camera_id);
    }).catch(err => console.error(err));

    const poll = () => {
      getLiveFeed()
        .then(res => {
          const events = res.data?.feed || [];
          setLiveEvents(events);
          const criticalEvents = events.filter(e => e.severity === 'critical' || e.severity === 'high');
          const criticalCams = criticalEvents.map(e => e.camera_id);
          
          if (criticalCams.length > 0) {
            setThreatCamIds(prev => {
              const newThreats = [...new Set([...prev, ...criticalCams])];
              if (newThreats.length > prevThreatCountRef.current) {
                // Play alarm when a NEW threat is detected
                playAlarmSound();
              }
              prevThreatCountRef.current = newThreats.length;
              return newThreats;
            });
          }
          
          // Update log with real events
          setAlertLog(criticalEvents.slice(0, 10));
        })
        .catch(() => {});
    };
    poll();
    const interval = setInterval(poll, 3000); // Poll every 3 seconds for fast demo
    return () => clearInterval(interval);
  }, []);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('camera_id', selectedCam);

    try {
      const response = await dashboardFetch('/video/upload', {
        method: 'POST',
        body: formData,
      });
      const data: unknown = await response.json();
      console.log("Upload response:", data);
      setToastMessage(`✅ Feed connected to ${selectedCam}. ML analysis running...`);
      setTimeout(() => setToastMessage(null), 5000);
    } catch (error) {
      console.error("Error running video inference:", error);
      setToastMessage("❌ ERROR: Connection to ML Server failed.");
      setTimeout(() => setToastMessage(null), 5000);
    } finally {
      setIsUploading(false);
      // Reset input
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const clearAlerts = () => {
    setThreatCamIds([]);
    setAlertLog([]);
    prevThreatCountRef.current = 0;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      
      {/* ── TOP BAR ─────────────────────────────────────── */}
      <div style={{
        padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)', zIndex: 10
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Eye size={20} color="#0ea5e9" />
            <h1 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-primary)', letterSpacing: '-0.3px' }}>
              Branch Topology
            </h1>
            {threatCamIds.length > 0 && (
              <span style={{
                background: 'rgba(239,68,68,0.15)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.4)',
                padding: '2px 10px', borderRadius: '99px', fontSize: '11px', fontWeight: '600',
                animation: 'fadeIn 0.3s ease'
              }}>
                {threatCamIds.length} THREAT{threatCamIds.length > 1 ? 'S' : ''} ACTIVE
              </span>
            )}
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
            Modern Bank Branch · Ground Floor · 8 Cameras Active
          </p>
        </div>

        {/* Camera Status Summary */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <div style={{ display: 'flex', gap: '16px' }}>
            {[
              { label: 'Active',  count: cameras.length,  color: '#10b981' },
              { label: 'Alerts',  count: threatCamIds.length,  color: '#ef4444' },
            ].map(s => (
              <div key={s.label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '20px', fontWeight: '700', color: s.color, lineHeight: 1 }}>{s.count}</div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{s.label}</div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <select
              value={selectedCam}
              onChange={(e) => setSelectedCam(e.target.value)}
              style={{
                background: 'var(--bg-surface)', color: 'var(--text-primary)', border: '1px solid var(--border)',
                padding: '8px 12px', borderRadius: '8px', fontSize: '12px', outline: 'none'
              }}
            >
              {cameras.map(c => (
                <option key={c.camera_id} value={c.camera_id} style={{ background: 'var(--bg-surface)' }}>{c.name}</option>
              ))}
            </select>
            
            <input 
              type="file" 
              accept="video/mp4,video/webm" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              onChange={handleFileUpload} 
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              style={{
                background: 'linear-gradient(135deg, #0ea5e9, #0284c7)', color: '#fff', border: 'none',
                padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '600',
                cursor: isUploading ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                boxShadow: '0 0 20px rgba(14,165,233,0.3)', opacity: isUploading ? 0.7 : 1
              }}
            >
              <Shield size={14} /> {isUploading ? 'Connecting...' : 'Upload Camera Feed'}
            </button>
            
            <div style={{ position: 'relative' }}>
              <button 
                onClick={() => setShowProdNote(!showProdNote)}
                style={{
                  background: 'var(--bg-surface)', color: 'var(--text-secondary)', border: '1px solid var(--border)',
                  padding: '7px 8px', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}
                title="Production Integration Info"
              >
                <Info size={16} />
              </button>
              {showProdNote && (
                <div style={{
                  position: 'absolute', top: '100%', right: '0', marginTop: '8px', width: '280px',
                  background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '8px',
                  padding: '12px', boxShadow: '0 10px 25px rgba(0,0,0,0.5)', zIndex: 100,
                  fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5'
                }}>
                  <div style={{ fontWeight: '700', color: '#0ea5e9', marginBottom: '6px', fontSize: '13px' }}>Production Integration Note</div>
                  In a real production environment, this manual upload button will be removed. The system will connect directly to the cameras via <b>RTSP or ONVIF</b> live streams, and the ML engine will process the video feeds continuously in real-time.
                </div>
              )}
            </div>

            {toastMessage && (
              <div style={{
                position: 'fixed', top: '20px', left: '50%', transform: 'translateX(-50%)',
                background: 'var(--bg-surface)', border: '1px solid #0ea5e9', borderRadius: '8px',
                padding: '12px 24px', color: 'var(--text-primary)', fontSize: '14px', fontWeight: '500',
                boxShadow: '0 10px 25px rgba(0,0,0,0.5)', zIndex: 1000,
                animation: 'fadeIn 0.3s ease'
              }}>
                {toastMessage}
              </div>
            )}

            {alertLog.length > 0 && (
              <button
                onClick={clearAlerts}
                style={{
                  background: 'var(--bg-surface)', color: 'var(--text-secondary)', border: '1px solid var(--border)',
                  padding: '8px 14px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer',
                }}
              >
                Clear All
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── MAIN BODY ────────────────────────────────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* ── LEAFLET MAP ──────────────────────────────────── */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden', padding: '16px' }}>
          <div style={{ position: 'relative', width: '100%', height: '100%', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border)' }}>
            
            <MapContainer center={[23.0225, 72.5714]} zoom={11} style={{ height: '100%', width: '100%' }} zoomControl={false}>
              <LayersControl position="topright">
                <LayersControl.BaseLayer checked name="Street View">
                  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
                </LayersControl.BaseLayer>
                <LayersControl.BaseLayer name="Satellite View">
                  <TileLayer url="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}" attribution="Google" />
                </LayersControl.BaseLayer>
              </LayersControl>
              
              {cameras.map(cam => {
                const isThreat  = threatCamIds.includes(cam.camera_id);
                const zoneColor = '#0ea5e9'; // Default public color
                const icon = createPulseIcon(isThreat ? '#ef4444' : zoneColor, isThreat);

                return (
                  <Marker 
                    key={cam.camera_id} 
                    position={[cam.lat, cam.lng]} 
                    icon={icon}
                    eventHandlers={{
                      mouseover: () => setHoveredCam(cam.camera_id),
                      mouseout: () => setHoveredCam(null),
                    }}
                  >
                    <Popup>
                      <div className="p-1">
                        <div className="font-bold text-gray-800">{cam.name}</div>
                        <div className="text-xs text-gray-500">{cam.city} District</div>
                        {isThreat && <div className="text-xs font-bold text-red-500 mt-1">⚠️ THREAT ACTIVE</div>}
                      </div>
                    </Popup>
                  </Marker>
                );
              })}
            </MapContainer>

            {/* Zone Legend — bottom right */}
            <div style={{
              position: 'absolute', bottom: '24px', right: '24px', zIndex: 1000,
              background: 'var(--bg-surface)', backdropFilter: 'blur(12px)',
              border: '1px solid var(--border)', borderRadius: '8px',
              padding: '10px 14px',
            }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: '600' }}>
                Map Legend
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#0ea5e9', boxShadow: `0 0 6px #0ea5e980` }} />
                <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Active Camera</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444', boxShadow: `0 0 10px #ef444480` }} />
                <span style={{ fontSize: '11px', color: '#ef4444', fontWeight: 'bold' }}>Threat Detected</span>
              </div>
            </div>
          </div>
        </div>

        {/* ── ALERT SIDEBAR ──────────────────────────────── */}
        <div style={{ 
          width: '300px', background: 'var(--bg-surface)', borderLeft: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', zIndex: 10
        }}>
          {/* Cameras list */}
          <div style={{ padding: '16px', borderBottom: '1px solid var(--border)' }}>
            <h3 style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Camera Status</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '10px' }}>
              {cameras.map(cam => {
                const isThreat  = threatCamIds.includes(cam.camera_id);
                const dotColor  = isThreat ? '#ef4444' : '#10b981';
                const isHovered = hoveredCam === cam.camera_id;
                const isSelected = selectedCam === cam.camera_id;
                return (
                  <div key={cam.camera_id} style={{
                    display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '7px 10px', borderRadius: '6px',
                    background: isThreat ? 'rgba(239,68,68,0.08)' : (isHovered || isSelected ? 'var(--bg-hover)' : 'transparent'),
                    borderLeft: isSelected ? '2px solid #0ea5e9' : '2px solid transparent',
                    transition: 'all 0.2s ease',
                    cursor: 'default',
                  }}
                    onMouseEnter={() => setHoveredCam(cam.camera_id)}
                    onMouseLeave={() => setHoveredCam(null)}
                  >
                    <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: dotColor, boxShadow: `0 0 6px ${dotColor}`, flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {cam.name}
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px', fontFamily: '"SF Mono", "Fira Code", monospace' }}>{cam.camera_id}</div>
                    </div>
                    {isThreat ? <AlertTriangle size={12} color="#ef4444" /> : <Wifi size={12} color="#10b98160" />}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Alert log */}
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: '600' }}>
                Alert Log
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{alertLog.length} events</span>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }} className="custom-scrollbar">
              {alertLog.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                  <Shield size={24} style={{ margin: '0 auto 8px', opacity: 0.3 }} />
                  No alerts. All clear.
                </div>
              ) : alertLog.map(log => (
                <div key={log.id} style={{
                  padding: '10px 12px', borderRadius: '8px', marginBottom: '6px',
                  background: 'var(--bg-surface)', borderTop: '1px solid var(--border)',
                  border: '1px solid rgba(239,68,68,0.15)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '10px', color: 'var(--text-muted)' }}>
                    <span style={{ fontSize: '11px', fontWeight: '700', color: '#ef4444' }}>⚠ {log.event_type.replace('_', ' ').toUpperCase()}</span>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{new Date(log.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{log.camera_id}</div>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>{log.summary}</div>
                  {log.thumbnail && (
                     <img src={log.thumbnail.startsWith('http') ? log.thumbnail : `http://127.0.0.1:8000${log.thumbnail}`} alt="Threat" style={{ width: '100%', height: '80px', objectFit: 'cover', marginTop: '8px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.1)' }} />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Global keyframes */}
      <style>{`
        @keyframes pulse-ring {
          0%   { transform: translate(-50%, -50%) scale(0.8); opacity: 1; }
          100% { transform: translate(-50%, -50%) scale(2.2); opacity: 0; }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
